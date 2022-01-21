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
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from rest.models import Meeting, RecordSet


@require_http_methods(["GET"])
def backend_end_meeting_callback(request):
    """
    Custom callback URL for end meeting.
    """
    parameters = request.GET
    if "end_nonce" not in parameters:
        return HttpResponse(status=204)
    try:
        meeting = Meeting.objects.get(id=parameters["meetingID"], end_nonce=parameters["end_nonce"])
        if meeting.end_callback_url:
            url_postfix = "meetingID={}&recordingmarks={}".format(parameters["meetingID"], parameters["recordingmarks"])
            if "?" in meeting.end_callback_url:
                url = "{}&{}".format(meeting.end_callback_url, url_postfix)
            else:
                url = "{}?{}".format(meeting.end_callback_url, url_postfix)
            requests.get(url)
        if parameters["recordingmarks"] == "false":
            try:
                record_set = RecordSet.objects.get(secret=meeting.secret, meeting_id=parameters["meetingID"], nonce=parameters["nonce"])
                record_set.delete()
            except RecordSet.DoesNotExist:
                pass
        meeting.delete()
    except Meeting.DoesNotExist:
        pass
    return HttpResponse(status=204)
