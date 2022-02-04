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


import re
import base64
import rest.endpoints.b3lb.constants as ct
from django.conf import settings
from django.contrib.admin import ModelAdmin, action
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db.models import (
    Model, UUIDField, BinaryField, FileField, ImageField, URLField,
    FloatField, SmallIntegerField, IntegerField, BigIntegerField, DateTimeField,
    CharField, TextField, BooleanField, ForeignKey, OneToOneField,
    UniqueConstraint, PROTECT, CASCADE, SET_NULL
)
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from math import pow
from rest.utils import xml_escape, get_file_from_storage
from uuid import uuid4


#
# CONSTANTS
#
SECRET_CHAR_POOL = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
NONCE_CHAR_POOL = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*(-_=+)'
MEETING_ID_LENGTH = 100  # ToDo AB1 -> CryptoHashFunction?


#
# DEFAULT FUNCTIONS
#
def get_b3lb_node_default_domain():
    return settings.B3LB_NODE_DEFAULT_DOMAIN


def get_random_secret():
    return get_random_string(42, SECRET_CHAR_POOL)


def get_nonce():
    return get_random_string(64, NONCE_CHAR_POOL)


#
# ADMIN ACTIONS
#
@action(description="Set nodes of cluster to active")
def set_cluster_nodes_to_active(modeladmin, request, queryset):
    for cluster in queryset:
        nodes = Node.objects.filter(cluster=cluster)
        nodes.update(maintenance=False)


@action(description="Set nodes of cluster to maintenance")
def set_cluster_nodes_to_maintenance(modeladmin, request, queryset):
    for cluster in queryset:
        nodes = Node.objects.filter(cluster=cluster)
        nodes.update(maintenance=True)


@action(description="Set Node to maintenance")
def maintenance_on(modeladmin, request, queryset):
    queryset.update(maintenance=True)


@action(description="Set Node to active")
def maintenance_off(modeladmin, request, queryset):
    queryset.update(maintenance=False)


@action(description="Enable records")
def records_on(modeladmin, request, queryset):
    queryset.update(records_enabled=True)


@action(description="Disable records")
def records_off(modeladmin, request, queryset):
    queryset.update(records_enabled=False)


#
# MODELS
#
class Cluster(Model):
    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    name = CharField(max_length=100, help_text="cluster name", unique=True)
    load_a_factor = FloatField(default=1.0, help_text="per attendee load factor")
    load_m_factor = FloatField(default=30.0, help_text="per meeting load factor")
    load_cpu_iterations = IntegerField(default=6, help_text="max sum iteration")
    load_cpu_max = IntegerField(default=5000, help_text="max cpu load")

    def __str__(self):
        return self.name

    class Meta(object):
        ordering = ['name']


class ClusterAdmin(ModelAdmin):
    model = Cluster
    list_display = ['name', 'number_of_nodes', 'available_nodes', 'maintenance_nodes', 'error_nodes', 'a_factor', 'm_factor', 'cpu_iterations', 'cpu_max']
    actions = [set_cluster_nodes_to_active, set_cluster_nodes_to_maintenance]

    def a_factor(self, obj):
        return obj.load_a_factor

    a_factor.short_description = "a-Factor"

    def m_factor(self, obj):
        return obj.load_m_factor

    m_factor.short_description = "m-Factor"

    def cpu_iterations(self, obj):
        return obj.load_cpu_iterations

    cpu_iterations.short_description = "# CPU Iter."

    def cpu_max(self, obj):
        return obj.load_cpu_max

    cpu_max.short_description = "CPU max. Load"

    def number_of_nodes(self, obj):
        count = Node.objects.filter(cluster=obj).count()
        url = (reverse("admin:rest_node_changelist") + "?" + urlencode({"cluster__uuid": f"{obj.uuid}"}))
        return format_html('<a href="{}">{}&nbsp;&nbsp;&nbsp;&nbsp;</a>', url, count)

    number_of_nodes.short_description = "# Nodes"

    def available_nodes(self, obj):
        count = Node.objects.filter(cluster=obj, has_errors=False, maintenance=False).count()
        url = (reverse("admin:rest_node_changelist") + "?" + urlencode({"cluster__uuid": f"{obj.uuid}", "maintenance__exact": 0, "has_errors__exact": 0}))
        return format_html('<a href="{}">{}&nbsp;&nbsp;&nbsp;&nbsp;</a>', url, count)

    available_nodes.short_description = "# Avail."

    def maintenance_nodes(self, obj):
        count = Node.objects.filter(cluster=obj, maintenance=True).count()
        url = (reverse("admin:rest_node_changelist") + "?" + urlencode({"cluster__uuid": f"{obj.uuid}", "maintenance__exact": 1}))
        return format_html('<a href="{}">{}&nbsp;&nbsp;&nbsp;&nbsp;</a>', url, count)

    maintenance_nodes.short_description = "# Maint."

    def error_nodes(self, obj):
        count = Node.objects.filter(cluster=obj, has_errors=True).count()
        url = (reverse("admin:rest_node_changelist") + "?" + urlencode({"cluster__uuid": f"{obj.uuid}", "has_errors__exact": 1}))
        return format_html('<a href="{}">{}&nbsp;&nbsp;&nbsp;&nbsp;</a>', url, count)

    error_nodes.short_description = "# Errors"


