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


from base64 import b32encode
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.conf import settings
from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.utils import timezone
from django.utils.crypto import get_random_string
from _hashlib import HASH
from math import pow
from os.path import join as path_join
from re import match
from rest.parameters import SET, OVERRIDE, MODE_CHOICES, PARAMETER_REGEXES, PARAMETER_CHOICES
from rest.b3lb.utils import xml_escape
from rest.classes.statistics import MeetingStats
from rest.classes.storage import DBStorage
from storages.backends.s3 import ClientError, S3Storage
from textwrap import wrap
from typing import Any, Dict, List
import rest.b3lb.constants as cst
import uuid as uid


#
# FUNCTIONS
#
def get_nonce():
    return get_random_string(cst.NONCE_LENGTH, cst.NONCE_CHAR_POOL)


def get_storage():
    if settings.B3LB_RECORD_STORAGE == "local":
        used_storage = FileSystemStorage()
    elif settings.B3LB_RECORD_STORAGE == "s3":
        used_storage = S3Storage()
        used_storage.access_key = settings.B3LB_S3_ACCESS_KEY
        used_storage.secret_key = settings.B3LB_S3_SECRET_KEY
        used_storage.endpoint_url = settings.B3LB_S3_ENDPOINT_URL
        used_storage.url_protocol = settings.B3LB_S3_URL_PROTOCOL
        used_storage.bucket_name = settings.B3LB_S3_BUCKET_NAME
    else:
        used_storage = default_storage
    return used_storage


#
# MODELS
#
class Cluster(models.Model):
    SHA_CHOICES = [(cst.SHA1, cst.SHA1), (cst.SHA256, cst.SHA256), (cst.SHA384, cst.SHA384), (cst.SHA512, cst.SHA512)]

    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    name = models.CharField(max_length=100, help_text="cluster name", unique=True)
    load_a_factor = models.FloatField(default=1.0, help_text="per attendee load factor")
    load_m_factor = models.FloatField(default=30.0, help_text="per meeting load factor")
    load_cpu_iterations = models.IntegerField(default=6, help_text="max sum iteration")
    load_cpu_max = models.IntegerField(default=5000, help_text="max cpu load")
    sha_function = models.CharField(max_length=6, choices=SHA_CHOICES, default=cst.SHA256)

    class Meta(object):
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_sha(self) -> HASH:
        return cst.SHA_BY_STRING.get(self.sha_function)()


def get_b3lb_node_default_domain():
    return settings.B3LB_NODE_DEFAULT_DOMAIN


