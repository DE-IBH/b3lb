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
import subprocess as sp
from django.core.files.base import ContentFile
from rest.models import Record, RecordProfile, RecordSet
from django.conf import settings as st
from tempfile import TemporaryDirectory


def celery_render_records(record_set=RecordSet()):
    # Create temporary dir
    # ToDo:
    #   ignore_cleanup_errors is only availabe in python 3.10+, but pypy version is python 3.7
    #   implement when using python 3.10+ in pypy docker
    with TemporaryDirectory(prefix=f"{st.B3LB_RECORD_RENDER_WORK_DIR}/") as temp_dir:
        # Save and unpack raw files
        with open(f"{temp_dir}/raw.tar", "wb") as tar_file:
            tar_file.write(record_set.recording_archive.open().read())

        # unpack raw tar file
        sp.check_output(["tar", "-xf", "raw.tar"], cwd=temp_dir)

        # run rendering
        record_profiles = RecordProfile.objects.all()
        for record_profile in record_profiles:
            # rendering command
            sp.check_output(record_profile.command.split(" "), cwd=temp_dir)

            # ToDo
            #   remove development command
            sp.check_output(["cp", "video.mp4", temp_dir], cwd=st.B3LB_RECORD_RENDER_WORK_DIR)

            # ToDo:
            #   Replace with real rendering and
            video_file_name = "video"
            video_path = f"{temp_dir}/{video_file_name}{record_profile.file_extension}"

            if os.path.isfile(video_path):
                video = open(video_path, "rb")
                record = Record.objects.get_or_create(record_set=record_set, profile=record_profile)[0]
                record.file.save(name=f"{record.record_set.file_path}/{record.uuid}.{record_profile.file_extension}", content=ContentFile(video.read()))
