from aiohttp import ClientSession
from aiohttp.web_request import URL
from asgiref.sync import sync_to_async
from asyncio import create_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from django.db.models import Sum
from json import dumps
from hashlib import sha1, sha256, sha384, sha512
from random import randint
from re import compile, escape
from requests import get
from rest.b3lb.metrics import incr_metric, update_create_metrics
from rest.models import ClusterGroup, ClusterGroupRelation, Meeting, Metric, Node, Parameter, RecordSet, Secret, SecretMeetingList, SecretMetricsList, Stats
from typing import Any, Dict, List, Literal, Tuple
from urllib.parse import urlencode


HOST_REGEX = compile(r'([^:]+)(:\d+)?$')
SLUG_REGEX = compile(r'^([a-z]{2,10})(-(\d{3}))?\.' + escape(settings.B3LB_API_BASE_DOMAIN) + '$')
CONTENT_TYPE = "text/xml"

SHA_ALGORITHMS_BY_LENGTH = {40: ClusterGroup.SHA1, 64: ClusterGroup.SHA256, 96: ClusterGroup.SHA384, 128: ClusterGroup.SHA512}
SHA_ALGORITHMS_BY_STRING = {ClusterGroup.SHA1: sha1, ClusterGroup.SHA256: sha256, ClusterGroup.SHA384: sha384, ClusterGroup.SHA512: sha512}

RETURN_STRING_GET_MEETINGS_NO_MEETINGS = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<meetings/>\r\n<messageKey>noMeetings</messageKey>\r\n<message>no meetings were found on this server</message>\r\n</response>'
RETURN_STRING_VERSION = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<version>2.0</version>\r\n</response>'
RETURN_STRING_CREATE_LIMIT_REACHED = '<response>\r\n<returncode>FAILED</returncode>\r\n<message>Meeting/Attendee limit reached.</message>\r\n</response>'
RETURN_STRING_IS_MEETING_RUNNING_FALSE = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<running>false</running>\r\n</response>'
RETURN_STRING_GET_RECORDING_TEXT_TRACKS_NOTHING_FOUND_JSON = '{"response":{"returncode":"FAILED","messageKey":"noRecordings","message":"No recording found"}}'
RETURN_STRING_GET_RECORDING_NO_RECORDINGS = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<recordings></recordings>\r\n<messageKey>noRecordings</messageKey>\r\n<message>There are no recordings for the meeting(s).</message>\r\n</response>'
RETURN_STRING_MISSING_MEETING_ID = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>missingParamMeetingID</messageKey>\r\n<message>You must specify a meeting ID for the meeting.</message>\r\n</response>'


