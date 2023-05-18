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

from asgiref.sync import sync_to_async
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseNotFound, HttpRequest, HttpResponseForbidden, HttpResponseBadRequest, FileResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db.utils import OperationalError
from django.views.decorators.http import require_http_methods
from rest.classes.api import ClientB3lbRequest, NodeB3lbRequest
from rest.classes.storage import DBStorage
from rest.models import Asset, Record


async def bbb_entrypoint(request: HttpRequest, endpoint: str = "", slug: str = "", sub_id: int = 0) -> HttpResponse:
    """
    Entrypoint for 'official' BigBlueButton API endpoints.
    """
    b3lb = ClientB3lbRequest(request, endpoint)

    # async: workaround for @require_http_methods decorator
    if not b3lb.is_allowed_method():
        return HttpResponseNotAllowed(b3lb.allowed_methods())

    await b3lb.set_secret_by_slug_and_slug_id(slug, sub_id)
    if not await sync_to_async(b3lb.is_authorized)():
        return HttpResponse("Unauthorized", status=401)
    return await b3lb.endpoint_delegation()

# async: workaround for @csrf_exempt decorator
bbb_entrypoint.csrf_exempt = True


@require_http_methods(["GET"])
def ping(request: HttpRequest):
    # ping function for monitoring checks
    # using django db connection check for validation
    try:
        connection.ensure_connection()
        return HttpResponse('OK!', content_type="text/plain")
    except OperationalError:
        return HttpResponse('Doh!', content_type="text/plain", status=503)


# Statistic endpoint for tenants
async def stats(request: HttpRequest, slug: str = "", sub_id: int = 0) -> HttpResponse:
    b3lb = ClientB3lbRequest(request, "b3lb_stats")

    # async: workaround for @require_http_methods decorator
    if not b3lb.is_allowed_method():
        return HttpResponseNotAllowed(b3lb.allowed_methods())

    b3lb.set_secret_by_slug_and_slug_id(slug, sub_id)
    return await b3lb.endpoint_delegation()


# Metric endpoint for tenants
# secured via tenant auth token
async def metrics(request: HttpRequest, slug: str = "", sub_id: int = 0) -> HttpResponse:
    b3lb = ClientB3lbRequest(request, "b3lb_metrics")

    # async: workaround for @require_http_methods decorator
    if not b3lb.is_allowed_method():
        return HttpResponseNotAllowed(b3lb.allowed_methods())

    b3lb.set_secret_by_slug_and_slug_id(slug, sub_id)
    return await b3lb.endpoint_delegation()


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


# Endpoint for getting custom css for meeting
# no default security
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


@require_http_methods(['GET'])
def recording(request: HttpRequest, nonce: str = "") -> FileResponse:
    """
    Endpoint for downloading recording video files.
    No security like on BigBlueButton Nodes.
    """
    if not nonce:
        return FileResponse()

    try:
        record = Record.objects.get(nonce=nonce)
    except ObjectDoesNotExist:
        return FileResponse()

    return FileResponse(record.file.open(), as_attachment=True, filename=f"video.{record.profile.file_extension}")


async def backend_endpoint(request: HttpRequest, backend: str, endpoint: str) -> HttpResponse:
    """
    Entrypoint for backend API endpoints.
    """
    b3lb = NodeB3lbRequest(request, backend, endpoint)

    if not b3lb.is_allowed_endpoint():
        return HttpResponseForbidden()

    # async: workaround for @require_http_methods decorator
    if not b3lb.is_allowed_method():
        return HttpResponseNotAllowed(b3lb.allowed_methods())
    return await b3lb.endpoint_delegation()

# async: workaround for @csrf_exempt decorator
backend_endpoint.csrf_exempt = True
