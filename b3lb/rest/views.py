# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2022 IBH IT-Service GmbH
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

from asgiref.sync import sync_to_async
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseNotFound, HttpRequest
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import connection
from django.db.utils import OperationalError
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from requests import get
from rest.classes.api import B3LBRequest
from rest.classes.storage import DBStorage
from rest.models import Asset, Meeting, RecordSet, SecretMetricsList, SecretRecordProfileRelation
from rest.tasks import render_record


async def bbb_entrypoint(request: HttpRequest, endpoint: str = "", slug: str = "", sub_id: int = 0) -> HttpResponse:
    """
    Entrypoint for 'official' BigBlueButton API endpoints.
    """
    b3lb = B3LBRequest(request, endpoint)

    # async: workaround for @require_http_methods decorator
    if not b3lb.is_allowed_method():
        return HttpResponseNotAllowed(b3lb.allowed_methods())

    await sync_to_async(b3lb.set_secret_by_slug_and_slug_id)(slug, sub_id)

    if not await sync_to_async(b3lb.is_authorized)():
        return HttpResponse("Unauthorized", status=401)

    return await b3lb.endpoint_delegation()
    # if endpoint in LEGAL_ENDPOINTS:
    #     if endpoint in WHITELISTED_ENDPOINTS:
    #         return await requested_endpoint(b3lb)
    #     elif endpoint == "getRecordingTextTracks":
    #         return HttpResponse(ct.RETURN_STRING_GET_RECORDING_TEXT_TRACKS_NOTHING_FOUND_JSON)
    #     elif endpoint == "getRecordings":
    #         return HttpResponse(ct.RETURN_STRING_GET_RECORDING_NO_RECORDINGS)
    #     else:
    #         response = HttpResponse()
    #         response.status_code = 403
    #         return response
    # else:
    #     return HttpResponseForbidden()

# async: workaround for @csrf_exempt decorator
bbb_entrypoint.csrf_exempt = True


@require_http_methods(["GET"])
def ping(request: HttpRequest):
    # ping function for monitoring checks
    try:
        connection.ensure_connection()
        return HttpResponse('OK!', content_type="text/plain")
    except OperationalError:
        return HttpResponse('Doh!', content_type="text/plain", status=503)


# Statistic endpoint for tenants
# secured via tenant auth token
@require_http_methods(["GET"])
def stats(request: HttpRequest, slug: str = "", sub_id: int = 0) -> HttpResponse:
    b3lb = B3LBRequest(request, "")
    b3lb.set_secret_by_slug_and_slug_id(slug, sub_id)
    auth_token = request.headers.get("Authorization", "")

    if auth_token and b3lb.secret and b3lb.secret.tenant and auth_token == str(b3lb.secret.tenant.stats_token):
        return HttpResponse(b3lb.get_tenant_statistic(), content_type='application/json')
    else:
        return HttpResponse("Unauthorized", status=401)


# Metric endpoint for tenants
# secured via tenant auth token
@require_http_methods(["GET"])
def metrics(request, slug: str = "", sub_id: int = 0) -> HttpResponse:
    b3lb = B3LBRequest(request, "")
    b3lb.set_secret_by_slug_and_slug_id(slug, sub_id)
    auth_token = b3lb.request.headers.get('Authorization', "")

    print(auth_token)
    if b3lb.get_forwarded_host() == settings.B3LB_API_BASE_DOMAIN and slug is None:
        return HttpResponse(SecretMetricsList.objects.get(secret=None).metrics, content_type='text/plain')
    elif auth_token and b3lb.secret and auth_token == str(b3lb.secret.tenant.stats_token):
        return HttpResponse(SecretMetricsList.objects.get(secret=b3lb.secret).metrics, content_type='text/plain')
    else:
        return HttpResponse("Unauthorized", status=401)


# Endpoint for getting slides for meeting
# no default security
@require_http_methods(['GET'])
def slide(request: HttpRequest, slug: str = "") -> HttpResponse:
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.slide:
        storage = DBStorage()
        return storage.get_response(asset.slide.name)
    else:
        return HttpResponseNotFound()


# Endpoint for getting logos for meeting
# no default security
@require_http_methods(['GET'])
def logo(request: HttpRequest, slug=None) -> HttpResponse:
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.logo:
        storage = DBStorage()
        return storage.get_response(asset.logo.name)
    else:
        return HttpResponseNotFound()



@require_http_methods(['GET'])
def custom_css(request: HttpRequest, slug: str = "") -> HttpResponse:
    """
    Endpoint for getting custom CSS file for meeting.
    No default security.
    """
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.custom_css:
        storage = DBStorage()
        return storage.get_response(asset.custom_css.name)
    else:
        return HttpResponseNotFound()


@require_http_methods(["POST"])
@csrf_exempt
def backend_record_upload(request: HttpRequest) -> HttpResponse:
    """
    Upload for BBB record files.
    Saves file to given Storage (default, local or S3)
    """
    nonce = request.GET.get("nonce")
    uploaded_file = request.FILES.get('file')
    if nonce and uploaded_file:
        try:
            record_set = RecordSet.objects.get(nonce=nonce)
        except RecordSet.DoesNotExist:
            return HttpResponse(status=200)
        try:
            record_set.recording_archive.save(name=f"{record_set.file_path}/raw.tar", content=ContentFile(uploaded_file.read()))
        except:
            return HttpResponse("Error during file save", status=503)

        record_set.status = RecordSet.UPLOADED
        record_set.save()

        secret_record_profile_relations = SecretRecordProfileRelation.objects.filter(secret=record_set.secret)
        for secret_record_profile_relation in secret_record_profile_relations:
            render_record.apply_async(args=[record_set.uuid, secret_record_profile_relation.record_profile.uuid], queue=secret_record_profile_relation.record_profile.celery_queue)

        record_set.refresh_from_db()
        if record_set.status == record_set.UPLOADED:
            record_set.status = record_set.RENDERED
            record_set.save()

    return HttpResponse(status=200)


@require_http_methods(["GET"])
def backend_end_meeting_callback(request: HttpRequest) -> HttpResponse:
    """
    Custom callback URL for end meeting.
    """
    parameters = request.GET
    if "nonce" in parameters and "meetingID" in parameters:
        try:
            meeting = Meeting.objects.get(id=parameters["meetingID"], nonce=parameters["nonce"])
        except Meeting.DoesNotExist:
            return HttpResponse(status=204)

        if parameters.get("recordingmarks") not in ["false", "true"]:
            recording_marks = "false"
        else:
            recording_marks = parameters.get("recordingmarks")

        if meeting.end_callback_url:
            url_suffix = f"meetingID={parameters.get('meetingID')}&recordingmarks={recording_marks}"
            if "?" in meeting.end_callback_url:
                get(f"{meeting.end_callback_url}&{url_suffix}")
            else:
                get(f"{meeting.end_callback_url}?{url_suffix}")

        if recording_marks == "false":
            try:
                RecordSet.objects.get(meeting=meeting).delete()
            except RecordSet.DoesNotExist:
                pass

        meeting.delete()

    return HttpResponse(status=204)


# ToDo Add endpoint for record download.
# ..