class ClientB3lbRequest:
    """
    Class for client to BigBlueButton node communication.
    """
    request: HttpRequest
    parameters: Dict[str, Any]
    meeting_id: str
    body: str
    endpoint: str
    checksum: str
    stats_token: str
    node: Node
    secret: Secret
    ENDPOINTS_PASS_THROUGH: List[str]
    ENDPOINTS: Dict[str, Any]

    #### Asynchronous BBB Endpoints
    async def create(self) -> HttpResponse:
        """
        'create' endpoint.
        Creates a new meeting on a node if not exists.
        """
        if not self.meeting_id:
            return HttpResponse(RETURN_STRING_MISSING_MEETING_ID, content_type=CONTENT_TYPE)
        if not await sync_to_async(self.is_meeting)() and not await sync_to_async(self.is_node_free)():
            return HttpResponse(RETURN_STRING_CREATE_LIMIT_REACHED, content_type=CONTENT_TYPE)

        meeting, created = await sync_to_async(Meeting.objects.get_or_create)(id=self.meeting_id, secret=self.secret, defaults=self.get_meeting_defaults())

        if created:
            await sync_to_async(update_create_metrics)(self.secret, self.node)
        await sync_to_async(self.check_parameters)(meeting)
        return await self.pass_through()

    async def join(self) -> HttpResponse:
        """
        'join' endpoint.
        Get node and delegate (redirect) client to node.
        """
        if not self.meeting_id:
            return HttpResponse(RETURN_STRING_MISSING_MEETING_ID, content_type=CONTENT_TYPE)
        if not await sync_to_async(self.is_meeting)():
            return HttpResponseBadRequest()
        await sync_to_async(self.check_parameters)()
        await sync_to_async(incr_metric)(Metric.JOINED, self.secret, self.node)
        return HttpResponseRedirect(self.get_node_endpoint_url())

    async def get_meetings(self) -> HttpResponse:
        """
        'getMeetings' endpoint.
        Returns cached data to client.
        """
        try:
            secret_meeting_list = await sync_to_async(SecretMeetingList.objects.get)(secret=self.secret)
            return HttpResponse(secret_meeting_list.xml, content_type=CONTENT_TYPE)
        except ObjectDoesNotExist:
            return HttpResponse(RETURN_STRING_GET_MEETINGS_NO_MEETINGS, content_type=CONTENT_TYPE)

    @staticmethod
    async def get_recordings() -> HttpResponse:
        """
        'getRecordings' endpoint.
        Currently, hardcoded for future implementation.
        """
        return HttpResponse(RETURN_STRING_GET_RECORDING_NO_RECORDINGS, content_type=CONTENT_TYPE)

    @staticmethod
    async def get_recording_text_tracks() -> HttpResponse:
        """
        'getRecordingTextTracks' endpoint.
        Currently, hardcoded for future implementation.
        """
        return HttpResponse(RETURN_STRING_GET_RECORDING_TEXT_TRACKS_NOTHING_FOUND_JSON, content_type="application/json")

    async def is_meeting_running(self) -> HttpResponse:
        """
        'isMeetingRunning' endpoint.
        Checks meeting from B3LB database.
        Send client request to node and return response to client if exists otherwise return hardcoded answer.
        """
        if not await sync_to_async(self.is_meeting)():
            return HttpResponse(RETURN_STRING_IS_MEETING_RUNNING_FALSE, content_type=CONTENT_TYPE)
        return await self.pass_through()

    async def pass_through(self) -> HttpResponse:
        """
        Multiple BBB endpoints.
        Send client request to correct node and return node response to client.
        """
        async with ClientSession() as session:
            if self.request.method == "POST":
                async with session.post(await sync_to_async(self.get_node_endpoint_url_encoded)(), data=self.body) as res:
                    return HttpResponse(await res.text(), status=res.status, content_type=res.headers.get('content-type', CONTENT_TYPE))
            else:
                async with session.get(await sync_to_async(self.get_node_endpoint_url_encoded)()) as res:
                    return HttpResponse(await res.text(), status=res.status, content_type=res.headers.get('content-type', CONTENT_TYPE))

    @staticmethod
    async def version() -> HttpResponse:
        """
        Empty ('')/root endpoint.
        Returns the BigBlueButton API version.
        """
        return HttpResponse(RETURN_STRING_VERSION, content_type=CONTENT_TYPE)

    #### Own Routines & Endpoints ####
    async def endpoint_delegation(self) -> HttpResponse:
        """
        Check for right bbb endpoint and return response.
        """
        if self.endpoint in self.ENDPOINTS:
            return await self.ENDPOINTS[self.endpoint]()
        elif self.endpoint in self.ENDPOINTS_PASS_THROUGH:
            return await self.pass_through()
        else:
            return HttpResponseForbidden()

    async def metrics(self) -> HttpResponse:
        """
        Return cached prometheus metrics.
        Must be authorized by stats_token
        """
        if self.get_forwarded_host() == settings.B3LB_API_BASE_DOMAIN or (self.stats_token and self.secret and self.stats_token == str(self.secret.tenant.stats_token)):
            return HttpResponse(await sync_to_async(self.get_secret_metrics)() , content_type='text/plain')
        else:
            return HttpResponse("Unauthorized", status=401)

    async def stats(self) -> HttpResponse:
        if self.stats_token and self.secret and self.secret.tenant and self.stats_token == str(self.secret.tenant.stats_token):
            return HttpResponse(await sync_to_async(self.get_tenant_statistic)(), content_type='application/json')
        else:
            return HttpResponse("Unauthorized", status=401)

    #### Class Routines ####
    def allowed_methods(self) -> List[Literal["GET", "POST", "DELETE", "PATCH", "PUT"]]:
        if self.endpoint in ["b3lb_metrics", "b3lb_stats"]:
            return ["GET"]
        return ["GET", "POST"]

    ## Check Routines ##
    def check_checksum(self) -> bool:
        algorithm = self.get_sha_algorithm_by_parameter()
        if not algorithm:
            algorithm = self.get_sha_algorithm_by_checksum_length()
            if not algorithm:
                return False

        sha = algorithm()
        endpoint_string = f"{self.endpoint}{self.get_query_string()}"

        for secret in [self.secret.secret, self.secret.secret2]:
            sha.update(f"{endpoint_string}{secret}".encode())
            if sha.hexdigest() == self.checksum:
                return True
        return False

    def check_parameters(self, meeting: Meeting = None):
        parameters = Parameter.objects.filter(tenant=self.secret.tenant)
        if self.endpoint == "join":
            endpoint_parameters = Parameter.PARAMETERS_JOIN
        elif self.endpoint == "create":
            endpoint_parameters = Parameter.PARAMETERS_CREATE
        else:
            endpoint_parameters = []

        for parameter in parameters:
            if parameter.parameter in endpoint_parameters:
                if parameter.parameter in self.parameters:
                    if parameter.mode == Parameter.BLOCK:
                        self.parameters.pop(parameter.parameter)
                    elif parameter.mode == Parameter.OVERRIDE:
                        self.parameters[parameter.parameter] = parameter.value
                elif parameter.mode in [Parameter.SET, Parameter.OVERRIDE]:
                    self.parameters[parameter.parameter] = parameter.value

        if self.endpoint == "join" and Parameter.USERDATA_BBB_CUSTOM_STYLE_URL not in self.parameters and hasattr(self.secret.tenant, 'asset') and self.secret.tenant.asset.custom_css:
            self.parameters[Parameter.USERDATA_BBB_CUSTOM_STYLE_URL] = self.secret.tenant.asset.custom_css_url

        elif self.endpoint == "create":
            self.parameters.pop("dialNumber", None)
            self.parameters.pop("voiceBridge", None)

            # check for custom logo
            if Parameter.LOGO not in self.parameters and hasattr(self.secret.tenant, 'asset') and self.secret.tenant.asset.logo:
                self.parameters[Parameter.LOGO] = self.secret.tenant.asset.logo_url

            # check for custom slide
            if self.request.method == "GET" and hasattr(self.secret.tenant, 'asset') and self.secret.tenant.asset.slide:
                slide_base64 = self.secret.tenant.asset.slide_base64
                if slide_base64:
                    self.body = f'<modules><module name="presentation"><document name="{self.secret.tenant.asset.s_filename}">{slide_base64}</document></module></modules>'
                else:
                    self.body = f'<modules><module name="presentation"><document url="{self.secret.tenant.asset.slide_url}" filename="{self.secret.tenant.asset.s_filename}"></document></module></modules>'
                self.request.method = "POST"

            # check if records are enabled
            if self.secret.is_record_enabled:
                record_set = RecordSet.objects.create(secret=self.secret, meeting=meeting, id_meeting=meeting.id, recording_ready_origin_url=self.parameters.pop("meta_bbb-recording-ready-url", ""), nonce=meeting.nonce)
                self.parameters["meta_recordset"] = record_set.nonce
            else:
                # record aren't enabled -> suppress any record related parameter
                for param in [Parameter.RECORD, Parameter.ALLOW_START_STOP_RECORDING, Parameter.AUTO_START_RECORDING]:
                    self.parameters[param] = "false"

            self.parameters["meta_endCallbackUrl"] = f"https://{self.secret.endpoint}/b3lb/b/meeting/end?nonce={meeting.nonce}"

    def is_allowed_method(self) -> bool:
        if self.request.method in self.allowed_methods():
            return True
        return False

    def is_authorized(self) -> bool:
        if self.secret and self.check_checksum():
            return True
        return False

    def is_in_limit(self) -> bool:
        if self.secret.tenant.meeting_limit > 0 and not Meeting.objects.filter(secret__tenant=self.secret.tenant).count() < self.secret.tenant.meeting_limit:
            incr_metric(Metric.MEETING_LIMIT_HITS, Secret.objects.get(tenant=self.secret.tenant, sub_id=0), self.node)
            return False

        if self.secret.meeting_limit > 0 and not Meeting.objects.filter(secret=self.secret).count() < self.secret.meeting_limit:
            incr_metric(Metric.MEETING_LIMIT_HITS, self.secret, self.node)
            return False

        if self.secret.tenant.attendee_limit > 0:
            attendee_sum = Meeting.objects.filter(secret__tenant=self.secret.tenant).aggregate(Sum('attendees'))["attendees__sum"]
            # Aggregation sum can return None or [0, inf).
            # Only check for limit if aggregation sum is an integer.
            if isinstance(attendee_sum, int) and not attendee_sum < self.secret.tenant.attendee_limit:
                incr_metric(Metric.ATTENDEE_LIMIT_HITS, Secret.objects.get(tenant=self.secret.tenant, sub_id=0), self.node)
                return False

        if self.secret.attendee_limit > 0:
            attendee_sum = Meeting.objects.filter(secret=self.secret).aggregate(Sum('attendees'))["attendees__sum"]
            # Same as above
            if isinstance(attendee_sum, int) and not attendee_sum < self.secret.attendee_limit:
                incr_metric(Metric.ATTENDEE_LIMIT_HITS, self.secret, self.node)
                return False
        return True

    def is_meeting(self) -> bool:
        if self.meeting_id:
            self.set_node_by_meeting_id()
            if self.node:
                return True
            return False
        return False

    def is_node_free(self) -> bool:
        self.set_node_by_lowest_workload()
        if self.node:
            return True
        return False

    ## Getter Routines ##
    def get_meeting_defaults(self) -> Dict[str, Any]:
        return {"id": self.meeting_id, "secret": self.secret, "node": self.node, "room_name": self.parameters.get("name", "Unknown"), "end_callback_url": self.parameters.get("meta_endCallbackUrl", "")}

    def get_node_endpoint_url(self) -> str:
        sha = self.get_sha_algorithm_by_cluster_group()
        parameter_str = ""
        if self.parameters:
            parameter_str = urlencode(self.parameters, safe='*')

        sha.update(f"{self.endpoint}{parameter_str}{self.node.secret}".encode())
        return f"{self.node.api_base_url}{self.endpoint}?{parameter_str}&checksum={sha.hexdigest()}"

    def get_node_endpoint_url_encoded(self) -> URL:
        return URL(self.get_node_endpoint_url(), encoded=True)

    def get_forwarded_host(self) -> str:
        return HOST_REGEX.sub(r'\1', self.request.META.get('HTTP_X_FORWARDED_HOST', self.request.META.get('HTTP_HOST')))

    def get_query_string(self) -> str:
        query_string = self.request.META.get("QUERY_STRING", "")
        query_string = query_string.replace("&checksum=" + self.checksum, "")
        query_string = query_string.replace("checksum=" + self.checksum + "&", "")
        query_string = query_string.replace("checksum=" + self.checksum, "")
        return query_string

    def get_secret_metrics(self) -> str:
        return SecretMetricsList.objects.get(secret=self.secret).metrics

    @staticmethod
    def get_sha_algorithm(sha: str) -> Any:
        if sha not in settings.B3LB_ALLOWED_SHA_ALGORITHMS or sha not in SHA_ALGORITHMS_BY_STRING:
            return None
        return SHA_ALGORITHMS_BY_STRING[sha]

    def get_sha_algorithm_by_cluster_group(self) -> Any:
        cluster_group = ClusterGroupRelation.objects.get(cluster=self.node.cluster).cluster_group
        return self.get_sha_algorithm(cluster_group.sha_function)

    def get_sha_algorithm_by_checksum_length(self) -> Any:
        check_length = len(self.checksum)
        if check_length not in SHA_ALGORITHMS_BY_LENGTH:
            return self.get_sha_algorithm("")
        return self.get_sha_algorithm(SHA_ALGORITHMS_BY_LENGTH[check_length])

    def get_sha_algorithm_by_parameter(self) -> Any:
        return self.get_sha_algorithm(self.parameters.get("checksumHash", ""))

    def get_tenant_statistic(self) -> str:
        statistic = {}
        for stat in Stats.objects.filter(tenant=self.secret.tenant):
            if stat.bbb_origin_server_name not in statistic:
                statistic[stat.bbb_origin_server_name] = {}
            statistic[stat.bbb_origin_server_name][stat.bbb_origin] = {
                "participantCount": stat.attendees,
                "listenerCount": stat.listenerCount,
                "voiceParticipantCount": stat.voiceParticipantCount,
                "moderatorCount": stat.moderatorCount,
                "videoCount": stat.videoCount,
                "meetingCount": stat.meetings
            }
        return dumps(statistic)

    ## Setter Routines ##
    def set_node_by_meeting_id(self):
        self.node = None
        if self.meeting_id:
            try:
                meeting = Meeting.objects.get(id=self.meeting_id, secret=self.secret)
                if not meeting.node.has_errors:
                    self.node = meeting.node
            except ObjectDoesNotExist:
                pass

    def set_node_by_lowest_workload(self):
        self.node = None
        lowest = 10000000
        lowest_node_list = []
        for cluster_relation in ClusterGroupRelation.objects.filter(cluster_group=self.secret.tenant.cluster_group):
            for node in Node.objects.filter(cluster=cluster_relation.cluster):
                if 0 <= node.load <= lowest:
                    if node.load == lowest:
                        lowest_node_list.append(node)
                    else:
                        lowest_node_list = [node]
                        lowest = node.load

        # return randomized node if multiple are possible
        if lowest_node_list:
            self.node = lowest_node_list[randint(0, len(lowest_node_list) - 1)]

    def set_secret_by_slug_and_slug_id(self, slug: str, sub_id: int):
        if not slug:
            search = SLUG_REGEX.search(self.get_forwarded_host())
            if search:
                slug = search.group(1).upper()
                sub_id = int(search.group(3) or 0)
        if slug:
            try:
                self.secret = Secret.objects.select_related("tenant", "tenant__asset").get(tenant__slug=slug.upper(), sub_id=sub_id)
            except ObjectDoesNotExist:
                pass

    ## INIT ##
    def __init__(self, request: HttpRequest, endpoint: str):
        self.request = request
        self.endpoint = endpoint
        self.parameters = {}
        self.body = ""
        for parameter in request.GET.keys():
            self.parameters[parameter] = request.GET.get(parameter)

        self.meeting_id = self.parameters.get("meetingID", "")
        self.checksum = self.parameters.pop("checksum", "")
        self.stats_token = self.request.headers.get("Authorization", "")

        self.secret = None
        self.node = None
        self.ENDPOINTS_PASS_THROUGH = ["end", "insertDocument", "setConfigXML", "getMeetingInfo"]
        self.ENDPOINTS = {
            "": self.version,
            "create": self.create,
            "join": self.join,
            "isMeetingRunning": self.is_meeting_running,
            "getMeetings": self.get_meetings,
            "getRecordingTextTracks": self.get_recording_text_tracks,
            "getRecordings": self.get_recordings,
            "b3lb_metrics": self.metrics,
            "b3lb_stats": self.stats
        }


