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


from django.db import models
from django.contrib import admin
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.conf import settings
import uuid as uid
import re
from math import pow
from rest.b3lb.utils import xml_escape


class Cluster(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    name = models.CharField(max_length=100, help_text="cluster name", unique=True)
    load_a_factor = models.FloatField(default=1.0, help_text="per attendee load factor")
    load_m_factor = models.FloatField(default=30.0, help_text="per meeting load factor")
    load_cpu_iterations = models.IntegerField(default=6, help_text="max sum iteration")
    load_cpu_max = models.IntegerField(default=5000, help_text="max cpu load")

    def __str__(self):
        return self.name

    class Meta(object):
        ordering = ['name']


class ClusterAdmin(admin.ModelAdmin):
    model = Cluster
    list_display = ['name', 'load_a_factor', 'load_m_factor', 'load_cpu_iterations', 'load_cpu_max']


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
    def load_base_url(self):
        return "{}{}.{}/{}".format(settings.B3LB_NODE_PROTOCOL, self.slug, self.domain, settings.B3LB_NODE_LOAD_ENDPOINT)

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


def maintenance_on(modeladmin, request, queryset):
    queryset.update(maintenance=True)


maintenance_on.short_description = "Set Node to maintenance"


def maintenance_off(modeladmin, request, queryset):
    queryset.update(maintenance=False)


maintenance_off.short_description = "Set Node to active"


class NodeAdmin(admin.ModelAdmin):
    model = Node
    list_display = ['slug', 'cluster', 'load', 'attendees', 'meetings', 'show_cpu_load', 'has_errors', 'maintenance']
    actions = [maintenance_on, maintenance_off]

    def show_cpu_load(self, obj):
        return "{:.1f} %".format(obj.cpu_load/100)

    show_cpu_load.short_description = "CPU Load"


class NodeMeetingList(models.Model):
    node = models.OneToOneField(Node, on_delete=models.CASCADE, primary_key=True)
    xml = models.TextField(default="")


class NodeMeetingListAdmin(admin.ModelAdmin):
    model = NodeMeetingList
    list_display = ['node']


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


class ClusterGroupAdmin(admin.ModelAdmin):
    model = ClusterGroup
    list_display = ['name', 'description']


class ClusterGroupRelation(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    cluster_group = models.ForeignKey(ClusterGroup, on_delete=models.PROTECT)
    cluster = models.ForeignKey(Cluster, on_delete=models.PROTECT)

    class Meta(object):
        ordering = ['cluster_group']

    def __str__(self):
        return "{}|{}".format(self.cluster_group.name, self.cluster.name)


class ClusterGroupRelationAdmin(admin.ModelAdmin):
    model = ClusterGroupRelation
    list_display = ['cluster_group', 'cluster']


class Tenant(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    slug = models.CharField(max_length=10, validators=[RegexValidator('[A-Z]{2,10}')])
    description = models.CharField(max_length=256, blank=True, default="")
    stats_token = models.UUIDField(default=uid.uuid4)
    cluster_group = models.ForeignKey(ClusterGroup, on_delete=models.PROTECT)
    attendee_limit = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of attendees (soft limit, 0 = unlimited).")
    meeting_limit = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of meetings (0 = unlimited).")

    class Meta(object):
        ordering = ['slug']

    def __str__(self):
        return self.slug

    @property
    def hostname(self):
        return "{}.{}".format(str(self.slug).lower(), settings.B3LB_API_BASE_DOMAIN)


class TenantAdmin(admin.ModelAdmin):
    model = Tenant
    list_display = ['slug', 'description', 'hostname', 'cluster_group', 'attendee_limit', 'meeting_limit']


class Secret(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False, unique=True, default=uid.uuid4)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)
    description = models.CharField(max_length=256, blank=True, default="")
    sub_id = models.SmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(999)])
    secret = models.CharField(max_length=42, default=get_random_secret, validators=[RegexValidator(r'^[a-zA-Z0-9]{42}$')])
    secret2 = models.CharField(max_length=42, default="", blank=True, validators=[RegexValidator(r'^($|[a-zA-Z0-9]{42})$')])
    attendee_limit = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of attendees (soft limit, 0 = unlimited).")
    meeting_limit = models.IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of meetings (0 = unlimited).")

    class Meta(object):
        ordering = ['tenant__slug', 'sub_id']
        constraints = [models.UniqueConstraint(fields=['tenant', 'sub_id'], name='unique_tenant_id_combination')]

    def __str__(self):
        return "{}-{}".format(self.tenant.slug, str(self.sub_id).zfill(3))

    @property
    def endpoint(self):
        if self.sub_id == 0:
            return "{}.{}".format(str(self.tenant.slug).lower(), settings.B3LB_API_BASE_DOMAIN)
        else:
            return "{}-{}.{}".format(str(self.tenant.slug).lower(), str(self.sub_id).zfill(3), settings.B3LB_API_BASE_DOMAIN)


