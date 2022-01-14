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
from rest.models import Meeting


@require_http_methods(["GET"])
def backend_end_meeting_callback(request):
    """
    Custom callback URL for end meeting.
    """
    parameters = request.GET
    print(parameters)
    if "nonce" not in parameters:
        return HttpResponse("Unauthorized", status=401)

    try:
        meeting = Meeting.objects.get(end_nonce=parameters["nonce"])
        requests.get(meeting.end_callback_url)
        meeting.is_running = False
        meeting.save()
    except Meeting.DoesNotExist:
        print("No Meeting found")

    return HttpResponse(status=204)
