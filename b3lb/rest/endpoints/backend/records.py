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

#
# B3LB Backend API Endpoints
#

import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest.models import RecordSet, Record


@require_http_methods(["POST"])
@csrf_exempt
def backend_record_upload(request):
    """
    Upload for BBB record files.
    Does currently nothing.
    """
    if settings.B3LB_STORAGE_USE_LOCAL_STORAGE or settings.B3LB_STORAGE_USE_S3_STORAGE:
        tar_file = request.FILES.get("file")
        tar_name = request.data.get("meeting_id")
        print(tar_name, tar_file)
        if tar_name:
            open("/upload/{}.tar.xz".format(tar_name), "wb")
        else:
            open("/upload/no_name.tar.xz".format(tar_name), "wb")
        return HttpResponse(status=204)
    else:
        return HttpResponse(status=423)
