# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2021 IBH IT-Service GmbH
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


import aiohttp
from aiohttp.web_request import URL
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from rest.models import Meeting, Metric, Stats, SecretMeetingList, Parameter, RecordSet
import rest.endpoints.b3lb.lb as lb
import rest.endpoints.b3lb.constants as constants
import json


##
# CONSTANTS
##
PASS_THOUGH_ENDPOINTS = [
    "end",
    "insertDocument",
    "setConfigXML",
    "isMeetingRunning",
    "getMeetingInfo"
]

WHITELISTED_ENDPOINTS = [
    "",
    "create",
    "join",
    "getMeetings",
    "publishRecordings",
    "deleteRecordings",
    "updateRecordings",
    "getRecordingTextTracks",
    "getRecordings",
    "putRecordingTextTrack",
] + PASS_THOUGH_ENDPOINTS

BLACKLISTED_ENDPOINTS = [
    "getDefaultConfigXML"
]

ENDPOINTS_WITH_INTERNAL_ID = [
    "create",
    "join",
    "end",
    "isMeetingRunning",
    "getMeetingInfo",
    "setConfigXML"
]

LEGAL_ENDPOINTS = WHITELISTED_ENDPOINTS + BLACKLISTED_ENDPOINTS
SUPPRESSED_PARAMS = ['dialNumber', 'voiceBridge']


##
# Meta Routine
##
async def requested_endpoint(secret, endpoint, request, params):
    if not endpoint:
        return HttpResponse(constants.RETURN_STRING_VERSION, content_type='text/html')

    external_id = params.get("meetingID")
    meeting = None
    if endpoint in ENDPOINTS_WITH_INTERNAL_ID:
        if external_id:
            params["meetingID"] = await lb.get_internal_id(secret, external_id)
        else:
            return HttpResponse(constants.RETURN_STRING_MISSING_MEETING_ID, content_type='test/html')
        meeting = await lb.get_running_meeting(params["meetingID"])

    if endpoint == "join":
        if meeting and meeting.node:
            return await join(params, meeting.node, secret)
        else:
            return HttpResponseBadRequest()

    if endpoint == "create":
        if not meeting:  # meeting doesn't exists
            limit_check = await lb.limit_check(secret)
            if limit_check:
                return await create(request, endpoint, params, meeting, secret, external_id=external_id)
            else:
                return HttpResponse(constants.RETURN_STRING_CREATE_LIMIT_REACHED, content_type='text/html')
        else:  # meeting exists
            return await create(request, endpoint, params, meeting, secret)

    if endpoint == "getMeetings":
        return await sync_to_async(get_meetings)(secret)

    # Pass Through Endpoints
    if endpoint in PASS_THOUGH_ENDPOINTS:
        if meeting and meeting.node:
            return await pass_through(request, endpoint, params, meeting, body=request.body)
        else:
            if endpoint == "isMeetingRunning":
                return HttpResponse(constants.RETURN_STRING_IS_MEETING_RUNNING_FALSE, content_type='text/html')
            else:
                return HttpResponse(constants.RETURN_STRING_GET_MEETING_NOT_FOUND, content_type='text/html')

    if endpoint == "getRecordings":
        # Todo: Implement get Records after implementing storage
        return HttpResponse(constants.RETURN_STRING_GET_RECORDING_NO_RECORDINGS, content_type='text/html')

    if endpoint == "publishRecordings":
        # Todo: Implement (un)publishing after implementing storage
        return HttpResponse(constants.RETURN_STRING_GENERAL_FAILED.format("published", "published"), content_type='text/html')

    if endpoint == "deleteRecordings":
        # Todo: Implement deletion after implementing storage
        return HttpResponse(constants.RETURN_STRING_GENERAL_FAILED.format("deleted", "deleted"), content_type='text/html')

    if endpoint == "updateRecordings":
        # Todo: Implement update Metadata after implementing storage
        return HttpResponse(constants.RETURN_STRING_GENERAL_FAILED.format("updated", "updated"), content_type='text/html')

    if endpoint == "setConfigXML":
        if meeting and meeting.node:
            return await pass_through(request, endpoint, params, meeting)
        else:
            return HttpResponseBadRequest()

    if endpoint == "getRecordingTextTracks":
        # Todo: Implement getRecordingTextTracks after implementing storage
        return HttpResponse(constants.RETURN_STRING_GET_RECORDING_TEXT_TRACKS_NOTHING_FOUND_JSON, content_type='application/json')

    if endpoint == "putRecordingTextTrack" and request.method == "POST":
        # Todo: Implement after design has been clarified
        return HttpResponse('{"response": {"messageKey": "upload_text_track_failed","message": "Text track upload failed.","recordId": "","returncode": "SUCCESS"}}', content_type='application/json')

    return HttpResponseBadRequest()


##
# Endpoints
##
def get_meetings(secret):
    try:
        secret_meeting_list = SecretMeetingList.objects.get(secret=secret)
    except ObjectDoesNotExist:
        return HttpResponse(constants.RETURN_STRING_GET_MEETINGS_NO_MEETINGS, content_type='text/html')

    return HttpResponse(secret_meeting_list.xml, content_type='text/html')


