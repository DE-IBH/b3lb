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

#
# B3LB Backend API Endpoints
#

from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest.models import RecordSet


@require_http_methods(["POST"])
@csrf_exempt
def backend_record_upload(request):
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
            return HttpResponseBadRequest()

        try:
            record_set.recording_archive.save(name="{}/raw.tar".format(record_set.file_path), content=ContentFile(uploaded_file.read()))
        except:
            return HttpResponse("Error during file save", status=503)

        record_set.status = RecordSet.UPLOADED
        record_set.save()

        return HttpResponse("File uploaded successfully", status=201)
    else:
        return HttpResponseBadRequest()