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

from django.http import HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_http_methods
from rest.models import Asset
import rest.utils as utils


@require_http_methods(['GET'])
def asset_slide(request, slug=None):
    """
    Tenant default slide for BBB Meetings.
    """
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.slide:
        return utils.get_file_response_from_storage(asset.slide.name)
    else:
        return HttpResponseNotFound()


@require_http_methods(['GET'])
def asset_logo(request, slug=None):
    """
    Tenant logo for BBB-Meeting & Frontends.
    """
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.logo:
        return utils.get_file_response_from_storage(asset.logo.name)
    else:
        return HttpResponseNotFound()


@require_http_methods(['GET'])
def asset_custom_css(request, slug=None):
    """
    Tenant custom CSS for BBB-Meetings.
    """
    try:
        asset = Asset.objects.get(tenant__slug=slug.upper())
    except ObjectDoesNotExist:
        return HttpResponseNotFound()

    if asset.custom_css:
        return utils.get_file_response_from_storage(asset.custom_css.name)
    else:
        return HttpResponseNotFound()