class Node(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    slug = models.CharField(max_length=100, help_text="node hostname setting")
    domain = models.CharField(max_length=50, default=get_b3lb_node_default_domain, help_text="node domain name setting")
    secret = models.CharField(max_length=50, help_text="BBB API secret setting")
    cluster = models.ForeignKey(Cluster, on_delete=models.PROTECT, null=False)
    attendees = models.IntegerField(default=0, help_text="number of attendees metric")
    meetings = models.IntegerField(default=0, help_text="number of meetings metric")
    cpu_load = models.IntegerField(default=0, help_text="cpu load metric (base 10000)")
    has_errors = models.BooleanField(default=True, help_text="polling has detected a failure")
    maintenance = models.BooleanField(default=False, help_text="in maintenance setting")

    class Meta(object):
        ordering = ['slug']

    def __str__(self):
        return self.slug

    @property
    def api_base_url(self):
        return "{}{}.{}/{}".format(settings.B3LB_NODE_PROTOCOL, self.slug, self.domain, settings.B3LB_NODE_BBB_ENDPOINT)

    @property
    def load(self):
        if self.maintenance:
            return -2

        if self.has_errors:
            return -1

        # linear load calculation for attendees and meetings
        work_attendees = self.attendees * self.cluster.load_a_factor
        work_meetings = self.meetings * self.cluster.load_m_factor

        # calculation of synthetic cpu load
        # load is sum of each Taylor polynomial from 1 to load_cpu_iterations
        # load_cpu_iterations = 0 -> no cpu calculation
        # synthetic load will be between 0 and load_cpu_max

        work_cpu = 0.0
        if self.cluster.load_cpu_iterations > 0:
            for iteration in range(1, self.cluster.load_cpu_iterations):
                work_cpu += pow(float(self.cpu_load) / 10000.0, iteration)
            work_cpu = work_cpu * self.cluster.load_cpu_max / float(self.cluster.load_cpu_iterations)

        # return total synthetic load
        return int(work_attendees + work_meetings + work_cpu)

    @property
    def load_base_url(self):
        return "{}{}.{}/{}".format(settings.B3LB_NODE_PROTOCOL, self.slug, self.domain, settings.B3LB_NODE_LOAD_ENDPOINT)


class NodeMeetingList(models.Model):
    node = models.OneToOneField(Node, on_delete=models.CASCADE, primary_key=True)
    xml = models.TextField(default="")


def get_random_secret():
    return get_random_string(42, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')


class ClusterGroup(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    name = models.CharField(max_length=100, help_text="Cluster name", unique=True)
    description = models.CharField(max_length=255, help_text="Cluster description", null=True)

    class Meta(object):
        ordering = ['name']

    def __str__(self):
        return self.name


class ClusterGroupRelation(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    cluster_group = models.ForeignKey(ClusterGroup, on_delete=models.PROTECT)
    cluster = models.ForeignKey(Cluster, on_delete=models.PROTECT)

    class Meta(object):
        ordering = ['cluster_group']

    def __str__(self):
        return "{}|{}".format(self.cluster_group.name, self.cluster.name)


class Tenant(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    slug = models.CharField(max_length=10, validators=[RegexValidator('^[A-Z]{2,10}$')])
    description = models.CharField(max_length=256, blank=True, default="")
    stats_token = models.UUIDField(default=uid.uuid4)
    cluster_group = models.ForeignKey(ClusterGroup, on_delete=models.PROTECT)
    attendee_limit = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of attendees (soft limit, 0 = unlimited).")
    meeting_limit = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of meetings (0 = unlimited).")
    recording_enabled = models.BooleanField(default=False)
    records_hold_time = models.IntegerField(default=14, validators=[MinValueValidator(0)], help_text="Days interval before deleting records.")

    class Meta(object):
        ordering = ['slug']

    def __str__(self):
        return self.slug

    @property
    def hostname(self):
        return "{}.{}".format(str(self.slug).lower(), settings.B3LB_API_BASE_DOMAIN)


class Secret(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)
    description = models.CharField(max_length=256, blank=True, default="")
    sub_id = models.SmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(999)])
    secret = models.CharField(max_length=42, default=get_random_secret, validators=[RegexValidator(r'^[a-zA-Z0-9]{42}$')])
    secret2 = models.CharField(max_length=42, default="", blank=True, validators=[RegexValidator(r'^($|[a-zA-Z0-9]{42})$')])
    attendee_limit = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of attendees (soft limit, 0 = unlimited).")
    meeting_limit = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of meetings (0 = unlimited).")
    recording_enabled = models.BooleanField(default=True)
    records_hold_time = models.IntegerField(default=14, validators=[MinValueValidator(0)], help_text="Days interval before deleting records.")

    class Meta(object):
        ordering = ['tenant__slug', 'sub_id']
        constraints = [models.UniqueConstraint(fields=['tenant', 'sub_id'], name='unique_tenant_id_combination')]

    def __str__(self):
        return "{}-{}".format(self.tenant.slug, str(self.sub_id).zfill(3))

    @property
    def endpoint(self) -> str:
        if self.sub_id == 0:
            return f"{self.tenant.slug.lower()}.{settings.B3LB_API_BASE_DOMAIN}"
        else:
            return f"{self.tenant.slug.lower()}-{str(self.sub_id).zfill(3)}.{settings.B3LB_API_BASE_DOMAIN}"

    @property
    def is_record_enabled(self) -> bool:
        return self.recording_enabled and self.tenant.recording_enabled

    @property
    def records_effective_hold_time(self) -> int:
        if 0 in [self.records_hold_time, self.tenant.records_hold_time]:
            return max(self.records_hold_time, self.tenant.records_hold_time)
        else:
            return min(self.records_hold_time, self.tenant.records_hold_time)

    @property
    def secrets(self) -> List[str]:
        # returns all secrets for secret rollover use-cases
        return [self.secret, self.secret2]


class AssetSlide(models.Model):
    blob = models.BinaryField()
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=100)


class AssetLogo(models.Model):
    blob = models.BinaryField()
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=50)


class AssetCustomCSS(models.Model):
    blob = models.BinaryField()
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=50)


