#!/usr/bin/env python3

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


import os
import io
import requests
import subprocess as sp
import sys
import tarfile


if len(sys.argv) < 2:
    exit()

B3LB_BASE_DOMAIN = "https://api-test.bbbconf.de/"
B3LB_SITE_SLUG = "b3lb"
PUBLISH_FOLDER = "/var/bigbluebutton/published/presentation"
published_presentations = os.listdir(PUBLISH_FOLDER)
os.chdir(PUBLISH_FOLDER)

internal_meeting_id = sys.argv[1]
if internal_meeting_id not in published_presentations:
    exit()

tar_file = io.BytesIO()

with open("/var/log/bigbluebutton/post_publish.log", "a") as f:
    f.write("B3LB Start Upload routine for {} received\n".format(internal_meeting_id))
    tar = tarfile.open(fileobj=tar_file, mode="w|xz")
    tar.add(internal_meeting_id)
    tar.close()

    response = requests.post("{}b3lb/b/record/upload".format(B3LB_BASE_DOMAIN), files={"file": tar_file.getvalue()}, data={"file_name": internal_meeting_id})

    if response.status_code == 204:
        f.write("B3LB Upload successful. Deleting record {}\n".format(internal_meeting_id))
        sp.check_output(["bbb-record", "--delete", internal_meeting_id])
    else:
        f.write("B3LB Upload failed. Keeping record files {}\n".format(internal_meeting_id))
