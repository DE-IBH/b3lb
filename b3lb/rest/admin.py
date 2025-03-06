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


from django.contrib.admin import ModelAdmin, RelatedOnlyFieldListFilter, action, site
from django.db.models import Q
from django.utils.html import format_html
from django.utils.http import urlencode
from django.urls import reverse
from rest.models import *


URL_FORMAT_STR = '<a href="{}" target="_blank" rel="noopener noreferrer">{}&nbsp;&nbsp;&nbsp;&nbsp;</a>'


class AssetAdmin(ModelAdmin):
    model = Asset
    list_display = ['__str__', "has_slide", "has_logo", "has_css"]

    def has_slide(self, obj) -> bool:
        return True if obj.slide else False

    has_slide.short_description = "Slide"
    has_slide.boolean = True

    def has_logo(self, obj) -> bool:
        return True if obj.logo else False

    has_logo.short_description = "Logo"
    has_logo.boolean = True

    def has_css(self, obj) -> bool:
        return True if obj.custom_css else False

    has_css.short_description = "Custom CSS"
    has_css.boolean = True


class ClusterAdmin(ModelAdmin):
    model = Cluster
    list_display = ['name', 'sha_function', 'number_of_nodes', 'available_nodes', 'maintenance_nodes', 'error_nodes', 'a_factor', 'm_factor', 'cpu_iterations', 'cpu_max']

    @staticmethod
    def _get_nodes(obj, condition: Q(), params: dict):
        url_params = "?" + urlencode({"cluster__uuid": f"{obj.uuid}"} | params)
        url = (reverse("admin:rest_node_changelist") + url_params.rstrip("?"))
        return format_html(URL_FORMAT_STR, url, Node.objects.filter(Q(cluster=obj) & condition).count())

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
        return self._get_nodes(obj, Q(), {})

    number_of_nodes.short_description = "# Nodes"

    def available_nodes(self, obj):
        return self._get_nodes(obj, Q(has_errors=False, maintenance=False), {"maintenance__exact": 0, "has_errors__exact": 0})

    available_nodes.short_description = "# Avail."

    def maintenance_nodes(self, obj):
        return self._get_nodes(obj, Q(maintenance=True), {"maintenance__exact": 1})

    maintenance_nodes.short_description = "# Maint."

    def error_nodes(self, obj):
        return self._get_nodes(obj, Q(has_errors=True), {"has_errors__exact": 1})

    error_nodes.short_description = "# Errors"

    @action(description="Set nodes of cluster to active")
    def set_cluster_nodes_to_active(self, request, queryset):
        for cluster in queryset:
            nodes = Node.objects.filter(cluster=cluster)
            nodes.update(maintenance=False)

    @action(description="Set nodes of cluster to maintenance")
    def set_cluster_nodes_to_maintenance(self, request, queryset):
        for cluster in queryset:
            nodes = Node.objects.filter(cluster=cluster)
            nodes.update(maintenance=True)


class ClusterGroupAdmin(ModelAdmin):
    model = ClusterGroup
    list_display = ['name', 'description', 'number_of_nodes', 'available_nodes', 'maintenance_nodes', 'error_nodes']

    @staticmethod
    def _count_nodes(obj, condition: Q, param_dict: dict) -> str:
        count = 0
        url_params = "?"
        for cluster_group_relation in ClusterGroupRelation.objects.filter(cluster_group=obj):
            query_condition = condition & Q(cluster=cluster_group_relation.cluster)
            count += Node.objects.filter(query_condition).count()
            url_params += urlencode({"cluster__uuid": f"{cluster_group_relation.cluster.uuid}"}) + "&"
        url_params += urlencode(param_dict) if param_dict else ""
        url = (reverse("admin:rest_node_changelist") + url_params.rstrip("?").rstrip("&"))
        return format_html(URL_FORMAT_STR, url, count)

    def number_of_nodes(self, obj):
        return self._count_nodes(obj, Q(), {})

    number_of_nodes.short_description = "# Nodes"

    def available_nodes(self, obj):
        return self._count_nodes(obj, Q(has_errors=False, maintenance=False), {"maintenance__exact": 0, "has_errors__exact": 0})

    available_nodes.short_description = "# Avail."

    def maintenance_nodes(self, obj):
        return self._count_nodes(obj, Q(maintenance=True), {"maintenance__exact": 1})

    maintenance_nodes.short_description = "# Maint."

    def error_nodes(self, obj):
        return self._count_nodes(obj, Q(has_errors=True), {"has_errors__exact": 1})

    error_nodes.short_description = "# Errors"


