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


from django.utils import timezone as tz
from os import makedirs, path
from requests import get
from rest.b3lb.make_xges import render_xges
from rest.models import Record, RecordSet, RecordProfile, SecretRecordProfileRelation
from subprocess import DEVNULL, PIPE, Popen
from tempfile import TemporaryDirectory


def render_by_profile(record_set: RecordSet, record_profile: RecordProfile, tempdir: str):
    """
    Render RecordSet with given RecordProfile in tempdir with

    tempdir/
    |__ raw.tar
    |__ in/
    |__ out/
    """
    print(f"Start rendering {record_set.__str__()} with profile {record_profile.name}")
    record, created = Record.objects.get_or_create(record_set=record_set, profile=record_profile, name=f"{record_set.meta_meeting_name} ({record_profile.description})")

    # unpack tar to IN folder
    Popen(["tar", "-xf", f"{tempdir}/raw.tar", "-C", f"{tempdir}/in/"], stdin=DEVNULL, stdout=PIPE, close_fds=True).wait()

    # generate xges file
    render_xges(f"{tempdir}/in/", f"{tempdir}/out/video.xges", record_profile)

    # render by xges file
    Popen(["ges-launch-1.0", "--load", f"{tempdir}/out/video.xges", "-o", f"{tempdir}/out/video.{record_profile.file_extension}"]).wait()

    # check result
    if not path.isfile(f"{tempdir}/out/video.{record_profile.file_extension}"):
        raise Exception("No video output")

    # create record entry
    with open(f"{tempdir}/out/video.{record_profile.file_extension}", "rb") as video_file:
        if not created:
            record.file.delete()
        record.file.save(name=f"{record_set.file_path}/{record_profile.name}.{record_profile.file_extension}", content=video_file)
    record.published = True
    record.save()
    print(f"Finished rendering {record_set.__str__()} with profile {record_profile.name}")


def render_record(record_set: RecordSet):
    if record_set.get_raw_size() == 0:
        print(f"raw.tar of {record_set.__str__()} empty or non existing!")
        return False

    # create temporary directory
    with TemporaryDirectory(dir="/srv/rendering") as tempdir:
        makedirs(f"{tempdir}/in")
        makedirs(f"{tempdir}/out")

        with open(f"{tempdir}/raw.tar", "wb") as raw:
            # download raw.tar
            raw.write(record_set.recording_archive.file.read())

            # render with profiles
            profile_relations = SecretRecordProfileRelation.objects.filter(secret=record_set.secret)
            if profile_relations.count() > 0:
                for profile_relation in profile_relations:
                    render_by_profile(record_set, profile_relation.record_profile, tempdir)
            else:
                for record_profile in RecordProfile.objects.filter(is_default=True):
                    render_by_profile(record_set, record_profile, tempdir)

    record_set.status = RecordSet.RENDERED
    record_set.save()
    if record_set.recording_ready_origin_url:
        try:
            get(record_set.recording_ready_origin_url)
        except:
            pass
    return True


def housekeeping_records():
    for record_set in RecordSet.objects.all():
        if record_set.status != RecordSet.DELETING and record_set.created_at < tz.now() - tz.timedelta(days=record_set.secret.records_effective_hold_time):
            record_set.status = RecordSet.DELETING
            record_set.save()
    for record_set in RecordSet.objects.filter(status=RecordSet.DELETING):
        for record in Record.objects.filter(record_set=record_set):
            record.delete()
        record_set.delete()
    return True
