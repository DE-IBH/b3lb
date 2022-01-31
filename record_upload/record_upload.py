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


import sys
import os
import subprocess as sp
import tarfile
import requests

if len(sys.argv) < 2:
    exit()

B3LB_BASE_DOMAIN = "https://api-test.bbbconf.de/"
PUBLISH_FOLDER = "/var/bigbluebutton/published/presentation"

published_presentations = os.listdir(PUBLISH_FOLDER)

meeting_id = sys.argv[1]

bbb_record_listing = sp.check_output(["bbb-record", "--list"]).decode("utf-8").split("\n")[2:]

tar_filename = "{}/{}.tar.xz".format(PUBLISH_FOLDER, meeting_id)

with open("/var/log/bigbluebutton/post_publish.log", "a") as f:
    f.write("B3LB Start Upload routine for {} received\n".format(meeting_id))
    tar = tarfile.open(tar_filename, mode="w|xz")
    tar.add("{}/{}".format(PUBLISH_FOLDER, meeting_id))
    tar.close()
    f.write("B3LB Upload files compressed to {}\n".format(tar_filename))

    response = requests.post("{}b3lb/b/record/upload", files={"file": open(tar_filename, "rb")})
    f.write("B3LB Upload Response Code: {}".format(response.status_code))