class ClusterGroupRelationAdmin(ModelAdmin):
    model = ClusterGroupRelation
    list_display = ['cluster_group', 'cluster']


class MeetingAdmin(ModelAdmin):
    model = Meeting
    list_display = ['__str__', 'bbb_origin_server_name', 'node', 'attendees', 'listenerCount', 'voiceParticipantCount', 'videoCount', 'age', 'id']
    list_filter = [('secret__tenant', RelatedOnlyFieldListFilter), 'node']
    search_fields = ['room_name']


class MetricAdmin(ModelAdmin):
    model = Metric
    list_display = ['name', 'secret', 'node', 'value']


class NodeAdmin(ModelAdmin):
    model = Node
    list_display = ['slug', 'cluster', 'load', 'attendees', 'meetings', 'show_cpu_load', 'has_errors', 'maintenance', 'api_mate']
    list_filter = [('cluster', RelatedOnlyFieldListFilter), 'has_errors', 'maintenance']
    search_fields = ['slug']

    def api_mate(self, obj):
        params = {
            "sharedSecret": obj.secret,
            "name": f"API Mate test room on {obj.slug.lower()}.{obj.domain}",
            "attendeePW": get_random_string(settings.B3LB_API_MATE_PW_LENGTH, cst.API_MATE_CHAR_POOL),
            "moderatorPW": get_random_string(settings.B3LB_API_MATE_PW_LENGTH, cst.API_MATE_CHAR_POOL)
        }

        url_enc_params = urlencode(params)
        url_base = f"{settings.B3LB_API_MATE_BASE_URL}#server=https://"
        url = f"{url_base}{obj.slug.lower()}.{obj.domain}/bigbluebutton&{url_enc_params}"
        # Todo
        #   check if single-domain is used, when implemented
        # url = f"{url_base} {settings.B3LB_API_BASE_DOMAIN}/b3lb/t/{low_slug_id}/bbb&{url_enc_params}"

        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">Link</a>', url)

    api_mate.short_description = "API Mate"

    @action(description="Set Node to maintenance")
    def maintenance_on(self, request, queryset):
        queryset.update(maintenance=True)

    @action(description="Set Node to active")
    def maintenance_off(self, request, queryset):
        queryset.update(maintenance=False)

    def show_cpu_load(self, obj):
        return "{:.1f} %".format(obj.cpu_load/100)

    show_cpu_load.short_description = "CPU Load"


class NodeMeetingListAdmin(ModelAdmin):
    model = NodeMeetingList
    list_display = ['node']


class ParameterAdmin(ModelAdmin):
    model = Parameter
    list_display = ['tenant', 'parameter', 'mode', 'value']
    list_filter = [('tenant', RelatedOnlyFieldListFilter), 'mode']


class RecordAdmin(ModelAdmin):
    model = Record
    list_display = ['__str__', 'record_set', 'profile', 'file']
    list_filter = [('record_set__secret__tenant', RelatedOnlyFieldListFilter)]

    class Meta(object):
        ordering = ['record_set', 'record_profile']

    def delete_queryset(self, request, queryset):
        for record in queryset:
            record.delete()


class RecordProfileAdmin(ModelAdmin):
    model = RecordProfile
    list_display = ['name', 'description', 'width', 'height', 'webcam_size', 'annotations', 'is_default']


class RecordSetAdmin(ModelAdmin):
    model = RecordSet
    list_display = ['__str__', 'secret', 'status', 'meta_meeting_id', 'created_at']
    list_filter = [('secret__tenant', RelatedOnlyFieldListFilter), 'status', 'created_at']

    class Meta(object):
        ordering = ['secret', 'created_at']

    def delete_queryset(self, request, queryset):
        for record_set in queryset:
            for record in Record.objects.filter(record_set=record_set):
                record.delete()
            record_set.delete()

    @action(description="Set status for deletion")
    def set_to_deletion(self, request, queryset):
        queryset.update(status=RecordSet.DELETING)

    @action(description="Set status for re-rendering")
    def set_to_rerender(self, request, queryset):
        queryset.update(status=RecordSet.UPLOADED)


