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

# ToDo Use async variant instead of requests
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
    if "nonce" in parameters and "meetingID" in parameters:
        try:
            meeting = Meeting.objects.get(id=parameters["meetingID"], nonce=parameters["nonce"])

            if parameters["recordingmarks"] not in ["false", "true"]:
                recording_marks = "false"
            else:
                recording_marks = parameters["recordingmarks"]

            if meeting.end_callback_url:
                url_suffix = "meetingID={}&recordingmarks={}".format(parameters["meetingID"], recording_marks)
                if "?" in meeting.end_callback_url:
                    url = "{}&{}".format(meeting.end_callback_url, url_suffix)
                else:
                    url = "{}?{}".format(meeting.end_callback_url, url_suffix)
                requests.get(url)

            if recording_marks == "false":
                try:
                    RecordSet.objects.get(meeting=meeting).delete()
                except RecordSet.DoesNotExist:
                    pass

            meeting.delete()
        except Meeting.DoesNotExist:
            return HttpResponse(status=204)
    return HttpResponse(status=204)
