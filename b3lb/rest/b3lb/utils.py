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

# This function file contains functions without import of b3lb files to prevent circular imports
from db_file_storage.storage import DatabaseFileStorage
from django.http import HttpResponse
from wsgiref.util import FileWrapper
import re

storage = DatabaseFileStorage()
forwarded_host_regex = re.compile(r'([^:]+)(:\d+)?$')


def get_file_response_from_storage(file_name):
    try:
        stored_file = storage.open(file_name)
    except Exception:
        return HttpResponse("Not Found", status=404)

    response = HttpResponse(FileWrapper(stored_file), content_type=stored_file.mimetype)
    response['Content-Length'] = stored_file.tell()

    return response


def get_file_from_storage(file_name):
    try:
        return storage.open(file_name).file.read()
    except Exception:
        return None


def get_forwarded_host(request):
    forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST'))
    return forwarded_host_regex.sub(r'\1', forwarded_host)


def xml_escape(string):
    if isinstance(string, str):
        escape_symbols = [
            ("&", "&amp;"),
            ("<", "&lt;"),
            (">", "&gt;"),
            ("'", "&apos;"),
            ('"', "&quot;")
        ]
        for symbol, escape in escape_symbols:
            string = string.replace(symbol, escape)
        return string
    else:
        return ""
