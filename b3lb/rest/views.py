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

from asgiref.sync import sync_to_async
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import OperationalError
from django.conf import settings
from django.views.decorators.http import require_http_methods
from rest.models import Cluster, SecretMetricsList, Asset
import rest.b3lb.lb as lb
import rest.b3lb.utils as utils
import rest.b3lb.endpoints as ep
import rest.b3lb.constants as ct
from datetime import datetime


async def api_pass_through(request, endpoint="", slug=None, sub_id=0):
    # async: workaround for @require_http_methods decorator
    if request.method not in ["GET", "POST"]:
        return HttpResponseNotAllowed(["GET", "POST"])

    parameters = request.GET

    params = {}
    for param in parameters:
        params[param] = parameters[param]

    if "checksum" in params:
        checksum = params["checksum"]
        del params["checksum"]
    else:
        return HttpResponse("Unauthorized", status=401)

    secret = await sync_to_async(lb.get_request_secret)(request, slug, sub_id)
    if not secret:
        return HttpResponse("Unauthorized", status=401)

    if not (lb.check_tenant(secret.secret, checksum, endpoint, request.META.get("QUERY_STRING")) or lb.check_tenant(secret.secret2, checksum, endpoint, request.META.get("QUERY_STRING"))):
        return HttpResponse("Unauthorized", status=401)

    if endpoint in ep.LEGAL_ENDPOINTS:
        if endpoint in ep.WHITELISTED_ENDPOINTS:
            return await ep.requested_endpoint(secret, endpoint, request, params)
        else:
            response = HttpResponse()

            if endpoint == "getRecordingTextTracks":
                response.write(ct.RETURN_STRING_GET_RECORDING_TEXT_TRACKS_NOTHING_FOUND_JSON)
            elif endpoint == "getRecordings":
                response.write(ct.RETURN_STRING_GET_RECORDING_NO_RECORDINGS)
            else:
                response.status_code = 403

            return response
    else:
        return HttpResponseForbidden()

# async: workaround for @csrf_excempt decorator
api_pass_through.csrf_exempt = True


@require_http_methods(["GET"])
def ping(request):
    # ping function for monitoring checks
    try:
        Cluster.objects.get(name="{}".format(datetime.now().strftime("%H%M%S")))
    except ObjectDoesNotExist:
        return HttpResponse('OK!', content_type="text/plain")
    except OperationalError:
        return HttpResponse('Doh!', content_type="text/plain", status=503)


# Statistic endpoint for tenants
# secured via auth token
@require_http_methods(["GET"])
def stats(request, slug=None, sub_id=0):
    auth_token = request.headers.get('Authorization')
    tenant = lb.get_request_tenant(request, slug, sub_id)

    if auth_token and tenant and auth_token == tenant.stats_token:
        return HttpResponse(ep.tenant_stats(tenant), content_type='application/json')
    else:
        return HttpResponse("Unauthorized", status=401)


# Metric endpoint for tenants
# secured via auth token
@require_http_methods(["GET"])
def metrics(request, slug=None, sub_id=0):
    forwarded_host = utils.get_forwarded_host(request)
    auth_token = request.headers.get('Authorization')
    secret = lb.get_request_secret(request, slug, sub_id)

    if forwarded_host == settings.B3LB_API_BASE_DOMAIN and slug is None:
        return HttpResponse(SecretMetricsList.objects.get(secret=None).metrics, content_type='text/plain')
    elif auth_token and secret and auth_token == secret.tenant.stats_token:
        return HttpResponse(SecretMetricsList.objects.get(secret=secret).metrics, content_type='text/plain')
    else:
        return HttpResponse("Unauthorized", status=401)


# Endpoint for getting slides
@require_http_methods(['GET'])
def slide(request, slug=None):
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.slide:
        return utils.get_file_response_from_storage(asset.slide.name)
    else:
        return HttpResponseNotFound()


# Endpoint for getting logos
@require_http_methods(['GET'])
def logo(request, slug=None):
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.logo:
        return utils.get_file_response_from_storage(asset.logo.name)
    else:
        return HttpResponseNotFound()


# Endpoint for getting custom CSS file
@require_http_methods(['GET'])
def custom_css(request, slug=None):
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.custom_css:
        return utils.get_file_response_from_storage(asset.custom_css.name)
    else:
        return HttpResponseNotFound()