class Asset(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, primary_key=True)
    slide = models.FileField(upload_to='rest.AssetSlide/blob/filename/mimetype', blank=True, null=True)
    slide_filename = models.CharField(max_length=250, blank=True, null=True)
    logo = models.FileField(upload_to='rest.AssetLogo/blob/filename/mimetype', blank=True, null=True)
    custom_css = models.FileField(upload_to='rest.AssetCustomCSS/blob/filename/mimetype', blank=True, null=True)

    @property
    def s_filename(self):
        if self.slide_filename:
            return xml_escape(self.slide_filename)
        elif self.slide:
            return xml_escape("{}.{}".format(self.tenant.slug.lower(), self.slide.name.split(".")[-1]))
        else:
            return '""'

    @property
    def custom_css_url(self) -> str:
        return f"https://{settings.B3LB_API_BASE_DOMAIN}/b3lb/t/{self.tenant.slug.lower()}/css"

    @property
    def logo_url(self) -> str:
        return f"https://{settings.B3LB_API_BASE_DOMAIN}/b3lb/t/{self.tenant.slug.lower()}/logo"

    @property
    def slide_url(self) -> str:
        return f"https://{settings.B3LB_API_BASE_DOMAIN}/b3lb/t/{self.tenant.slug.lower()}/slide"

    @property
    def slide_base64(self) -> str:
        if self.slide:
            return DBStorage().get_base64(self.slide.name)
        return ""

    class Meta(object):
        ordering = ['tenant__slug']

    def __str__(self):
        return self.tenant.slug


class SecretMeetingList(models.Model):
    secret = models.OneToOneField(Secret, on_delete=models.CASCADE, primary_key=True)
    xml = models.TextField(default="")


class SecretMetricsList(models.Model):
    secret = models.OneToOneField(Secret, on_delete=models.CASCADE, unique=True, null=True)
    metrics = models.TextField(default="")

    def __str__(self):
        if self.secret:
            return self.secret.__str__()
        else:
            return "<<total>>"


# meeting - tenant - node relation class
class Meeting(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    id = models.CharField(max_length=cst.MEETING_ID_LENGTH)
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE)
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    room_name = models.CharField(max_length=cst.MEETING_NAME_LENGTH)
    age = models.DateTimeField(default=timezone.now)
    attendees = models.SmallIntegerField(default=0)
    end_callback_url = models.URLField(default="")
    listenerCount = models.SmallIntegerField(default=0)
    nonce = models.CharField(max_length=cst.NONCE_LENGTH, default=get_nonce, editable=False, unique=True)
    voiceParticipantCount = models.SmallIntegerField(default=0)
    moderatorCount = models.SmallIntegerField(default=0)
    videoCount = models.SmallIntegerField(default=0)
    bbb_origin = models.CharField(max_length=255, default="")
    bbb_origin_server_name = models.CharField(max_length=255, default="")

    class Meta(object):
        ordering = ['secret__tenant', 'age']
        constraints = [UniqueConstraint(fields=['id', 'secret'], name='unique_meeting')]

    def __str__(self):
        return "{} {}".format(self.secret.tenant.slug, self.room_name)