class SecretAdmin(admin.ModelAdmin):
    model = Secret
    list_display = ['__str__', 'description', 'endpoint', 'attendee_limit', 'meeting_limit']


class AssetSlide(models.Model):
    blob = models.BinaryField()
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=50)


class AssetSlideAdmin(admin.ModelAdmin):
    model = AssetSlide
    list_display = ['filename', 'mimetype']


class AssetLogo(models.Model):
    blob = models.BinaryField()
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=50)


class AssetLogoAdmin(admin.ModelAdmin):
    model = AssetLogo
    list_display = ['filename', 'mimetype']


class Asset(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, primary_key=True)
    slide = models.FileField(upload_to='rest.AssetSlide/blob/filename/mimetype', blank=True, null=True)
    slide_filename = models.CharField(max_length=250, blank=True, null=True)
    logo = models.ImageField(upload_to='rest.AssetLogo/blob/filename/mimetype', blank=True, null=True)

    @property
    def s_filename(self):
        if self.slide_filename:
            return xml_escape(self.slide_filename)
        elif self.slide:
            return "{}.{}".format(self.tenant.slug.lower(), self.slide.name.split(".")[-1])
        else:
            return ""

    @property
    def logo_url(self):
        return "{}/b3lb/t/{}/logo".format(settings.B3LB_API_BASE_DOMAIN, self.tenant.slug.lower())

    @property
    def slide_url(self):
        return "{}/b3lb/t/{}/slide".format(settings.B3LB_API_BASE_DOMAIN, self.tenant.slug.lower())

    class Meta(object):
        ordering = ['tenant__slug']

    def __str__(self):
        return self.tenant.slug


class AssetAdmin(admin.ModelAdmin):
    model = Asset
    list_display = ['__str__']


class SecretMeetingList(models.Model):
    secret = models.OneToOneField(Secret, on_delete=models.CASCADE, primary_key=True)
    xml = models.TextField(default="")


class SecretMeetingListAdmin(admin.ModelAdmin):
    model = SecretMeetingList
    list_display = ['secret']


class SecretMetricsList(models.Model):
    secret = models.OneToOneField(Secret, on_delete=models.CASCADE, unique=True, null=True)
    metrics = models.TextField(default="")

    def __str__(self):
        if self.secret:
            return self.secret.__str__()
        else:
            return "<<total>>"


class SecretMetricsListAdmin(admin.ModelAdmin):
    model = SecretMetricsList
    list_display = ['__str__']


# meeting - tenant - node relation class
class Meeting(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE)
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    room_name = models.CharField(max_length=500)
    age = models.DateTimeField(default=timezone.now)
    attendees = models.SmallIntegerField(default=0)
    listenerCount = models.SmallIntegerField(default=0)
    voiceParticipantCount = models.SmallIntegerField(default=0)
    moderatorCount = models.SmallIntegerField(default=0)
    videoCount = models.SmallIntegerField(default=0)
    bbb_origin = models.CharField(max_length=255, default="")
    bbb_origin_server_name = models.CharField(max_length=255, default="")

    class Meta(object):
        ordering = ['secret__tenant', 'age']

    def __str__(self):
        return "{} {}".format(self.secret.tenant.slug, self.room_name)


