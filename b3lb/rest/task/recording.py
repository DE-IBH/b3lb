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


from rest.b3lb.utils import load_template
from rest.models import Record, RecordSet, SecretRecordProfileRelation
from shlex import split
from subprocess import DEVNULL, PIPE, Popen
from tempfile import TemporaryDirectory
import os


def render_record(record_set: RecordSet):
    if record_set.get_raw_size() == 0:
        print(f"raw.tar of {record_set.__str__()} empty!")
        return False

    # create temporary directory
    with TemporaryDirectory(dir="/data") as tempdir:
        os.mkdir(f"{tempdir}/in")
        os.mkdir(f"{tempdir}/out")

        with open(f"{tempdir}/raw.tar", "wb") as raw:
            # download raw.tar
            raw.write(record_set.recording_archive.file.read())
            for profile_relation in SecretRecordProfileRelation.objects.filter(secret=record_set.secret):
                print(f"Start rendering {record_set.__str__()} with profile {profile_relation.record_profile.name}")
                record, created = Record.objects.get_or_create(record_set=record_set, profile=profile_relation.record_profile)

                template = load_template(f"render/{profile_relation.record_profile.backend_profile}")

                # generate backend profile (docker-compose.yml) in tmpdir
                with open(f"{tempdir}/docker-compose.yml", "w") as docker_file:
                    docker_file.write(template.render({"tmpdir": f"{tempdir}", "extension": profile_relation.record_profile.file_extension, "commands": split(profile_relation.record_profile.command)}))

                # unpack tar to IN folder
                Popen(["tar", "-xf", f"{tempdir}/raw.tar", "-C", f"{tempdir}/in/"], stdin=DEVNULL, stdout=PIPE, close_fds=True).wait()

                # render with given profile
                Popen(["docker-compose", "-f", f"{tempdir}/docker-compose.yml", "up"]).wait()

                # check result
                if not os.path.isfile(f"{tempdir}/out/video.{profile_relation.record_profile.file_extension}"):
                    raise Exception("No video output")

                # create record entry
                with open(f"{tempdir}/out/video.{profile_relation.record_profile.file_extension}", "rb") as video_file:
                    if not created:
                        record.file.delete()
                    record.file.save(name=f"{record_set.file_path}/{profile_relation.record_profile.name}.{profile_relation.record_profile.file_extension}", content=video_file)
                record.save()
                print(f"Finished rendering {record_set.__str__()} with profile {profile_relation.record_profile.name}")

    record_set.status = RecordSet.RENDERED
    record_set.save()
    return True
