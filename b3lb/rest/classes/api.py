# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2023 IBH IT-Service GmbH
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
# for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


from aiohttp import ClientSession
from aiohttp.web_request import URL
from asgiref.sync import sync_to_async
from asyncio import create_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.db.models.query import QuerySet, Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from django.template.loader import render_to_string
from json import dumps
from _hashlib import HASH
from random import randint
from requests import get
from requests.exceptions import RequestException
from rest.b3lb.metrics import incr_metric, update_create_metrics
from rest.b3lb.parameters import ALLOW_START_STOP_RECORDING, AUTO_START_RECORDING, BLOCK, LOGO, OVERRIDE, PARAMETERS_CREATE, PARAMETERS_JOIN, RECORD, SET, USERDATA_BBB_CUSTOM_STYLE_URL
from rest.b3lb.utils import get_checksum
from rest.models import is_meeting_name_length_fine, ClusterGroupRelation, Meeting, Metric, Node, Parameter, Record, RecordSet, Secret, SecretMeetingList, SecretMetricsList, Stats
from typing import Any, Dict, List, Literal, Union
from uuid import UUID
from urllib.parse import urlencode
from xmltodict import parse
import rest.b3lb.constants as cst


class ClientB3lbRequest:
    """
    Class for client to BigBlueButton node communication.
    """
    request: HttpRequest
    parameters: Dict[str, Any]
    meeting_id: str
    body: Union[str, bytes]
    endpoint: str
    checksum: str
    stats_token: str
    node: Union[Node, None]
    secret: Union[Secret, None]
    state: str
    ENDPOINTS_PASS_THROUGH: List[str]
    ENDPOINTS: Dict[str, Any]

    #### Asynchronous BBB Endpoints
    async def create(self) -> HttpResponse:
        """
        'create' endpoint.
        Creates a new meeting on a node if not exists.
        """
        if not self.meeting_id:
            return HttpResponse(cst.RETURN_STRING_MISSING_MEETING_ID, content_type=cst.CONTENT_TYPE)

        if not is_meeting_name_length_fine(self.parameters.get("name", "")):
            return HttpResponse(cst.RETURN_STRING_WRONG_MEETING_NAME_LENGTH, content_type=cst.CONTENT_TYPE)

        if not await self.is_meeting():
            if not await sync_to_async(self.is_node_free)():
                return HttpResponse(cst.RETURN_STRING_CREATE_NO_NODE_AVAILABE, content_type=cst.CONTENT_TYPE)
            elif not await sync_to_async(self.is_in_limit)():
                return HttpResponse(cst.RETURN_STRING_CREATE_LIMIT_REACHED, content_type=cst.CONTENT_TYPE)

        meeting, created = await sync_to_async(Meeting.objects.get_or_create)(id=self.meeting_id, secret=self.secret, defaults=self.get_meeting_defaults())

        if created:
            await sync_to_async(update_create_metrics)(self.secret, self.node)
        await sync_to_async(self.check_parameters)(meeting, created)
        return await self.pass_through()

    async def join(self) -> HttpResponse:
        """
        'join' endpoint.
        Get node and delegate (redirect) client to node.
        """
        if not self.meeting_id:
            return HttpResponse(cst.RETURN_STRING_MISSING_MEETING_ID, content_type=cst.CONTENT_TYPE)
        if not await self.is_meeting():
            return HttpResponseBadRequest()
        await sync_to_async(self.check_parameters)()
        await sync_to_async(incr_metric)(Metric.JOINED, self.secret, self.node)
        return HttpResponseRedirect(await sync_to_async(self.get_node_endpoint_url)())

    async def get_meetings(self) -> HttpResponse:
        """
        'getMeetings' endpoint.
        Returns cached data to client.
        """
        try:
            secret_meeting_list = await sync_to_async(SecretMeetingList.objects.get)(secret=self.secret)
            return HttpResponse(secret_meeting_list.xml, content_type=cst.CONTENT_TYPE)
        except ObjectDoesNotExist:
            return HttpResponse(cst.RETURN_STRING_GET_MEETINGS_NO_MEETINGS, content_type=cst.CONTENT_TYPE)

    async def get_recordings(self) -> HttpResponse:
        """
        'getRecordings' endpoint.
        """
        if not self.secret.is_record_enabled:
            return HttpResponse(cst.RETURN_STRING_GET_RECORDING_NO_RECORDINGS, content_type=cst.CONTENT_TYPE)

        records = []
        recording_ids = self.parameters.get("recordID", "")
        if recording_ids:
            for recording_id in recording_ids.split(","):
                records = await sync_to_async(self.get_recording_dicts)(records, recording_id=recording_id)
        elif self.meeting_id:
            for meeting_id in self.meeting_id.split(","):
                records = await sync_to_async(self.get_recording_dicts)(records, meeting_id=meeting_id)
        else:
            records = await sync_to_async(self.get_recording_dicts)(records)

        if records:
            return HttpResponse(render_to_string(template_name="getRecordings.xml", context={"records": records}), content_type=cst.CONTENT_TYPE)
        return HttpResponse(cst.RETURN_STRING_GET_RECORDING_NO_RECORDINGS, content_type=cst.CONTENT_TYPE)

    async def publish_recordings(self) -> HttpResponse:
        """
        'publishRecordings' endpoint.
        """
        recording_ids = self.parameters.get("recordID", "")
        publish = self.parameters.get("publish", "")
        if not recording_ids:
            return HttpResponse(cst.RETURN_STRING_MISSING_RECORD_ID, content_type=cst.CONTENT_TYPE)

        if not publish or publish.lower() not in ["true", "false"]:
            return HttpResponse(cst.RETURN_STRING_MISSING_RECORD_PUBLISH, content_type=cst.CONTENT_TYPE)

        self.state = ""  # set to empty string for not filtering by state
        if publish == "true":
            published = True
        else:
            published = False

        for recording_id in recording_ids.split(","):
            recordings = await sync_to_async(self.filter_recordings)(recording_id=recording_id)
            await sync_to_async(recordings.update)(published=published)

        return HttpResponse(cst.RETURN_STRING_RECORD_PUBLISHED.format(publish), content_type=cst.CONTENT_TYPE)

    async def delete_recordings(self) -> HttpResponse:
        """
        'deleteRecordings' endpoint.
        """
        recording_ids = self.parameters.get("recordID", "")
        if not recording_ids:
            return HttpResponse(cst.RETURN_STRING_MISSING_RECORD_ID, content_type=cst.CONTENT_TYPE)

        self.state = ""  # set to empty string for not filtering by state
        for recording_id in recording_ids.split(","):
            await sync_to_async(self.delete_recordings_by_recording_id)(recording_id)

        return HttpResponse(cst.RETURN_STRING_RECORD_DELETED, content_type=cst.CONTENT_TYPE)

    async def update_recordings(self) -> HttpResponse:
        """
        'updateRecordings' endpoint.
        Currently limited to 'gl-listed' and 'name' meta data.
        Other data are ignored.
        ToDo: Upgrade to generic meta data update endpoint for recordings.
        """
        recording_ids = self.parameters.get("recordID", "")
        if not recording_ids:
            return HttpResponse(cst.RETURN_STRING_MISSING_RECORD_ID, content_type=cst.CONTENT_TYPE)

        gl_listed = self.parameters.get("meta_gl-listed", "")
        name = self.parameters.get("meta_name", "").strip()  # replacing Greenlight parameter syntax, which isn't part of the entered name

        # prevent database update error with arbitrary long name parameter value
        if len(name) > cst.RECORD_PROFILE_DESCRIPTION_LENGTH + cst.MEETING_NAME_LENGTH + 3:
            name = name[:cst.RECORD_PROFILE_DESCRIPTION_LENGTH + cst.MEETING_NAME_LENGTH + 3]

        self.state = ""  # no recording filter by state

        listed = False
        if gl_listed == "true":
            listed = True
        elif gl_listed != "false":
            gl_listed = ""

        for recording_id in recording_ids.split(","):
            recordings = await sync_to_async(self.filter_recordings)(recording_id=recording_id)
            if name:
                await sync_to_async(recordings.update)(name=name)
            if gl_listed:
                await sync_to_async(recordings.update)(gl_listed=listed)

        return HttpResponse(cst.RETURN_STRING_RECORD_UPDATED, content_type=cst.CONTENT_TYPE)

    @staticmethod
    async def get_recording_text_tracks() -> HttpResponse:
        """
        'getRecordingTextTracks' endpoint.
        Currently, hardcoded for future implementation.
        """
        return HttpResponse(cst.RETURN_STRING_GET_RECORDING_TEXT_TRACKS_NOTHING_FOUND_JSON, content_type="application/json")

    async def is_meeting_running(self) -> HttpResponse:
        """
        'isMeetingRunning' endpoint.
        Checks meeting from B3LB database.
        Send client request to node and return response to client if exists otherwise return hardcoded answer.
        """
        if not await self.is_meeting():
            return HttpResponse(cst.RETURN_STRING_IS_MEETING_RUNNING_FALSE, content_type=cst.CONTENT_TYPE)
        return await self.pass_through()

    async def pass_through(self) -> HttpResponse:
        """
        Multiple BBB endpoints.
        Send client request to correct node and return node response to client.
        """
        if not self.meeting_id:
            return HttpResponse(cst.RETURN_STRING_MISSING_MEETING_ID, content_type=cst.CONTENT_TYPE)
        if not await self.is_meeting():
            return HttpResponse(cst.RETURN_STRING_GET_MEETING_INFO_FALSE, content_type=cst.CONTENT_TYPE)
        if not self.node:
            await self.set_node_by_meeting_id()
        async with ClientSession() as session:
            if self.request.method == "POST":
                async with session.post(await sync_to_async(self.get_node_endpoint_url_encoded)(), data=self.body) as res:
                    return HttpResponse(await res.text(), status=res.status, content_type=res.headers.get('content-type', cst.CONTENT_TYPE))
            else:
                async with session.get(await sync_to_async(self.get_node_endpoint_url_encoded)()) as res:
                    return HttpResponse(await res.text(), status=res.status, content_type=res.headers.get('content-type', cst.CONTENT_TYPE))

    @staticmethod
    async def version() -> HttpResponse:
        """
        Empty ('')/root endpoint.
        Returns the BigBlueButton API version.
        """
        return HttpResponse(cst.RETURN_STRING_VERSION, content_type=cst.CONTENT_TYPE)

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
        if self.endpoint in ["b3lb_metrics", "b3lb_stats", "join"]:
            return ["GET"]
        return ["GET", "POST"]

    def filter_recordings(self, meeting_id: str = "", recording_id: str = "") -> QuerySet[Record]:
        if self.state and self.state not in ["unpublished", "published"]:
            return QuerySet(model=Record)  # return empty QuerySet if state isn't in allowed states

        query = Q(record_set__secret=self.secret)

        if recording_id:
            try:
                UUID(recording_id)
                query &= Q(uuid=recording_id)
            except ValueError:
                return QuerySet(model=Record)  # return empty QuerySet for BadRequest

        if meeting_id:
            try:
                UUID(meeting_id)
                query %= Q(record_set__meta_meeting_id=meeting_id)
            except ValueError:
                return QuerySet(model=Record)  # return empty QuerySet for BadRequest

        if self.state == "published":
            query &= Q(published=True)
        elif self.state == "unpublished":
            query &= Q(published=False)

        return Record.objects.filter(query)

    def delete_recordings_by_recording_id(self, recording_id: str = ""):
        recordings = self.filter_recordings(recording_id=recording_id)
        for recording in recordings:
            recording.delete()

    ## Check Routines ##
    def check_checksum(self) -> bool:
        algorithm = self.get_sha_by_parameter()
        if not algorithm:
            algorithm = self.get_sha_by_length()
            if not algorithm:
                return False

        endpoint_string = f"{self.endpoint}{self.get_query_string()}"

        for secret in [self.secret.secret, self.secret.secret2]:
            if get_checksum(algorithm(), f"{endpoint_string}{secret}") == self.checksum:
                return True
        return False

    def check_parameters(self, meeting: Meeting = None, created: bool = False):
        parameters = Parameter.objects.filter(tenant=self.secret.tenant)
        if self.endpoint == "join":
            endpoint_parameters = PARAMETERS_JOIN
        elif self.endpoint == "create":
            endpoint_parameters = PARAMETERS_CREATE
        else:
            endpoint_parameters = []

        for parameter in parameters:
            if parameter.parameter in endpoint_parameters:
                if parameter.parameter in self.parameters:
                    if parameter.mode == BLOCK:
                        self.parameters.pop(parameter.parameter)
                    elif parameter.mode == OVERRIDE:
                        self.parameters[parameter.parameter] = parameter.value
                elif parameter.mode in [SET, OVERRIDE]:
                    self.parameters[parameter.parameter] = parameter.value

        if self.endpoint == "join" and USERDATA_BBB_CUSTOM_STYLE_URL not in self.parameters and hasattr(self.secret.tenant, 'asset') and self.secret.tenant.asset.custom_css:
            self.parameters[USERDATA_BBB_CUSTOM_STYLE_URL] = self.secret.tenant.asset.custom_css_url

        elif self.endpoint == "create":
            self.parameters.pop("dialNumber", None)
            self.parameters.pop("voiceBridge", None)

            # check for custom logo
            if LOGO not in self.parameters and hasattr(self.secret.tenant, 'asset') and self.secret.tenant.asset.logo:
                self.parameters[LOGO] = self.secret.tenant.asset.logo_url

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
                if created: # only if meeting has been created otherwise do nothing
                    record_set = RecordSet.objects.create(secret=self.secret, meeting=meeting, meta_meeting_id=meeting.id, recording_ready_origin_url=self.parameters.pop("meta_bbb-recording-ready-url", ""), meta_end_callback_url=meeting.end_callback_url, nonce=meeting.nonce)
                    self.parameters[f"meta_{settings.B3LB_RECORD_META_DATA_TAG}"] = record_set.nonce
            else:
                # record aren't enabled -> suppress any record related parameter
                for param in [RECORD, ALLOW_START_STOP_RECORDING, AUTO_START_RECORDING]:
                    self.parameters[param] = "false"

            self.parameters["meta_endCallbackUrl"] = f"https://{settings.B3LB_API_BASE_DOMAIN}/b3lb/b/meeting/end?nonce={meeting.nonce}"

    def is_allowed_method(self) -> bool:
        if self.request.method in self.allowed_methods():
            return True
        return False

    def is_authorized(self) -> bool:
        if self.secret and self.check_checksum():
            return True
        return False

    def is_in_limit(self) -> bool:
        """
        Check meeting and attendee limit for secret and tenant.
        Returns True if values are below limit, False if limit is reached.
        """
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

    async def is_meeting(self) -> bool:
        if self.meeting_id:
            await self.set_node_by_meeting_id()
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
        parameter_str = ""
        if self.parameters:
            parameter_str = urlencode(self.parameters, safe='*')
        return f"{self.node.api_base_url}{self.endpoint}?{parameter_str}&checksum={get_checksum(self.node.cluster.get_sha(), f'{self.endpoint}{parameter_str}{self.node.secret}')}"

    def get_node_endpoint_url_encoded(self) -> URL:
        return URL(self.get_node_endpoint_url(), encoded=True)

    def get_forwarded_host(self) -> str:
        return cst.HOST_REGEX.sub(r'\1', self.request.META.get('HTTP_X_FORWARDED_HOST', self.request.META.get('HTTP_HOST')))

    def get_query_string(self) -> str:
        query_string = self.request.META.get("QUERY_STRING", "")
        query_string = query_string.replace("&checksum=" + self.checksum, "")
        query_string = query_string.replace("checksum=" + self.checksum + "&", "")
        query_string = query_string.replace("checksum=" + self.checksum, "")
        return query_string

    def get_recording_dicts(self, records: List[Dict[str, Any]], meeting_id: str = "", recording_id: str = "") -> List[Dict[str, Any]]:
        for record in self.filter_recordings(meeting_id=meeting_id, recording_id=recording_id):
            if record.get_file_size() > 0:
                records.append(record.get_recording_dict())
        return records

    def get_secret_metrics(self) -> str:
        return SecretMetricsList.objects.get(secret=self.secret).metrics

    def get_sha_by_length(self) -> Union[HASH, None]:
        return cst.SHA_ALGORITHMS.get(len(self.checksum))

    def get_sha_by_parameter(self) -> Union[HASH, None]:
        return cst.SHA_ALGORITHMS.get(self.parameters.get("checksumHash", ""))

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
    async def set_node_by_meeting_id(self):
        self.node = None
        if self.meeting_id:
            try:
                meeting = await sync_to_async(Meeting.objects.select_related("node").get)(id=self.meeting_id, secret=self.secret)
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

    async def set_secret_by_slug_and_slug_id(self, slug: str, sub_id: int):
        if not slug:
            search = cst.SLUG_REGEX.search(self.get_forwarded_host())
            if search:
                slug = search.group(1).upper()
                sub_id = int(search.group(3) or 0)
        if slug:
            try:
                self.secret = await sync_to_async(Secret.objects.select_related("tenant", "tenant__asset").get)(tenant__slug=slug.upper(), sub_id=sub_id)
            except ObjectDoesNotExist:
                pass

    ## INIT ##
    def __init__(self, request: HttpRequest, endpoint: str):
        self.request = request
        self.endpoint = endpoint
        self.parameters = {}
        self.body = request.body
        for parameter in request.GET.keys():
            self.parameters[parameter] = request.GET.get(parameter)

        self.meeting_id = self.parameters.get("meetingID", "")
        self.checksum = self.parameters.pop("checksum", "")
        self.stats_token = self.request.headers.get("Authorization", "")

        self.secret = None
        self.node = None
        self.state = self.parameters.get("state", "")
        self.ENDPOINTS_PASS_THROUGH = ["end", "insertDocument", "setConfigXML", "getMeetingInfo"]
        self.ENDPOINTS = {
            "": self.version,
            "create": self.create,
            "join": self.join,
            "isMeetingRunning": self.is_meeting_running,
            "getMeetings": self.get_meetings,
            "getRecordingTextTracks": self.get_recording_text_tracks,
            "getRecordings": self.get_recordings,
            "deleteRecordings": self.delete_recordings,
            "publishRecordings": self.publish_recordings,
            "updateRecordings": self.update_recordings,
            "b3lb_metrics": self.metrics,
            "b3lb_stats": self.stats
        }


