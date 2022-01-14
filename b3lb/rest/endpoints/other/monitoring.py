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
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import OperationalError
from django.views.decorators.http import require_http_methods
from rest.models import Cluster
from datetime import datetime


@require_http_methods(["GET"])
def monitoring_ping(request):
    """
    Ping endpoint with DB connectivity test
    """
    try:
        Cluster.objects.get(name="{}".format(datetime.now().strftime("%H%M%S")))
    except ObjectDoesNotExist:
        return HttpResponse('OK!', content_type="text/plain")
    except OperationalError:
        return HttpResponse('Doh!', content_type="text/plain", status=503)
