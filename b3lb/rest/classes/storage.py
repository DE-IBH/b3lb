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

from base64 import b64encode
from db_file_storage.storage import DatabaseFileStorage
from django.http import HttpResponse
from django.db.models import ObjectDoesNotExist
from wsgiref.util import FileWrapper


# Slides in POST requests have a maximum size by the BigBlueButton API
# see: https://docs.bigbluebutton.org/dev/api.html#pre-upload-slides
#
# Based on API description, the max request size is 2MB, in practice tests it was < 1MB
#
# So the maximum base64 size was set to 1024000
# so, the max. size of slides in a POST request is 1024000 * 0.75 ~ 768kiB

MAX_BASE64_SLIDE_SIZE_IN_POST = 1024000
MAX_SLIDE_SIZE_IN_POST = MAX_BASE64_SLIDE_SIZE_IN_POST * 0.75


class DBStorage:
    storage: DatabaseFileStorage

    def get_response(self, file_name: str) -> HttpResponse:
        try:
            stored_file = self.storage.open(file_name)
        except ObjectDoesNotExist:
            return HttpResponse("Not Found", status=404)

        response = HttpResponse(FileWrapper(stored_file), content_type=stored_file.mimetype)
        response['Content-Length'] = stored_file.tell()

        return response

    def get_base64(self, file_name: str) -> str:
        try:
            stored_file = self.storage.open(file_name).file.read()
        except ObjectDoesNotExist:
            stored_file = b""

        if 0 < len(stored_file) <= MAX_SLIDE_SIZE_IN_POST:
            based_64 = b64encode(stored_file).decode()
            if len(based_64) <= MAX_BASE64_SLIDE_SIZE_IN_POST:
                return based_64
        return ""

    def __init__(self):
        self.storage = DatabaseFileStorage()