class NodeB3lbRequest:
    """
    Class for node to B3LB backend communication.
    """
    BACKENDS: Dict[str, Dict[Literal["methods", "function"], Any]]
    request: HttpRequest
    meeting: Union[Meeting, None]
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
            # fire and forget end meeting request to original callback url
            create_task(self.send_end_callback(self.meeting.end_callback_url))
            if self.recording_marks == "false":
                record_set = await sync_to_async(self.get_record_set_by_nonce)()
                if record_set:
                    await sync_to_async(record_set.delete)()
            await sync_to_async(self.meeting.delete)()
        return HttpResponse(status=204)

    async def endpoint_delegation(self) -> HttpResponse:
        if self.full_endpoint() in self.BACKENDS:
            return await self.BACKENDS[self.full_endpoint()]["function"]()
        return HttpResponseForbidden()

    def full_endpoint(self) -> str:
        return f"{self.backend}/{self.endpoint}"

    def get_record_set_by_nonce(self) -> Union[RecordSet, None]:
        try:
            record_set = RecordSet.objects.get(nonce=self.nonce)
        except ObjectDoesNotExist:
            return None
        return record_set

    async def send_end_callback(self, end_callback_url: str):
        """
        Send async end callback (fire and forget).
        """
        if end_callback_url:
            if "?" in end_callback_url:
                url = f"{end_callback_url}&meetingID={self.meeting_id}&recordingmarks={self.recording_marks}"
            else:
                url = f"{end_callback_url}?meetingID={self.meeting_id}&recordingmarks={self.recording_marks}"
            try:
                get(url)
            except RequestException as rex:
                print(f"Exception: {rex}")
                print(f"Couldn't send callback to URL: {url}")

    async def upload_record(self) -> HttpResponse:
        record_set: RecordSet
        if not self.nonce:
            return HttpResponse(status=400)

        record_set = await sync_to_async(self.get_record_set_by_nonce)()
        if not record_set:
            return HttpResponse(status=404)

        uploaded_file = self.request.FILES.get("file", None)
        if not uploaded_file:
            return HttpResponse(status=400)

        uploaded_meta = self.request.FILES.get("meta", {})
        if not uploaded_meta:
            return HttpResponse(status=400)

        meta = parse(uploaded_meta.read()).get("recording", {})

        if not meta or not isinstance(meta, dict):
            return HttpResponse(status=400)

        if meta.get("meta", {}).get("isBreakout", "false") == "true":
            return HttpResponse(status=403) # no support for breakout room recordings currently

        try:
            await sync_to_async(record_set.recording_archive.save)(name=f"{record_set.file_path}/raw.tar", content=ContentFile(uploaded_file.read()))
        except:
            return HttpResponse("Error during file save", status=503)

        record_set.meta_bbb_origin = meta.get("meta", {}).get("bbb-origin", "")
        record_set.meta_bbb_origin_server_name = meta.get("meta", {}).get("bbb-origin-server-name", "")
        record_set.meta_bbb_origin_version = meta.get("meta", {}).get("bbb-origin-version", "")
        if meta.get("meta", {}).get("gl-listed", "false") == "true":
            record_set.meta_gl_listed = True
        record_set.meta_meeting_name = meta.get("meeting", {}).get("@name", "")
        record_set.meta_start_time = meta.get("start_time", "")
        record_set.meta_end_time = meta.get("end_time", "")
        record_set.meta_participants = int(meta.get("participants", "1"))

        record_set.status = record_set.UPLOADED
        await sync_to_async(record_set.save)()

        return HttpResponse(status=204)

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
            "record/upload": {"methods": ["POST"], "function": self.upload_record}
        }
