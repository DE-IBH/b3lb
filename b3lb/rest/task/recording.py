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
from django.template.loader import render_to_string
from os import makedirs, path
from requests import get
from rest.models import Record, RecordSet, RecordProfile, SecretRecordProfileRelation
from shlex import split
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
    record, created = Record.objects.get_or_create(record_set=record_set, profile=record_profile)

    # generate backend record_profile (docker-compose.yml) in tmpdir
    with open(f"{tempdir}/docker-compose.yml", "w") as docker_file:
        docker_file.write(render_to_string(template_name=f"render/{record_profile.backend_profile}", context={"tmpdir": f"{tempdir}", "extension": record_profile.file_extension, "commands": split(record_profile.command)}))

    # unpack tar to IN folder
    Popen(["tar", "-xf", f"{tempdir}/raw.tar", "-C", f"{tempdir}/in/"], stdin=DEVNULL, stdout=PIPE, close_fds=True).wait()

    # render with given record_profile
    Popen(["docker-compose", "-f", f"{tempdir}/docker-compose.yml", "up"]).wait()

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
    with TemporaryDirectory(dir="/data") as tempdir:
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
        if record_set.status != RecordSet.DELETING and record_set.created_at < tz.now() - tz.timedelta(days=record_set.secret.tenant.records_hold_time):
            record_set.status = RecordSet.DELETING
            record_set.save()
    for record_set in RecordSet.objects.filter(status=RecordSet.DELETING):
        for record in Record.objects.filter(record_set=record_set):
            record.delete()
        record_set.delete()
    return True