class Node(Model):
    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    slug = CharField(max_length=100, help_text="node hostname setting")
    domain = CharField(max_length=50, default=get_b3lb_node_default_domain, help_text="node domain name setting")
    secret = CharField(max_length=50, help_text="BBB API secret setting")
    cluster = ForeignKey(Cluster, on_delete=PROTECT, null=False)
    attendees = IntegerField(default=0, help_text="number of attendees metric")
    meetings = IntegerField(default=0, help_text="number of meetings metric")
    cpu_load = IntegerField(default=0, help_text="cpu load metric (base 10000)")
    has_errors = BooleanField(default=True, help_text="polling has detected a failure")
    maintenance = BooleanField(default=False, help_text="in maintenance setting")

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


class NodeAdmin(ModelAdmin):
    model = Node
    list_display = ['slug', 'cluster', 'load', 'attendees', 'meetings', 'show_cpu_load', 'has_errors', 'maintenance']
    list_filter = [('cluster', admin.RelatedOnlyFieldListFilter), 'has_errors', 'maintenance']
    search_fields = ['slug']
    actions = [maintenance_on, maintenance_off]

    def show_cpu_load(self, obj):
        return "{:.1f} %".format(obj.cpu_load/100)

    show_cpu_load.short_description = "CPU Load"


class NodeMeetingList(Model):
    node = OneToOneField(Node, on_delete=CASCADE, primary_key=True)
    xml = TextField(default="")


class NodeMeetingListAdmin(ModelAdmin):
    model = NodeMeetingList
    list_display = ['node']


class ClusterGroup(Model):
    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    name = CharField(max_length=100, help_text="Cluster name", unique=True)
    description = CharField(max_length=255, help_text="Cluster description", null=True)

    class Meta(object):
        ordering = ['name']

    def __str__(self):
        return self.name


class ClusterGroupAdmin(ModelAdmin):
    model = ClusterGroup
    list_display = ['name', 'description', 'number_of_nodes', 'available_nodes', 'maintenance_nodes', 'error_nodes']

    def number_of_nodes(self, obj):
        count = 0
        for cluster_group_relation in ClusterGroupRelation.objects.filter(cluster_group=obj):
            count += Node.objects.filter(cluster=cluster_group_relation.cluster).count()
        return count

    number_of_nodes.short_description = "# Nodes"

    def available_nodes(self, obj):
        count = 0
        for cluster_group_relation in ClusterGroupRelation.objects.filter(cluster_group=obj):
            count += Node.objects.filter(cluster=cluster_group_relation.cluster, has_errors=False, maintenance=False).count()
        url = (reverse("admin:rest_node_changelist") + "?" + urlencode({"maintenance__exact": 0, "has_errors__exact": 0}))
        return format_html('<a href="{}">{}&nbsp;&nbsp;&nbsp;&nbsp;</a>', url, count)

    available_nodes.short_description = "# Avail."

    def maintenance_nodes(self, obj):
        count = 0
        for cluster_group_relation in ClusterGroupRelation.objects.filter(cluster_group=obj):
            count += Node.objects.filter(cluster=cluster_group_relation.cluster, maintenance=True).count()
        url = (reverse("admin:rest_node_changelist") + "?" + urlencode({"maintenance__exact": 1}))
        return format_html('<a href="{}">{}&nbsp;&nbsp;&nbsp;&nbsp;</a>', url, count)

    maintenance_nodes.short_description = "# Maint."

    def error_nodes(self, obj):
        count = 0
        for cluster_group_relation in ClusterGroupRelation.objects.filter(cluster_group=obj):
            count += Node.objects.filter(cluster=cluster_group_relation.cluster, has_errors=True).count()
        url = (reverse("admin:rest_node_changelist") + "?" + urlencode({"has_errors__exact": 1}))
        return format_html('<a href="{}">{}&nbsp;&nbsp;&nbsp;&nbsp;</a>', url, count)

    error_nodes.short_description = "# Errors"


class ClusterGroupRelation(Model):
    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    cluster_group = ForeignKey(ClusterGroup, on_delete=PROTECT)
    cluster = ForeignKey(Cluster, on_delete=PROTECT)

    class Meta(object):
        ordering = ['cluster_group']

    def __str__(self):
        return "{}|{}".format(self.cluster_group.name, self.cluster.name)


class ClusterGroupRelationAdmin(ModelAdmin):
    model = ClusterGroupRelation
    list_display = ['cluster_group', 'cluster']


class Tenant(Model):
    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    slug = CharField(max_length=10, validators=[RegexValidator('[A-Z]{2,10}')])
    description = CharField(max_length=256, blank=True, default="")
    stats_token = UUIDField(default=uuid4)
    cluster_group = ForeignKey(ClusterGroup, on_delete=PROTECT)
    attendee_limit = IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of attendees (soft limit, 0 = unlimited).")
    meeting_limit = IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of meetings (0 = unlimited).")
    recording_enabled = BooleanField(default=False)
    records_hold_time = IntegerField(default=14, validators=[MinValueValidator(0)], help_text="Days interval before deleting records.")

    class Meta(object):
        ordering = ['slug']

    def __str__(self):
        return self.slug

    @property
    def hostname(self):
        return "{}.{}".format(str(self.slug).lower(), settings.B3LB_API_BASE_DOMAIN)


class TenantAdmin(ModelAdmin):
    model = Tenant
    list_display = ['slug', 'description', 'hostname', 'cluster_group', 'recording_enabled', 'attendee_limit', 'meeting_limit']
    actions = [records_on, records_off]