async def join(params, node, secret):
    params = await sync_to_async(lb.check_parameter)(params, secret.tenant, join=True)

    # check custom style css
    if Parameter.USERDATA_BBB_CUSTOM_STYLE_URL not in params and hasattr(secret.tenant, 'asset') and secret.tenant.asset.custom_css:
        params[Parameter.USERDATA_BBB_CUSTOM_STYLE_URL] = secret.tenant.asset.custom_css_url

    url = "{}{}".format(node.api_base_url, lb.get_endpoint_str("join", params, node.secret))

    # update metric stats
    await sync_to_async(lb.incr_metric)(Metric.JOINED, secret, node)

    return HttpResponseRedirect(url)


async def create(request, endpoint, params, secret, meeting=Meeting(), external_id=None):
    # suppress some parameters
    for param in SUPPRESSED_PARAMS:
        params.pop(param, None)
    body = request.body
    created = False

    if not meeting and not external_id:
        return HttpResponse(constants.RETURN_STRING_MISSING_MEETING_ID, content_type='test/html')
    elif meeting:
        external_id = meeting.external_id

    if meeting and meeting.node:
        node = meeting.node
    else:
        node = await lb.get_node_params_by_lowest_workload(secret.tenant.cluster_group)

    if not node:
        return HttpResponse(constants.RETURN_STRING_CREATE_FAILED)

    params = await sync_to_async(lb.check_parameter)(params, secret.tenant)

    # check for custom logo
    if Parameter.LOGO not in params and hasattr(secret.tenant, 'asset') and secret.tenant.asset.logo:
        params["logo"] = secret.tenant.asset.logo_url

    # check for custom slide
    if request.method == "GET" and hasattr(secret.tenant, 'asset') and secret.tenant.asset.slide:
        body = await sync_to_async(lb.get_slide_body_for_post)(secret)
        request.method = "POST"

    if "meta_endCallbackUrl" in params:
        end_callback_origin_url = params["meta_endCallbackUrl"]
    else:
        end_callback_origin_url = ""

    if not meeting:
        defaults = {
            "id": params["meetingID"],
            "external_id": external_id,
            "secret": secret,
            "node": node,
            "room_name": params.get("name", "Unknown"),
            "end_callback_url": end_callback_origin_url
        }
        meeting, created = await sync_to_async(Meeting.objects.get_or_create)(id=params["meetingID"], secret=secret, defaults=defaults)
        await lb.update_create_metrics(secret, node)

    # check if records are enabled
    if secret.is_record_enabled:
        if "meta_bbb-recording-ready-url" in params:
            record_set = await sync_to_async(RecordSet.objects.create)(secret=secret, meeting_relation=meeting, recording_ready_origin_url=params["meta_meta_bbb-recording-ready-url"])
        else:
            record_set = await sync_to_async(RecordSet.objects.create)(secret=secret, meeting_relation=meeting)
        params["meta_{}-recordset".format(settings.B3LB_SITE_SLUG)] = record_set.nonce
    else:
        # record aren't enabled -> suppress any record related parameter
        for param in [Parameter.RECORD, Parameter.ALLOW_START_STOP_RECORDING, Parameter.AUTO_START_RECORDING]:
            params[param] = "false"

    if "meta_bbb-recording-ready-url" in params:
        del params["meta_bbb-recording-ready-url"]

    params["meta_endCallbackUrl"] = "https://{}-{}.{}/b3lb/b/meeting/end?nonce={}".format(secret.tenant.slug.lower(), str(secret.sub_id).zfill(3), settings.B3LB_API_BACKEND_DOMAIN, meeting.nonce)

    response = await pass_through(request, endpoint, params, meeting, body=body)

    return response


# request to and response from node
async def pass_through(request, endpoint, params, meeting, body=None):
    url = "{}{}".format(meeting.node.api_base_url, lb.get_endpoint_str(endpoint, params, meeting.node.secret))

    async with aiohttp.ClientSession() as session:
        if request.method == "POST":
            async with session.post(URL(url, encoded=True), data=body) as res:
                response = await res.text()
                return HttpResponse(await lb.replace_information_in_xml(response, endpoint, meeting), status=res.status, content_type=res.headers.get('content-type', 'text/html'))
        else:
            async with session.get(URL(url, encoded=True)) as res:
                response = await res.text()
                print(response)
                return HttpResponse(await lb.replace_information_in_xml(response, endpoint, meeting), status=res.status, content_type=res.headers.get('content-type', 'text/html'))


def tenant_stats(tenant):
    result = {}
    stats = Stats.objects.filter(tenant=tenant)

    for stat in stats:
        if stat.bbb_origin_server_name not in result:
            result[stat.bbb_origin_server_name] = {}
        result[stat.bbb_origin_server_name][stat.bbb_origin] = {
            "participantCount": stat.attendees,
            "listenerCount": stat.listenerCount,
            "voiceParticipantCount": stat.voiceParticipantCount,
            "moderatorCount": stat.moderatorCount,
            "videoCount": stat.videoCount,
            "meetingCount": stat.meetings
        }
    return json.dumps(result)
