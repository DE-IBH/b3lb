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

import os
import subprocess as sp
from rest.models import Record, RecordProfile, RecordSet
from django.conf import settings as st


def check_dir_paths(sub_folder_name):
    if not os.path.isdir(f"{st.B3LB_RECORD_RENDER_WORK_DIR}/indir/{sub_folder_name}"):
        os.makedirs(f"{st.B3LB_RECORD_RENDER_WORK_DIR}/indir/{sub_folder_name}")
    if not os.path.isdir(f"{st.B3LB_RECORD_RENDER_WORK_DIR}/outdir"):
        os.makedirs(f"{st.B3LB_RECORD_RENDER_WORK_DIR}/outdir")


def celery_render_records(record_set=RecordSet()):
    # Check if dirs exists
    check_dir_paths(record_set.uuid)

    # Save and unpack raw files
    with open(f"{st.B3LB_RECORD_RENDER_WORK_DIR}/indir/{record_set.uuid}/raw.tar", "wb") as tar_file:
        tar_file.write(record_set.recording_archive.open().read())

    sp.check_output(["tar", "-xf", "raw.tar"], cwd=f"{st.B3LB_RECORD_RENDER_WORK_DIR}/indir/{record_set.uuid}")

    # delete raw.tar
    sp.check_output(["rm", "raw.tar"], cwd=f"{st.B3LB_RECORD_RENDER_WORK_DIR}/indir/{record_set.uuid}")

    # record_profiles = RecordProfile.objects.all()
    # for record_profile in record_profiles:
    #
    #     record = Record.objects.get_or_create(record_set=record_set, profile=record_profile)
    #
    #
    #     sp.check_output(record_profile.command.split(" "), cwd=st.B3LB_RECORD_RENDER_WORK_DIR)