class Secret(Model):
    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    tenant = ForeignKey(Tenant, on_delete=PROTECT)
    description = CharField(max_length=256, blank=True, default="")
    sub_id = SmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(999)])
    secret = CharField(max_length=42, default=get_random_secret, validators=[RegexValidator(r'^[a-zA-Z0-9]{42}$')])
    secret2 = CharField(max_length=42, default="", blank=True, validators=[RegexValidator(r'^($|[a-zA-Z0-9]{42})$')])
    attendee_limit = IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of attendees (soft limit, 0 = unlimited).")
    meeting_limit = IntegerField(default=0, validators=[MinValueValidator(0)], help_text="Max. number of meetings (0 = unlimited).")
    recording_enabled = BooleanField(default=True)
    records_hold_time = IntegerField(default=14, validators=[MinValueValidator(0)], help_text="Days interval before deleting records.")

    class Meta(object):
        ordering = ['tenant__slug', 'sub_id']
        constraints = [UniqueConstraint(fields=['tenant', 'sub_id'], name='unique_tenant_id_combination')]

    def __str__(self):
        return "{}-{}".format(self.tenant.slug, str(self.sub_id).zfill(3))

    @property
    def endpoint(self):
        if self.sub_id == 0:
            return "{}.{}".format(str(self.tenant.slug).lower(), settings.B3LB_API_BASE_DOMAIN)
        else:
            return "{}-{}.{}".format(str(self.tenant.slug).lower(), str(self.sub_id).zfill(3), settings.B3LB_API_BASE_DOMAIN)

    @property
    def is_record_enabled(self):
        if self.recording_enabled and self.tenant.recording_enabled:
            return True
        else:
            return False

    @property
    def records_effective_hold_time(self):
        if 0 in [self.records_hold_time, self.tenant.records_hold_time]:
            return max(self.records_hold_time, self.tenant.records_hold_time)
        else:
            return min(self.records_hold_time, self.tenant.records_hold_time)


class SecretAdmin(ModelAdmin):
    model = Secret
    list_display = ['__str__', 'description', 'endpoint', 'recording_enabled', 'attendee_limit', 'meeting_limit']
    actions = [records_on, records_off]


class AssetSlide(Model):
    blob = BinaryField()
    filename = CharField(max_length=255)
    mimetype = CharField(max_length=50)


class AssetSlideAdmin(ModelAdmin):
    model = AssetSlide
    list_display = ['filename', 'mimetype']


class AssetLogo(Model):
    blob = BinaryField()
    filename = CharField(max_length=255)
    mimetype = CharField(max_length=50)


class AssetLogoAdmin(ModelAdmin):
    model = AssetLogo
    list_display = ['filename', 'mimetype']


class AssetCustomCSS(Model):
    blob = BinaryField()
    filename = CharField(max_length=255)
    mimetype = CharField(max_length=50)


class AssetCustomCSSAdmin(ModelAdmin):
    model = AssetCustomCSS
    list_display = ['filename', 'mimetype']


class Asset(Model):
    tenant = OneToOneField(Tenant, on_delete=CASCADE, primary_key=True)
    slide = FileField(upload_to='rest.AssetSlide/blob/filename/mimetype', blank=True, null=True)
    slide_filename = CharField(max_length=250, blank=True, null=True)
    logo = ImageField(upload_to='rest.AssetLogo/blob/filename/mimetype', blank=True, null=True)
    custom_css = FileField(upload_to='rest.AssetCustomCSS/blob/filename/mimetype', blank=True, null=True)

    @property
    def s_filename(self):
        if self.slide_filename:
            return xml_escape(self.slide_filename)
        elif self.slide:
            return "{}.{}".format(self.tenant.slug.lower(), self.slide.name.split(".")[-1])
        else:
            return ""

    @property
    def custom_css_url(self):
        return "https://{}/b3lb/t/{}/css".format(settings.B3LB_API_BASE_DOMAIN, self.tenant.slug.lower())

    @property
    def logo_url(self):
        return "https://{}/b3lb/t/{}/logo".format(settings.B3LB_API_BASE_DOMAIN, self.tenant.slug.lower())

    @property
    def slide_url(self):
        return "https://{}/b3lb/t/{}/slide".format(settings.B3LB_API_BASE_DOMAIN, self.tenant.slug.lower())

    @property
    def slide_base64(self):
        if self.slide:
            stored_file = get_file_from_storage(self.slide.name)
            if len(stored_file) <= ct.MAX_SLIDE_SIZE_IN_POST:
                based_64 = base64.b64encode(stored_file).decode()
                if len(based_64) <= ct.MAX_BASE64_SLIDE_SIZE_IN_POST:
                    return based_64
        return None

    class Meta(object):
        ordering = ['tenant__slug']

    def __str__(self):
        return self.tenant.slug


class AssetAdmin(ModelAdmin):
    model = Asset
    list_display = ['__str__']


class SecretMeetingList(Model):
    secret = OneToOneField(Secret, on_delete=CASCADE, primary_key=True)
    xml = TextField(default="")


class SecretMeetingListAdmin(ModelAdmin):
    model = SecretMeetingList
    list_display = ['secret']


class SecretMetricsList(Model):
    secret = OneToOneField(Secret, on_delete=CASCADE, unique=True, null=True)
    metrics = TextField(default="")

    def __str__(self):
        if self.secret:
            return self.secret.__str__()
        else:
            return "<<total>>"


class SecretMetricsListAdmin(ModelAdmin):
    model = SecretMetricsList
    list_display = ['__str__']