# Meeting - Secret - Recording relation class
class RecordSet(models.Model):
    UNKNOWN = "UNKNOWN"
    UPLOADED = "UPLOADED"
    RENDERED = "RENDERED"
    DELETING = "DELETING"

    STATUS_CHOICES = [
        (UNKNOWN, "Recording state is unknown or meeting is running"),
        (UPLOADED, "Recording file has been uploaded"),
        (RENDERED, "Recordings have been rendered to video files"),
        (DELETING, "Recordings will be deleted"),
    ]

    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE)
    meeting = models.ForeignKey(Meeting, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    recording_archive = models.FileField(storage=get_storage)
    recording_ready_origin_url = models.URLField(default="")
    nonce = models.CharField(max_length=cst.NONCE_LENGTH, default=get_nonce, editable=False, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="UNKNOWN")
    file_path = models.CharField(max_length=50)

    # information from metadata.xml and Meeting
    meta_bbb_origin = models.CharField(max_length=20, default="")
    meta_bbb_origin_version = models.CharField(max_length=20, default="")
    meta_bbb_origin_server_name = models.CharField(max_length=50, default="")
    meta_is_breakout = models.BooleanField(default=False)
    meta_end_callback_url = models.URLField(default="")
    meta_meeting_id = models.CharField(max_length=cst.MEETING_ID_LENGTH, default="")
    meta_meeting_name = models.CharField(max_length=cst.MEETING_NAME_LENGTH, default="")
    meta_start_time = models.CharField(max_length=14, default="")
    meta_end_time = models.CharField(max_length=14, default="")
    meta_participants = models.SmallIntegerField(default=0)

    def get_raw_size(self) -> int:
        try:
            return self.recording_archive.size
        except FileNotFoundError:
            return 0
        except FileExistsError:
            return 0
        except ValueError:
            return 0
        except ClientError:
            return 0


    def delete(self, using=None, keep_parents=False):
        try:
            self.recording_archive.delete()
            super().delete()
        except NotImplementedError:
            super().delete()
        except:
            pass

    def __str__(self):
        return f"{self.secret.__str__()} | {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base32 = b32encode(self.uuid.bytes)[:26].lower().decode("utf-8")
        path = wrap(base32, settings.B3LB_RECORD_PATH_HIERARCHY_WIDTH)[:settings.B3LB_RECORD_PATH_HIERARCHY_DEPHT]
        path.append(base32[settings.B3LB_RECORD_PATH_HIERARCHY_WIDTH * settings.B3LB_RECORD_PATH_HIERARCHY_DEPHT:])
        self.file_path = path_join("record", *path)


class RecordProfile(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    description = models.CharField(max_length=cst.RECORD_PROFILE_DESCRIPTION_LENGTH)
    name = models.CharField(max_length=32, unique=True)
    width = models.IntegerField(default=1920, help_text="width of video")
    height = models.IntegerField(default=1080, help_text="height of video")
    webcam_size = models.IntegerField(default=0, help_text="percentual size of webcam in video")
    crop_webcam = models.BooleanField(default=False)
    stretch_webcam = models.BooleanField(default=False)
    backdrop = models.CharField(max_length=255, default="")
    annotations = models.BooleanField(default=True, help_text="Show annotations in video")
    mime_type = models.CharField(max_length=32, default="video/mp4", help_text="video mime type, can be 'video/mp4' or 'video/webm'")
    file_extension = models.CharField(max_length=10, default="mp4", help_text="video format, can be 'mp4' or 'webm'")
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class SecretRecordProfileRelation(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE)
    record_profile = models.ForeignKey(RecordProfile, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.secret.__str__()}-{self.record_profile.__str__()}"


class Record(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    file = models.FileField(storage=get_storage)
    profile = models.ForeignKey(RecordProfile, on_delete=models.PROTECT, null=True)
    name = models.CharField(max_length=cst.RECORD_PROFILE_DESCRIPTION_LENGTH + cst.MEETING_NAME_LENGTH + 3)
    gl_listed = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    record_set = models.ForeignKey(RecordSet, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(default=timezone.now)
    nonce = models.CharField(max_length=cst.NONCE_LENGTH, default=get_nonce, editable=False, unique=True)

    def get_file_size(self) -> int:
        try:
            return self.file.size
        except FileNotFoundError:
            return 0
        except FileExistsError:
            return 0
        except ValueError:
            return 0
        except ClientError:
            return 0

    def delete(self, using=None, keep_parents=False):
        try:
            self.file.delete()
            super().delete()
        except NotImplementedError:
            super().delete()
        except:
            pass

    def get_recording_dict(self) -> Dict[str, Any]:
        if self.published:
            state = "published"
        else:
            state = "unpublished"

        if self.gl_listed:
            gl_listed = "true"
        else:
            gl_listed = "false"

        video_length = int((int(self.record_set.meta_end_time) - int(self.record_set.meta_start_time)) / 60000.)  # milliseconds to minutes

        record_dict = {
            "uuid": str(self.uuid),
            "meeting_id": self.record_set.meta_meeting_id,
            "internal_meeting_id": self.record_set.meta_meeting_id,
            "name": self.name,
            "is_breakout": self.record_set.meta_is_breakout,
            "gl_listed": gl_listed,
            "published": self.published,
            "state": state,
            "start_time": self.record_set.meta_start_time,
            "end_time": self.record_set.meta_end_time,
            "participants": self.record_set.meta_participants,
            "raw_size": self.record_set.get_raw_size(),
            "bbb_origin": self.record_set.meta_bbb_origin,
            "bbb_origin_server_name": self.record_set.meta_bbb_origin_server_name,
            "bbb_origin_version": self.record_set.meta_bbb_origin_version,
            "end_callback_url":  self.record_set.meta_end_callback_url,
            "meeting_name": self.record_set.meta_meeting_name,
            "video_size": self.get_file_size(),
            "video_url": f"https://{settings.B3LB_API_BASE_DOMAIN}/b3lb/r/{self.nonce}",
            "video_length": video_length  # ToDo: Get length of video via routine?
        }
        return record_dict

    def __str__(self):
        return f"{self.record_set.__str__()} | {self.profile.name}"


class Stats(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    tenant = models.ForeignKey(Tenant, null=True, on_delete=models.CASCADE)
    attendees = models.IntegerField(default=0)
    meetings = models.IntegerField(default=0)
    listenerCount = models.IntegerField(default=0)
    voiceParticipantCount = models.IntegerField(default=0)
    moderatorCount = models.IntegerField(default=0)
    videoCount = models.IntegerField(default=0)
    bbb_origin = models.CharField(max_length=255, default="")
    bbb_origin_server_name = models.CharField(max_length=255, default="")

    class Meta(object):
        ordering = ['tenant']

    def update_values(self, meeting: MeetingStats):
        self.attendees = meeting.attendees
        self.meetings = meeting.meetings
        self.listenerCount = meeting.listener_count
        self.moderatorCount = meeting.moderator_count
        self.videoCount = meeting.video_count
        self.save()

    def __str__(self):
        return "{}: {} ({})".format(self.tenant.slug, self.bbb_origin_server_name, self.bbb_origin)


class Metric(models.Model):
    ATTENDEES = "attendees"
    LISTENERS = "listeners"
    VOICES = "voices"
    VIDEOS = "videos"
    MEETINGS = "meetings"
    JOINED = "attendees_total"
    CREATED = "meetings_total"
    DURATION_COUNT = "meeting_duration_seconds_count"
    DURATION_SUM = "meeting_duration_seconds_sum"
    ATTENDEE_LIMIT_HITS = "attendee_limit_hits"
    MEETING_LIMIT_HITS = "meeting_limit_hits"

    GAUGES = [
        ATTENDEES,
        LISTENERS,
        VOICES,
        VIDEOS,
        MEETINGS
    ]

    NAME_CHOICES = [
        (ATTENDEES, "Total number of current attendees"),
        (LISTENERS, "Total number of current listeners"),
        (VOICES, "Total number of current voice participants"),
        (VIDEOS, "Total number of current video participants"),
        (MEETINGS, "Total number of running meetings"),
        (JOINED, "Number of attendees that have joined"),
        (CREATED, "Number of meetings that have been created"),
        (DURATION_COUNT, "Total number of meeting durations"),
        (DURATION_SUM, "Sum of meeting durations"),
        (ATTENDEE_LIMIT_HITS, "Number of attendee limit hits"),
        (MEETING_LIMIT_HITS, "Number of meeting limit hits")
    ]

    name = models.CharField(max_length=64, choices=NAME_CHOICES)
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE)
    node = models.ForeignKey(Node, on_delete=models.CASCADE, null=True)
    value = models.BigIntegerField(default=0)

    class Meta(object):
        constraints = [
            models.UniqueConstraint(fields=['name', 'secret', 'node'], name="unique_metric")
        ]


class Parameter(models.Model):
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    parameter = models.CharField(max_length=64, choices=PARAMETER_CHOICES)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    value = models.CharField(max_length=250, blank=True, null=True)

    def clean_fields(self, exclude=None):
        if self.mode in [SET, OVERRIDE]:
            if not (self.value and match(PARAMETER_REGEXES[self.parameter], self.value)):
                raise ValidationError(f'Value must have the format "{PARAMETER_REGEXES[self.parameter]}"!', params={'value': self.value})

    class Meta(object):
        constraints = [models.UniqueConstraint(fields=['parameter', 'tenant'], name="unique_parameter")]
