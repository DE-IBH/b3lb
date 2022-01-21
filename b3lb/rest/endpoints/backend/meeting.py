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
    print(parameters)
    print(parameters["recordingmarks"])
    print(parameters.get("recordingmarks"))
    if "end_nonce" not in parameters:
        return HttpResponse("Unauthorized", status=401)
    try:
        meeting = Meeting.objects.get(id=parameters["meetingID"], end_nonce=parameters["end_nonce"])
        print("Meeting end url: {}".format(meeting.end_callback_url))
        if meeting.end_callback_url:
            print("send meeting end callback to original url")
            requests.get(meeting.end_callback_url)
        print("check recordingmarks")
        if parameters["recordingmarks"] == "false":
            try:
                record_set = RecordSet.objects.get(secret=meeting.secret, meeting_id=parameters["meetingID"], nonce=parameters["nonce"])
                print("delete RecordSet with uuid: {}".format(record_set.uuid))
                record_set.delete()
            except RecordSet.DoesNotExist:
                pass
        meeting.delete()
    except Meeting.DoesNotExist:
        print("No meeting found")
    return HttpResponse(status=204)