# meeting - tenant - node relation class
class Meeting(Model):
    id = CharField(max_length=MEETING_ID_LENGTH, primary_key=True)
    external_id = CharField(max_length=64)
    secret = ForeignKey(Secret, on_delete=CASCADE)
    node = ForeignKey(Node, on_delete=CASCADE)
    room_name = CharField(max_length=500)
    age = DateTimeField(default=now)
    attendees = SmallIntegerField(default=0)
    listenerCount = SmallIntegerField(default=0)
    voiceParticipantCount = SmallIntegerField(default=0)
    moderatorCount = SmallIntegerField(default=0)
    videoCount = SmallIntegerField(default=0)
    bbb_origin = CharField(max_length=255, default="")
    bbb_origin_server_name = CharField(max_length=255, default="")
    end_callback_url = URLField(default="")
    nonce = CharField(max_length=64, default=get_nonce, editable=False, unique=True)

    class Meta(object):
        ordering = ['secret__tenant', 'age']

    def __str__(self):
        return "{} {}".format(self.secret.tenant.slug, self.room_name)


class MeetingAdmin(ModelAdmin):
    model = Meeting
    list_display = ['__str__', 'bbb_origin_server_name', 'node', 'attendees', 'listenerCount', 'voiceParticipantCount', 'videoCount', 'age', 'id']
    list_filter = [('secret__tenant', admin.RelatedOnlyFieldListFilter), 'node']
    search_fields = ['room_name']


# Meeting - Secret - Recording relation class
class RecordSet(Model):
    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    secret = ForeignKey(Secret, on_delete=CASCADE)
    meeting_relation = ForeignKey(Meeting, on_delete=SET_NULL, null=True)
    meeting_id = CharField(max_length=MEETING_ID_LENGTH, default="")
    created_at = DateTimeField(default=now)
    recording_ready_origin_url = URLField(default="")
    nonce = CharField(max_length=64, default=get_nonce, editable=False, unique=True)


class RecordSetAdmin(ModelAdmin):
    model = RecordSet
    list_display = ['uuid', 'secret', 'meeting_id', 'created_at']


class Record(Model):
    UNKNOWN = "UNKNOWN"
    UPLOADED = "UPLOADED"
    RENDERED = "RENDERED"
    DELETING = "DELETING"
    DELETED = "DELETED"

    STATUS_CHOICES = [
        (UNKNOWN, "Record state is unknown"),
        (UPLOADED, "Record files has been uploaded"),
        (RENDERED, "Record files has been rendered to a video"),
        (DELETING, "Record video will be deleted"),
        (DELETED, "Record files have been deleted")
    ]

    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    id = CharField(max_length=MEETING_ID_LENGTH)
    status = CharField(max_length=10, choices=STATUS_CHOICES, default="UNKNOWN")
    relation = ForeignKey(RecordSet, on_delete=CASCADE)
    storage_id = CharField(max_length=100, default="")
    duration = IntegerField(default=0)
    started_at = DateTimeField(default=now)


class RecordAdmin(ModelAdmin):
    model = Record
    list_display = ['id', 'storage_id', 'duration', 'started_at']


class Stats(Model):
    uuid = UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    tenant = ForeignKey(Tenant, null=True, on_delete=CASCADE)
    attendees = IntegerField(default=0)
    meetings = IntegerField(default=0)
    listenerCount = IntegerField(default=0)
    voiceParticipantCount = IntegerField(default=0)
    moderatorCount = IntegerField(default=0)
    videoCount = IntegerField(default=0)
    bbb_origin = CharField(max_length=255, default="")
    bbb_origin_server_name = CharField(max_length=255, default="")

    class Meta(object):
        ordering = ['tenant']

    def __str__(self):
        return "{}: {} ({})".format(self.tenant.slug, self.bbb_origin_server_name, self.bbb_origin)


class StatsAdmin(ModelAdmin):
    model = Stats
    list_display = ['tenant', 'meetings', 'attendees', 'listenerCount', 'voiceParticipantCount', 'videoCount']
    list_filter = ['tenant']


class Metric(Model):
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

    name = CharField(max_length=64, choices=NAME_CHOICES)
    secret = ForeignKey(Secret, on_delete=CASCADE)
    node = ForeignKey(Node, on_delete=CASCADE, null=True)
    value = BigIntegerField(default=0)

    class Meta(object):
        constraints = [
            UniqueConstraint(fields=['name', 'secret', 'node'], name="unique_metric")
        ]


class MetricAdmin(ModelAdmin):
    model = Metric
    list_display = ['name', 'secret', 'node', 'value']


