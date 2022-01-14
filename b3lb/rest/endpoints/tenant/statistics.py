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

from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from rest.models import SecretMetricsList
import rest.endpoints.b3lb.lb as lb
import rest.utils as utils
import rest.endpoints.b3lb.endpoints as ep


@require_http_methods(["GET"])
def statistic_stats(request, slug=None, sub_id=0):
    """
    Statistics for specific tenant.
    Secured via AuthToken.
    """
    auth_token = request.headers.get('Authorization')
    tenant = lb.get_request_tenant(request, slug, sub_id)

    if auth_token and tenant and auth_token == tenant.stats_token:
        return HttpResponse(ep.tenant_stats(tenant), content_type='application/json')
    else:
        return HttpResponse("Unauthorized", status=401)


# Metric endpoint for tenants
# secured via auth token
@require_http_methods(["GET"])
def statistic_metrics(request, slug=None, sub_id=0):
    """
    Prometheus Metrics for specific Tenant.
    Secured via AuthToken.
    """
    forwarded_host = utils.get_forwarded_host(request)
    auth_token = request.headers.get('Authorization')
    secret = lb.get_request_secret(request, slug, sub_id)

    if forwarded_host == settings.B3LB_API_BASE_DOMAIN and slug is None:
        return HttpResponse(SecretMetricsList.objects.get(secret=None).metrics, content_type='text/plain')
    elif auth_token and secret and auth_token == secret.tenant.stats_token:
        return HttpResponse(SecretMetricsList.objects.get(secret=secret).metrics, content_type='text/plain')
    else:
        return HttpResponse("Unauthorized", status=401)