class NodeB3lbRequest:
    """
    Class for node to B3LB backend communication.
    """
    BACKENDS: Dict[str, Dict[Literal["methods", "function"], Any]]
    request: HttpRequest
    meeting: Meeting
    backend: str
    endpoint: str
    meeting_id: str
    nonce: str
    recording_marks: str

    def is_allowed_endpoint(self) -> bool:
        if self.full_endpoint() in self.BACKENDS:
            return True
        return False

    def allowed_methods(self) -> List[str]:
        return self.BACKENDS[self.full_endpoint()]["methods"]

    def is_allowed_method(self) -> bool:
        if self.full_endpoint() in self.BACKENDS and self.request.method in self.BACKENDS[self.full_endpoint()]["methods"]:
            return True
        return False

    def is_meeting(self) -> bool:
        if self.meeting_id and self.nonce:
            try:
                self.meeting = Meeting.objects.get(id=self.meeting_id, nonce=self.nonce)
                return True
            except ObjectDoesNotExist:
                return False
        return False

    async def end_meeting(self) -> HttpResponse:
        """
        Run end meeting routines and destroy meeting database object.
        """
        if await sync_to_async(self.is_meeting)():
            # fire and forget request to meeting creator system/client
            create_task(self.send_end_callback())
            if self.recording_marks == "false":
                try:
                    await sync_to_async(RecordSet.objects.get)(meeting=self.meeting, nonce=self.nonce)
                except ObjectDoesNotExist:
                    pass
            self.meeting.delete()
        return HttpResponse(status=204)

    async def endpoint_delegation(self) -> HttpResponse:
        if self.full_endpoint() in self.BACKENDS:
            return await self.BACKENDS[self.full_endpoint()]["function"]()
        return HttpResponseForbidden()

    def full_endpoint(self) -> str:
        return f"{self.backend}/{self.endpoint}"

    async def send_end_callback(self):
        """
        Send async end callback (fire and forget).
        """
        if "?" in self.meeting.end_callback_url:
            url = f"{self.meeting.end_callback_url}&meetingID={self.meeting_id}&recordingmarks={self.recording_marks}"
        else:
            url = f"{self.meeting.end_callback_url}?meetingID={self.meeting_id}&recordingmarks={self.recording_marks}"
        get(url)

    def __init__(self, request: HttpRequest, backend: str, endpoint: str):
        self.request = request
        self.meeting = None
        self.backend = backend
        self.endpoint = endpoint
        self.meeting_id = self.request.GET.get("meetingID", "")
        self.nonce = self.request.GET.get("nonce", "")
        self.recording_marks = self.request.GET.get("recordingmarks", "false")
        self.BACKENDS = {
            "meeting/end": {"methods": ["GET"], "function": self.end_meeting},
        }
