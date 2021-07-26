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
from rest.models import Meeting, Metric, Stats, SecretMeetingList, Asset, Parameter
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.core.exceptions import ObjectDoesNotExist
import rest.b3lb.lb as lb
import rest.b3lb.constants as constants
import json


##
# CONSTANTS
##
WHITELISTED_ENDPOINTS = [
    "",
    "create",
    "join",
    "end",
    "setConfigXML",
    "getMeetings",
    "isMeetingRunning",
    "getMeetingInfo",
]

BLACKLISTED_ENDPOINTS = [
    "publishRecordings",
    "deleteRecordings",
    "updateRecordings",
    "getRecordingTextTracks",
    "getRecordings",
    "putRecordingTextTrack",
    "getDefaultConfigXML"
]

LEGAL_ENDPOINTS = WHITELISTED_ENDPOINTS + BLACKLISTED_ENDPOINTS


##
# Meta Routine
##
async def requested_endpoint(secret, endpoint, request, params):
    if not endpoint:
        return HttpResponse(constants.RETURN_STRING_VERSION, content_type='text/html')

    if endpoint == "join":
        node = await lb.get_node_by_meeting_id(params["meetingID"], secret)
        if node:
            return await join(params, node, secret)
        else:
            return HttpResponseBadRequest()

    if endpoint == "create":
        node, new_meeting = await lb.check_meeting_existence(params["meetingID"], secret)
        if node and new_meeting:
            limit_check = await lb.limit_check(secret)
            if limit_check:
                return await create(request, endpoint, params, node, secret)
            else:
                return HttpResponse(constants.RETURN_STRING_CREATE_LIMIT_REACHED, content_type='text/html')
        elif node:
            return await create(request, endpoint, params, node, secret)
        else:
            return HttpResponse(constants.RETURN_STRING_CREATE_FAILED, content_type='text/html')

    if endpoint == "end":
        node = await lb.get_node_by_meeting_id(params["meetingID"], secret)
        if node:
            return await pass_through(request, endpoint, params, node)
        else:
            node = await sync_to_async(lb.get_node_params_by_lowest_workload)(secret.tenant.cluster_group)
            return await pass_through(request, endpoint, params, node)

    if endpoint == "isMeetingRunning":
        node = await lb.get_node_by_meeting_id(params["meetingID"], secret)

        if node:
            return await pass_through(request, endpoint, params, node)
        else:
            return HttpResponse(constants.RETURN_STRING_IS_MEETING_RUNNING_FALSE, content_type='text/html')

    if endpoint == "getMeetings":
        return await sync_to_async(get_meetings)(secret)

    if endpoint == "getMeetingInfo":
        node = await lb.get_node_by_meeting_id(params["meetingID"], secret)
        if node:
            return await pass_through(request, endpoint, params, node)
        else:
            return HttpResponse(constants.RETURN_STRING_GET_MEETING_INFO_NOT_FOUND, content_type='text/html')

    if endpoint == "setConfigXML":
        node = await lb.get_node_by_meeting_id(params["meetingID"], secret)
        if node:
            return await pass_through(request, endpoint, params, node)
        else:
            return HttpResponseBadRequest()

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
    if Parameter.USERDATA_BBB_CUSTOM_STYLE_URL not in params:
        params[Parameter.USERDATA_BBB_CUSTOM_STYLE_URL] = secret.tenant.asset.custom_css_url

    url = "{}{}".format(node.api_base_url, lb.get_endpoint_str("join", params, node.secret))

    # update metric stats
    await sync_to_async(lb.incr_metric)(Metric.JOINED, secret, node)

    return HttpResponseRedirect(url)


async def create(request, endpoint, params, node, secret):
    # suppress some parameters
    params.pop('dialNumber', None)
    params.pop('voiceBridge', None)
    body = request.body

    try:
        meeting_id = params["meetingID"]
    except KeyError:
        return HttpResponse(constants.RETURN_STRING_MISSING_MEETING_ID, content_type='test/html')

    params = await sync_to_async(lb.check_parameter)(params, secret.tenant)

    # check for custom logo
    if Parameter.LOGO not in params:
        try:
            if secret.tenant.asset and secret.tenant.asset.logo:
                params["logo"] = secret.tenant.asset.logo_url
        except Asset.DoesNotExist:
            pass

    # check for custom slide
    if request.method == "GET":
        try:
            if secret.tenant.asset and secret.tenant.asset.slide:
                body = await sync_to_async(lb.get_slide_body_for_post)(secret)
                request.method = "POST"
        except Asset.DoesNotExist:
            pass

    response = await pass_through(request, endpoint, params, node, body=body)

    defaults = {
        "id": meeting_id,
        "secret": secret,
        "node": node,
        "room_name": params.get("name", "Unknown")
    }

    obj, created = await sync_to_async(Meeting.objects.get_or_create)(id=meeting_id, secret=secret, defaults=defaults)

    if created:
        await lb.update_create_metrics(secret, node)

    return response


# for endpoints without manipulations of b3lb
async def pass_through(request, endpoint, params, node, body=None):
    url = "{}{}".format(node.api_base_url, lb.get_endpoint_str(endpoint, params, node.secret))

    async with aiohttp.ClientSession() as session:
        if request.method == "POST":
            async with session.post(URL(url, encoded=True), data=body) as res:
                return HttpResponse(await res.text(), status=res.status, content_type=res.headers.get('content-type', 'text/html'))
        else:
            async with session.get(URL(url, encoded=True)) as res:
                return HttpResponse(await res.text(), status=res.status, content_type=res.headers.get('content-type', 'text/html'))


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
