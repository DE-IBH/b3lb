#!/usr/bin/env python3

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

from datetime import datetime, timedelta
import urllib
import xml.etree.ElementTree as ET
import subprocess as sp
import hashlib
import urllib.request as request

MEETING_TIMEOUT = timedelta(hours=12)

api_url = ""
api_secret = ""

pipeout = sp.check_output(['bbb-conf', '--secret']).decode('utf-8').split("\n")
for line in pipeout:
    if line.find("URL: ") != -1:
        api_url = line.split("URL: ")[1]
    elif line.find("Secret: ") != -1:
        api_secret = line.split("Secret: ")[1]


def build_url(endpoint, params={}):
    p = urllib.parse.urlencode(params)

    sha_1 = hashlib.sha1()
    sha_1.update("{}{}{}".format(endpoint, p, api_secret).encode())

    params['checksum'] = sha_1.hexdigest()

    return "{}api/{}?{}".format(api_url, endpoint, urllib.parse.urlencode(params))


url = build_url("getMeetings")

try:
    xml = ET.fromstring(request.urlopen(url).read().decode('utf-8'))
except Exception as e:
    print("Failed to contact API endpoint {}: {}".format(url, e))
    exit(1)

for child in xml:
    if child.tag == "meetings":
        for meeting in child:
            mtags = {}
            for child in meeting:
                if child.tag in ['meetingName', 'meetingID', 'startTime', 'moderatorPW']:
                    if child.tag.endswith('Time'):
                        if child.text != "0":
                            mtags[child.tag] = datetime.fromtimestamp(
                                int(child.text)/1000)
                    else:
                        mtags[child.tag] = child.text

            if 'startTime' in mtags and 'meetingID' in mtags and 'moderatorPW' in mtags:
                to = datetime.now() - mtags['startTime']
                if to > MEETING_TIMEOUT:
                    print("Killing '{}' running for '{}'".format(
                        mtags['meetingName'], to))
                    url = build_url(
                        "end", {'meetingID': mtags['meetingID'], 'password': mtags['moderatorPW']})
                    try:
                        result = request.urlopen(url).read().decode('utf-8')
                    except Exception as e:
                        print(" => {}".format(e))