class SecretAdmin(ModelAdmin):
    model = Secret
    list_display = ['__str__', 'description', 'endpoint', 'attendee_limit', 'meeting_limit', 'recording_enabled', 'api_mate']
    list_filter = [('tenant', RelatedOnlyFieldListFilter)]

    def api_mate(self, obj):
        low_slug = str(obj.tenant.slug).lower()
        low_slug_id = f"{low_slug}-{str(obj.sub_id).zfill(3)}"
        params = {
            "sharedSecret": obj.secret,
            "name": f"API Mate test room for {low_slug_id}",
            "attendeePW": get_random_string(settings.B3LB_API_MATE_PW_LENGTH, cst.API_MATE_CHAR_POOL),
            "moderatorPW": get_random_string(settings.B3LB_API_MATE_PW_LENGTH, cst.API_MATE_CHAR_POOL)
        }
        slide_string = ""
        try:
            slide = Asset.objects.get(tenant__secret=obj).slide
            if slide:
                slide_string = f"pre-upload=https://{settings.B3LB_API_BASE_DOMAIN}/b3lb/t/{low_slug}/slide"
        except Asset.DoesNotExist:
            pass

        if obj.is_record_enabled:
            params["record"] = True

        url_enc_params = urlencode(params)
        url_base = f" {settings.B3LB_API_MATE_BASE_URL}#server=https://"
        url = f"{url_base}{obj.endpoint}/bigbluebutton&{url_enc_params}"
        # Todo
        #   check if single-domain is used, when implemented
        # url = f"{url_base}{settings.B3LB_API_BASE_DOMAIN}/b3lb/t/{low_slug_id}/bbb&{url_enc_params}"
        if slide_string:
            url += f"&{slide_string}"

        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">Link</a>', url)

    api_mate.short_description = "API Mate"

    @action(description="Enable recording")
    def records_on(self, request, queryset):
        queryset.update(recording_enabled=True)

    @action(description="Disable recording")
    def records_off(self, request, queryset):
        queryset.update(recording_enabled=False)


class SecretMeetingListAdmin(ModelAdmin):
    model = SecretMeetingList
    list_display = ['secret']


class SecretMetricsListAdmin(ModelAdmin):
    model = SecretMetricsList
    list_display = ['__str__']


class SecretRecordProfileRelationAdmin(ModelAdmin):
    model = SecretRecordProfileRelation
    list_display = ['__str__', 'secret', 'record_profile']
    list_filter = [('secret__tenant', RelatedOnlyFieldListFilter), 'record_profile']


class StatsAdmin(ModelAdmin):
    model = Stats
    list_display = ['tenant', 'meetings', 'attendees', 'listenerCount', 'voiceParticipantCount', 'videoCount']
    list_filter = ['tenant']


class TenantAdmin(ModelAdmin):
    model = Tenant
    list_display = ['slug', 'description', 'hostname', 'cluster_group', 'recording_enabled', 'attendee_limit', 'meeting_limit']
    list_filter = [('cluster_group', RelatedOnlyFieldListFilter)]
    search_fields = ['cluster_group', 'slug', 'description']

    @action(description="Enable recording")
    def records_on(self, request, queryset):
        queryset.update(recording_enabled=True)

    @action(description="Disable recording")
    def records_off(self, request, queryset):
        queryset.update(recording_enabled=False)



# register all models for admin view
site.register(Asset, AssetAdmin)
site.register(Cluster, ClusterAdmin)
site.register(ClusterGroup, ClusterGroupAdmin)
site.register(ClusterGroupRelation, ClusterGroupRelationAdmin)
site.register(Meeting, MeetingAdmin)
site.register(Metric, MetricAdmin)
site.register(Node, NodeAdmin)
site.register(NodeMeetingList, NodeMeetingListAdmin)
site.register(Parameter, ParameterAdmin)
site.register(Record, RecordAdmin)
site.register(RecordProfile, RecordProfileAdmin)
site.register(RecordSet, RecordSetAdmin)
site.register(Secret, SecretAdmin)
site.register(SecretMeetingList, SecretMeetingListAdmin)
site.register(SecretMetricsList, SecretMetricsListAdmin)
site.register(SecretRecordProfileRelation, SecretRecordProfileRelationAdmin)
site.register(Stats, StatsAdmin)
site.register(Tenant, TenantAdmin)