class MeetingAdmin(admin.ModelAdmin):
    model = Meeting
    list_display = ['__str__', 'bbb_origin_server_name', 'node', 'attendees', 'listenerCount', 'voiceParticipantCount', 'videoCount', 'age', 'id']


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

    def __str__(self):
        return "{}: {} ({})".format(self.tenant.slug, self.bbb_origin_server_name, self.bbb_origin)


class StatsAdmin(admin.ModelAdmin):
    model = Stats
    list_display = ['tenant', 'meetings', 'attendees', 'listenerCount', 'voiceParticipantCount', 'videoCount']


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


class MetricAdmin(admin.ModelAdmin):
    model = Metric
    list_display = ['name', 'secret', 'node', 'value']


class Parameter(models.Model):
    # Parameters
    MAX_PARTICIPANTS = "maxParticipants"
    LOGOUT_URL = "logoutURL"
    DURATION = "duration"
    WEBCAMS_ONLY_FOR_MODERATOR = "webcamsOnlyForModerator"
    BANNER_TEXT = "bannerText"
    BANNER_COLOR = "bannerColor"
    COPYRIGHT = "copyright"
    MUTE_ON_START = "muteOnStart"
    ALLOW_MODS_TO_UNMUTE_USERS = "allowModsToUnmuteUsers"
    LOCK_SETTINGS_DISABLE_CAM = "lockSettingsDisableCam"
    LOCK_SETTINGS_DISABLE_MIC = "lockSettingsDisableMic"
    LOCK_SETTINGS_DISABLE_PRIVATE_CHAT = "lockSettingsDisablePrivateChat"
    LOCK_SETTINGS_DISABLE_PUBLIC_CHAT = "lockSettingsDisablePublicChat"
    LOCK_SETTINGS_DISABLE_NOTE = "lockSettingsDisableNote"
    LOCK_SETTINGS_LOCKED_LAYOUT = "lockSettingsLockedLayout"
    LOCK_SETTINGS_HIDE_USER_LIST = "lockSettingsHideUserList"
    LOCK_SETTINGS_LOCK_ON_JOIN = "lockSettingsLockOnJoin"
    LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE = "lockSettingsLockOnJoinConfigurable"
    GUEST_POLICY = "guestPolicy"
    MEETING_KEEP_EVENT = "meetingKeepEvents"

    # Modes
    BLOCK = "BLOCK"
    SET = "SET"
    OVERRIDE = "OVERRIDE"
    
    PARAMETER_CHOICES = (
        (ALLOW_MODS_TO_UNMUTE_USERS, ALLOW_MODS_TO_UNMUTE_USERS),
        (BANNER_COLOR, BANNER_COLOR),
        (BANNER_TEXT, BANNER_TEXT),
        (COPYRIGHT, COPYRIGHT),
        (DURATION, DURATION),
        (GUEST_POLICY, GUEST_POLICY),
        (LOCK_SETTINGS_DISABLE_CAM, LOCK_SETTINGS_DISABLE_CAM),
        (LOCK_SETTINGS_DISABLE_MIC, LOCK_SETTINGS_DISABLE_MIC),
        (LOCK_SETTINGS_DISABLE_PRIVATE_CHAT, LOCK_SETTINGS_DISABLE_PRIVATE_CHAT),
        (LOCK_SETTINGS_DISABLE_PUBLIC_CHAT, LOCK_SETTINGS_DISABLE_PUBLIC_CHAT),
        (LOCK_SETTINGS_DISABLE_NOTE, LOCK_SETTINGS_DISABLE_NOTE),
        (LOCK_SETTINGS_HIDE_USER_LIST, LOCK_SETTINGS_HIDE_USER_LIST),
        (LOCK_SETTINGS_LOCK_ON_JOIN, LOCK_SETTINGS_LOCK_ON_JOIN),
        (LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE, LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE),
        (LOCK_SETTINGS_LOCKED_LAYOUT, LOCK_SETTINGS_LOCKED_LAYOUT),
        (LOGOUT_URL, LOGOUT_URL),
        (MAX_PARTICIPANTS, MAX_PARTICIPANTS),
        (MEETING_KEEP_EVENT, MEETING_KEEP_EVENT),
        (MUTE_ON_START, MUTE_ON_START),
        (WEBCAMS_ONLY_FOR_MODERATOR, WEBCAMS_ONLY_FOR_MODERATOR),
    )

    MODE_CHOICES = [
        (BLOCK, BLOCK),
        (SET, SET),
        (OVERRIDE, OVERRIDE)
    ]

    BOOLEAN_REGEX = r'^(true|false)$'
    NUMBER_REGEX = r'^\d+$'
    POLICY_REGEX = r'^(ALWAYS_ACCEPT|ALWAYS_DENY|ASK_MODERATOR)$'
    COLOR_REGEX = r'^#[a-fA-F0-9]{6}$'
    URL_REGEX = r"^https?://[\w.-]+(?:\.[\w.-]+)+[\w._~:/?#[\]@!\$&'()*+,;=.%-]+$"
    ANY_REGEX = r'.'

    PARAMETER_REGEXES = {
        MAX_PARTICIPANTS: NUMBER_REGEX,
        LOGOUT_URL: URL_REGEX,
        DURATION: NUMBER_REGEX,
        WEBCAMS_ONLY_FOR_MODERATOR: BOOLEAN_REGEX,
        BANNER_TEXT: ANY_REGEX,
        BANNER_COLOR: COLOR_REGEX,
        COPYRIGHT: ANY_REGEX,
        MUTE_ON_START: BOOLEAN_REGEX,
        ALLOW_MODS_TO_UNMUTE_USERS: BOOLEAN_REGEX,
        LOCK_SETTINGS_DISABLE_CAM: BOOLEAN_REGEX,
        LOCK_SETTINGS_DISABLE_MIC: BOOLEAN_REGEX,
        LOCK_SETTINGS_DISABLE_PRIVATE_CHAT: BOOLEAN_REGEX,
        LOCK_SETTINGS_DISABLE_PUBLIC_CHAT: BOOLEAN_REGEX,
        LOCK_SETTINGS_DISABLE_NOTE: BOOLEAN_REGEX,
        LOCK_SETTINGS_LOCKED_LAYOUT: BOOLEAN_REGEX,
        LOCK_SETTINGS_HIDE_USER_LIST: BOOLEAN_REGEX,
        LOCK_SETTINGS_LOCK_ON_JOIN: BOOLEAN_REGEX,
        LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE: BOOLEAN_REGEX,
        GUEST_POLICY: POLICY_REGEX,
        MEETING_KEEP_EVENT: BOOLEAN_REGEX
    }

    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    parameter = models.CharField(max_length=64, choices=PARAMETER_CHOICES)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    value = models.CharField(max_length=250, blank=True, null=True)

    def clean_fields(self, exclude=None):
        if self.mode in [self.SET, self.OVERRIDE]:
            if not re.match(self.PARAMETER_REGEXES[self.parameter], self.value):
                raise ValidationError('Value must have the format "{}"!'.format(self.PARAMETER_REGEXES[self.parameter]), params={'value': self.value})

    class Meta(object):
        constraints = [
            models.UniqueConstraint(fields=['parameter', 'tenant'], name="unique_parameter")
        ]


class ParameterAdmin(admin.ModelAdmin):
    model = Parameter
    list_display = ['tenant', 'parameter', 'mode', 'value']
