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
PUBLISH_FOLDER = "/var/bigbluebutton/published/presentation"
published_presentations = os.listdir(PUBLISH_FOLDER)

internal_meeting_id = sys.argv[1]
if internal_meeting_id not in published_presentations:
    exit()

meeting_id = ""

bbb_record_listing = sp.check_output(["bbb-record", "--list"]).decode("utf-8").split("\n")[2:]
for line in bbb_record_listing:
    if line[:2] == "--":
        break
    if line.split(" ")[0] == internal_meeting_id:
        meeting_id = line.split(" ")[-1]

tar_filename = "{}/{}.tar.xz".format(PUBLISH_FOLDER, internal_meeting_id)
tar_file = io.BytesIO()

with open("/var/log/bigbluebutton/post_publish.log", "a") as f:
    f.write("B3LB Start Upload routine for {} received\n".format(internal_meeting_id))
    tar = tarfile.open(fileobj=tar_file, mode="w|xz")
    # tar = tarfile.open(tar_filename, mode="w|xz")
    tar.add("{}/{}".format(PUBLISH_FOLDER, internal_meeting_id))
    tar.close()
    f.write("B3LB Upload files compressed.\n".format(tar_filename))

    if meeting_id:
        response = requests.post("{}b3lb/b/record/upload".format(B3LB_BASE_DOMAIN), files={"file": tar_file.getvalue()}, data={"meeting_id": meeting_id})
    else:
        response = requests.post("{}b3lb/b/record/upload".format(B3LB_BASE_DOMAIN), files={"file": tar_file.getvalue()})

    if response.status_code == 204:
        f.write("B3LB Upload successful. Deleting record {}\n".format(internal_meeting_id))
        sp.check_output(["bbb-record", "--delete", internal_meeting_id])
    else:
        f.write("B3LB Upload failed. Keeping record files {}\n".format(internal_meeting_id))