class Parameter(Model):
    # Create Parameters
    WELCOME = "welcome"
    MAX_PARTICIPANTS = "maxParticipants"
    LOGOUT_URL = "logoutURL"
    RECORD = "record"
    DURATION = "duration"
    MODERATOR_ONLY_MESSAGE = "moderatorOnlyMessage"
    AUTO_START_RECORDING = "autoStartRecording"
    ALLOW_START_STOP_RECORDING = "allowStartStopRecording"
    WEBCAMS_ONLY_FOR_MODERATOR = "webcamsOnlyForModerator"
    LOGO = "logo"
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
    LOCK_SETTINGS_LOCK_ON_JOIN = "lockSettingsLockOnJoin"
    LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE = "lockSettingsLockOnJoinConfigurable"
    GUEST_POLICY = "guestPolicy"
    MEETING_KEEP_EVENT = "meetingKeepEvents"
    END_WHEN_NO_MODERATOR = "endWhenNoModerator"
    END_WHEN_NO_MODERATOR_DELAY_IN_MINUTES = "endWhenNoModeratorDelayInMinutes"
    MEETING_LAYOUT = "meetingLayout"
    LEARNING_DASHBOARD_ENABLED = "learningDashboardEnabled"
    LEARNING_DASHBOARD_CLEANUP_DELAY_IN_MINUTES = "learningDashboardCleanupDelayInMinutes"

    # Join
    ROLE = "role"
    EXCLUDE_FROM_DASHBOARD = "excludeFromDashboard"

    # Join Parameters
    # see https://docs.bigbluebutton.org/admin/customize.html#passing-custom-parameters-to-the-client-on-join for documentation
    #
    # some join parameters needs settings.yml defined inputs, see
    # https://github.com/bigbluebutton/bigbluebutton/blob/develop/bigbluebutton-html5/private/config/settings.yml
    # for possible options

    # Join Parameters - Application
    USERDATA_BBB_ASK_FOR_FEEDBACK_ON_LOGOUT = "userdata-bbb_ask_for_feedback_on_logout"
    USERDATA_BBB_AUTO_JOIN_AUDIO = "userdata-bbb_auto_join_audio"
    USERDATA_BBB_CLIENT_TITLE = "userdata-bbb_client_title"
    USERDATA_BBB_FORCE_LISTEN_ONLY = "userdata-bbb_force_listen_only"
    USERDATA_BBB_LISTEN_ONLY_MODE = "userdata-bbb_listen_only_mode"
    USERDATA_BBB_SKIP_CHECK_AUDIO = "userdata-bbb_skip_check_audio"
    USERDATA_BBB_SKIP_CHECK_AUDIO_ON_FIRST_JOIN = "userdata-bbb_skip_check_audio_on_first_join"
    USERDATA_BBB_OVERRIDE_DEFAULT_LOCALE = "userdata-bbb_override_default_locale"
    
    # Join Parameters - Branding
    USERDATA_BBB_DISPLAY_BRANDING_AREA = "userdata-bbb_display_branding_area"

    # Join Parameters - Shortcut
    USERDATA_BBB_SHORTCUTS = "userdata-bbb_shortcuts"

    # Join Parameters - Kurento
    USERDATA_BBB_AUTO_SHARE_WEBCAM = "userdata-bbb_auto_share_webcam"
    USERDATA_BBB_PREFFERED_CAMERA_PROFILE = "userdata-bbb_preferred_camera_profile"
    USERDATA_BBB_ENABLE_SCREEN_SHARING = "userdata-bbb_enable_screen_sharing"
    USERDATA_BBB_ENABLE_VIDEO = "userdata-bbb_enable_video"
    USERDATA_BBB_RECORD_VIDEO = "userdata-bbb_record_video"  # currently useless, because record is forbidden in b3lb
    USERDATA_BBB_SKIP_VIDEO_PREVIEW = "userdata-bbb_skip_video_preview"
    USERDATA_BBB_SKIP_VIDEO_PREVIEW_ON_FIRST_JOIN = "userdata-bbb_skip_video_preview_on_first_join"
    USERDATA_BBB_MIRROR_OWN_WEBCAM = "userdata-bbb_mirror_own_webcam"

    # Join Parameter - Presentation
    USERDATA_BBB_FORCE_RESTORE_PRESENTATION_ON_NEW_EVENTS = "userdata-bbb_force_restore_presentation_on_new_events"

    # Join Parameter - Whiteboard
    USERDATA_BBB_MULTI_USER_PEN_ONLY = "userdata-bbb_multi_user_pen_only"
    USERDATA_BBB_PRESENTER_TOOLS = "userdata-bbb_presenter_tools"
    USERDATA_BBB_MULTI_USER_TOOLS = "userdata-bbb_multi_user_tools"

    # Join Parameter - Styling
    USERDATA_BBB_CUSTOM_STYLE = "userdata-bbb_custom_style"
    USERDATA_BBB_CUSTOM_STYLE_URL = "userdata-bbb_custom_style_url"

    # Join Parameter - Layout
    USERDATA_BBB_AUTO_SWAP_LAYOUT = "userdata-bbb_auto_swap_layout"
    USERDATA_BBB_HIDE_PRESENTATION = "userdata-bbb_hide_presentation"
    USERDATA_BBB_SHOW_PARTICIPIANTS_ON_LOGIN = "userdata-bbb_show_participants_on_login"
    USERDATA_BBB_SHOW_PUBLIC_CHAT_ON_LOGIN = "userdata-bbb_show_public_chat_on_login"

    # Join Parameter - External
    USERDATA_BBB_OUTSIDE_TOGGLE_SELF_VOICE = "userdata-bbb_outside_toggle_self_voice"
    USERDATA_BBB_OUTSIDE_TOGGLE_RECORDING = "userdata-bbb_outside_toggle_recording"  # currently useless, because of forbidden recording

    # Modes
    BLOCK = "BLOCK"
    SET = "SET"
    OVERRIDE = "OVERRIDE"
    
    PARAMETER_CHOICES = (
        # Create
        (ALLOW_MODS_TO_UNMUTE_USERS, ALLOW_MODS_TO_UNMUTE_USERS),
        (ALLOW_START_STOP_RECORDING, ALLOW_START_STOP_RECORDING),
        (AUTO_START_RECORDING, AUTO_START_RECORDING),
        (BANNER_COLOR, BANNER_COLOR),
        (BANNER_TEXT, BANNER_TEXT),
        (COPYRIGHT, COPYRIGHT),
        (DURATION, DURATION),
        (END_WHEN_NO_MODERATOR, END_WHEN_NO_MODERATOR),
        (END_WHEN_NO_MODERATOR_DELAY_IN_MINUTES, END_WHEN_NO_MODERATOR_DELAY_IN_MINUTES),
        (GUEST_POLICY, GUEST_POLICY),
        (LOCK_SETTINGS_DISABLE_CAM, LOCK_SETTINGS_DISABLE_CAM),
        (LOCK_SETTINGS_DISABLE_MIC, LOCK_SETTINGS_DISABLE_MIC),
        (LOCK_SETTINGS_DISABLE_PRIVATE_CHAT, LOCK_SETTINGS_DISABLE_PRIVATE_CHAT),
        (LOCK_SETTINGS_DISABLE_PUBLIC_CHAT, LOCK_SETTINGS_DISABLE_PUBLIC_CHAT),
        (LOCK_SETTINGS_DISABLE_NOTE, LOCK_SETTINGS_DISABLE_NOTE),
        (LOCK_SETTINGS_LOCK_ON_JOIN, LOCK_SETTINGS_LOCK_ON_JOIN),
        (LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE, LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE),
        (LOCK_SETTINGS_LOCKED_LAYOUT, LOCK_SETTINGS_LOCKED_LAYOUT),
        (LOGO, LOGO),
        (LOGOUT_URL, LOGOUT_URL),
        (MAX_PARTICIPANTS, MAX_PARTICIPANTS),
        (MEETING_KEEP_EVENT, MEETING_KEEP_EVENT),
        (MODERATOR_ONLY_MESSAGE, MODERATOR_ONLY_MESSAGE),
        (MUTE_ON_START, MUTE_ON_START),
        (WEBCAMS_ONLY_FOR_MODERATOR, WEBCAMS_ONLY_FOR_MODERATOR),
        (WELCOME, WELCOME),
        (MEETING_LAYOUT, MEETING_LAYOUT),
        (LEARNING_DASHBOARD_ENABLED, LEARNING_DASHBOARD_ENABLED),
        (LEARNING_DASHBOARD_CLEANUP_DELAY_IN_MINUTES, LEARNING_DASHBOARD_CLEANUP_DELAY_IN_MINUTES),

        # Join
        (ROLE, ROLE),
        (EXCLUDE_FROM_DASHBOARD, EXCLUDE_FROM_DASHBOARD),

        # Join - Application
        (USERDATA_BBB_ASK_FOR_FEEDBACK_ON_LOGOUT, USERDATA_BBB_ASK_FOR_FEEDBACK_ON_LOGOUT),
        (USERDATA_BBB_AUTO_JOIN_AUDIO, USERDATA_BBB_AUTO_JOIN_AUDIO),
        (USERDATA_BBB_CLIENT_TITLE, USERDATA_BBB_CLIENT_TITLE),
        (USERDATA_BBB_FORCE_LISTEN_ONLY, USERDATA_BBB_FORCE_LISTEN_ONLY),
        (USERDATA_BBB_LISTEN_ONLY_MODE, USERDATA_BBB_LISTEN_ONLY_MODE),
        (USERDATA_BBB_SKIP_CHECK_AUDIO, USERDATA_BBB_SKIP_CHECK_AUDIO),
        (USERDATA_BBB_SKIP_CHECK_AUDIO_ON_FIRST_JOIN, USERDATA_BBB_SKIP_CHECK_AUDIO_ON_FIRST_JOIN),
        (USERDATA_BBB_OVERRIDE_DEFAULT_LOCALE, USERDATA_BBB_OVERRIDE_DEFAULT_LOCALE),

        # Join - Branding
        (USERDATA_BBB_DISPLAY_BRANDING_AREA, USERDATA_BBB_DISPLAY_BRANDING_AREA),

        # Join - Shortcut
        (USERDATA_BBB_SHORTCUTS, USERDATA_BBB_SHORTCUTS),

        # Join - Kurento
        (USERDATA_BBB_AUTO_SHARE_WEBCAM, USERDATA_BBB_AUTO_SHARE_WEBCAM),
        (USERDATA_BBB_PREFFERED_CAMERA_PROFILE, USERDATA_BBB_PREFFERED_CAMERA_PROFILE),
        (USERDATA_BBB_ENABLE_SCREEN_SHARING, USERDATA_BBB_ENABLE_SCREEN_SHARING),
        (USERDATA_BBB_ENABLE_VIDEO, USERDATA_BBB_ENABLE_VIDEO),
        (USERDATA_BBB_RECORD_VIDEO, USERDATA_BBB_RECORD_VIDEO),
        (USERDATA_BBB_SKIP_VIDEO_PREVIEW, USERDATA_BBB_SKIP_VIDEO_PREVIEW),
        (USERDATA_BBB_SKIP_VIDEO_PREVIEW_ON_FIRST_JOIN, USERDATA_BBB_SKIP_VIDEO_PREVIEW_ON_FIRST_JOIN),
        (USERDATA_BBB_MIRROR_OWN_WEBCAM, USERDATA_BBB_MIRROR_OWN_WEBCAM),

        # Join - Presentation
        (USERDATA_BBB_FORCE_RESTORE_PRESENTATION_ON_NEW_EVENTS, USERDATA_BBB_FORCE_RESTORE_PRESENTATION_ON_NEW_EVENTS),

        # Join - Whiteboard
        (USERDATA_BBB_MULTI_USER_PEN_ONLY, USERDATA_BBB_MULTI_USER_PEN_ONLY),
        (USERDATA_BBB_PRESENTER_TOOLS, USERDATA_BBB_PRESENTER_TOOLS),
        (USERDATA_BBB_MULTI_USER_TOOLS, USERDATA_BBB_MULTI_USER_TOOLS),

        # Join - Styling
        (USERDATA_BBB_CUSTOM_STYLE, USERDATA_BBB_CUSTOM_STYLE),
        (USERDATA_BBB_CUSTOM_STYLE_URL, USERDATA_BBB_CUSTOM_STYLE_URL),

        # Join - Layout
        (USERDATA_BBB_AUTO_SWAP_LAYOUT, USERDATA_BBB_AUTO_SWAP_LAYOUT),
        (USERDATA_BBB_HIDE_PRESENTATION, USERDATA_BBB_HIDE_PRESENTATION),
        (USERDATA_BBB_SHOW_PARTICIPIANTS_ON_LOGIN, USERDATA_BBB_SHOW_PARTICIPIANTS_ON_LOGIN),
        (USERDATA_BBB_SHOW_PUBLIC_CHAT_ON_LOGIN, USERDATA_BBB_SHOW_PUBLIC_CHAT_ON_LOGIN),

        # Join - External
        (USERDATA_BBB_OUTSIDE_TOGGLE_SELF_VOICE, USERDATA_BBB_OUTSIDE_TOGGLE_SELF_VOICE),
        (USERDATA_BBB_OUTSIDE_TOGGLE_RECORDING, USERDATA_BBB_OUTSIDE_TOGGLE_RECORDING),
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
    LOCALE_REGEX = r'^[a-z]{2}$'
    CAMERA_REGEX = r'^(low-u30|low-u25|low-u20|low-u15|low-u12|low-u8|low|medium|high|hd)$'
    URL_REGEX = r"^https?://[\w.-]+(?:\.[\w.-]+)+[\w._~:/?#[\]@!\$&'()*+,;=.%-]+$"
    ROLE_REGEX = r'^(VIEWER|MODERATOR)$'
    MEETING_LAYOUT_REGEX = r'(CUSTOM_LAYOUT|SMART_LAYOUT|PRESENTATION_FOCUS|VIDEO_FOCUS)$'
    ANY_REGEX = r'.'

    PARAMETER_REGEXES = {
        # Create
        WELCOME: ANY_REGEX,
        MAX_PARTICIPANTS: NUMBER_REGEX,
        LOGOUT_URL: URL_REGEX,
        RECORD: BOOLEAN_REGEX,
        DURATION: NUMBER_REGEX,
        MODERATOR_ONLY_MESSAGE: ANY_REGEX,
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
        LOCK_SETTINGS_LOCK_ON_JOIN: BOOLEAN_REGEX,
        LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE: BOOLEAN_REGEX,
        AUTO_START_RECORDING: BOOLEAN_REGEX,
        ALLOW_START_STOP_RECORDING: BOOLEAN_REGEX,
        LOGO: URL_REGEX,
        GUEST_POLICY: POLICY_REGEX,
        MEETING_KEEP_EVENT: BOOLEAN_REGEX,
        END_WHEN_NO_MODERATOR: BOOLEAN_REGEX,
        END_WHEN_NO_MODERATOR_DELAY_IN_MINUTES: NUMBER_REGEX,
        MEETING_LAYOUT: MEETING_LAYOUT_REGEX,
        LEARNING_DASHBOARD_ENABLED: BOOLEAN_REGEX,
        LEARNING_DASHBOARD_CLEANUP_DELAY_IN_MINUTES: NUMBER_REGEX,

        # Join
        ROLE: ROLE_REGEX,
        EXCLUDE_FROM_DASHBOARD: BOOLEAN_REGEX,

        # Join - Application
        USERDATA_BBB_ASK_FOR_FEEDBACK_ON_LOGOUT: BOOLEAN_REGEX,
        USERDATA_BBB_AUTO_JOIN_AUDIO: BOOLEAN_REGEX,
        USERDATA_BBB_CLIENT_TITLE: ANY_REGEX,
        USERDATA_BBB_FORCE_LISTEN_ONLY: BOOLEAN_REGEX,
        USERDATA_BBB_LISTEN_ONLY_MODE: BOOLEAN_REGEX,
        USERDATA_BBB_SKIP_CHECK_AUDIO: BOOLEAN_REGEX,
        USERDATA_BBB_SKIP_CHECK_AUDIO_ON_FIRST_JOIN: BOOLEAN_REGEX,
        USERDATA_BBB_OVERRIDE_DEFAULT_LOCALE: LOCALE_REGEX,

        # Join - Branding
        USERDATA_BBB_DISPLAY_BRANDING_AREA: BOOLEAN_REGEX,

        # Join - Shortcut
        USERDATA_BBB_SHORTCUTS: ANY_REGEX,

        # Join - Kurento
        USERDATA_BBB_AUTO_SHARE_WEBCAM: BOOLEAN_REGEX,
        USERDATA_BBB_PREFFERED_CAMERA_PROFILE: CAMERA_REGEX,
        USERDATA_BBB_ENABLE_SCREEN_SHARING: BOOLEAN_REGEX,
        USERDATA_BBB_ENABLE_VIDEO: BOOLEAN_REGEX,
        USERDATA_BBB_RECORD_VIDEO: BOOLEAN_REGEX,
        USERDATA_BBB_SKIP_VIDEO_PREVIEW: BOOLEAN_REGEX,
        USERDATA_BBB_SKIP_VIDEO_PREVIEW_ON_FIRST_JOIN: BOOLEAN_REGEX,
        USERDATA_BBB_MIRROR_OWN_WEBCAM: BOOLEAN_REGEX,

        # Join - Presentation
        USERDATA_BBB_FORCE_RESTORE_PRESENTATION_ON_NEW_EVENTS: BOOLEAN_REGEX,

        # Join - Whiteboard
        USERDATA_BBB_MULTI_USER_PEN_ONLY: BOOLEAN_REGEX,
        USERDATA_BBB_PRESENTER_TOOLS: ANY_REGEX,
        USERDATA_BBB_MULTI_USER_TOOLS: ANY_REGEX,

        # Join - Styling
        USERDATA_BBB_CUSTOM_STYLE: ANY_REGEX,
        USERDATA_BBB_CUSTOM_STYLE_URL: URL_REGEX,

        # Join - Layout
        USERDATA_BBB_AUTO_SWAP_LAYOUT: BOOLEAN_REGEX,
        USERDATA_BBB_HIDE_PRESENTATION: BOOLEAN_REGEX,
        USERDATA_BBB_SHOW_PARTICIPIANTS_ON_LOGIN: BOOLEAN_REGEX,
        USERDATA_BBB_SHOW_PUBLIC_CHAT_ON_LOGIN: BOOLEAN_REGEX,

        # Join - External
        USERDATA_BBB_OUTSIDE_TOGGLE_SELF_VOICE: BOOLEAN_REGEX,
        USERDATA_BBB_OUTSIDE_TOGGLE_RECORDING: BOOLEAN_REGEX

    }

    PARAMETERS_CREATE = [ALLOW_MODS_TO_UNMUTE_USERS, ALLOW_START_STOP_RECORDING, AUTO_START_RECORDING,
                         BANNER_COLOR, BANNER_TEXT, COPYRIGHT, DURATION, END_WHEN_NO_MODERATOR,
                         END_WHEN_NO_MODERATOR_DELAY_IN_MINUTES, GUEST_POLICY, LOCK_SETTINGS_DISABLE_CAM, LOCK_SETTINGS_DISABLE_MIC,
                         LOCK_SETTINGS_DISABLE_PRIVATE_CHAT, LOCK_SETTINGS_DISABLE_PUBLIC_CHAT, LOCK_SETTINGS_DISABLE_NOTE,
                         LOCK_SETTINGS_LOCK_ON_JOIN, LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE, LOCK_SETTINGS_LOCKED_LAYOUT, LOGO, LOGOUT_URL,
                         MAX_PARTICIPANTS, MEETING_KEEP_EVENT, MODERATOR_ONLY_MESSAGE, MUTE_ON_START, WEBCAMS_ONLY_FOR_MODERATOR, RECORD,
                         WELCOME, MEETING_LAYOUT, LEARNING_DASHBOARD_ENABLED, LEARNING_DASHBOARD_CLEANUP_DELAY_IN_MINUTES]

    PARAMETERS_JOIN = [USERDATA_BBB_ASK_FOR_FEEDBACK_ON_LOGOUT, USERDATA_BBB_AUTO_JOIN_AUDIO, USERDATA_BBB_CLIENT_TITLE, USERDATA_BBB_FORCE_LISTEN_ONLY,
                       USERDATA_BBB_LISTEN_ONLY_MODE, USERDATA_BBB_SKIP_CHECK_AUDIO, USERDATA_BBB_SKIP_CHECK_AUDIO_ON_FIRST_JOIN,
                       USERDATA_BBB_OVERRIDE_DEFAULT_LOCALE, USERDATA_BBB_DISPLAY_BRANDING_AREA, USERDATA_BBB_SHORTCUTS, USERDATA_BBB_AUTO_SHARE_WEBCAM,
                       USERDATA_BBB_PREFFERED_CAMERA_PROFILE, USERDATA_BBB_ENABLE_SCREEN_SHARING, USERDATA_BBB_ENABLE_VIDEO, USERDATA_BBB_RECORD_VIDEO,
                       USERDATA_BBB_SKIP_VIDEO_PREVIEW, USERDATA_BBB_SKIP_VIDEO_PREVIEW_ON_FIRST_JOIN, USERDATA_BBB_MIRROR_OWN_WEBCAM,
                       USERDATA_BBB_FORCE_RESTORE_PRESENTATION_ON_NEW_EVENTS, USERDATA_BBB_MULTI_USER_PEN_ONLY, USERDATA_BBB_PRESENTER_TOOLS,
                       USERDATA_BBB_MULTI_USER_TOOLS, USERDATA_BBB_CUSTOM_STYLE, USERDATA_BBB_CUSTOM_STYLE_URL, USERDATA_BBB_AUTO_SWAP_LAYOUT,
                       USERDATA_BBB_HIDE_PRESENTATION, USERDATA_BBB_SHOW_PARTICIPIANTS_ON_LOGIN, USERDATA_BBB_SHOW_PUBLIC_CHAT_ON_LOGIN,
                       USERDATA_BBB_OUTSIDE_TOGGLE_SELF_VOICE, USERDATA_BBB_OUTSIDE_TOGGLE_RECORDING, ROLE, EXCLUDE_FROM_DASHBOARD]

    mode = CharField(max_length=10, choices=MODE_CHOICES)
    parameter = CharField(max_length=64, choices=PARAMETER_CHOICES)
    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    value = CharField(max_length=250, blank=True, null=True)

    def clean_fields(self, exclude=None):
        if self.mode in [self.SET, self.OVERRIDE]:
            if not re.match(self.PARAMETER_REGEXES[self.parameter], self.value):
                raise ValidationError('Value must have the format "{}"!'.format(self.PARAMETER_REGEXES[self.parameter]), params={'value': self.value})

    class Meta(object):
        constraints = [
            UniqueConstraint(fields=['parameter', 'tenant'], name="unique_parameter")
        ]


class ParameterAdmin(ModelAdmin):
    model = Parameter
    list_display = ['tenant', 'parameter', 'mode', 'value']
    list_filter = [('tenant', admin.RelatedOnlyFieldListFilter), 'mode']
