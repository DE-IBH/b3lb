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


from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.template.loader import render_to_string
from rest.classes.statistics import MeetingStats
from rest.models import Meeting, Metric, Node, Secret, SecretMetricsList, Stats, Tenant


def update_secret_metrics(secret_uuid: str):
    if secret_uuid:
        secret_zero = Secret.objects.get(uuid=secret_uuid)
        if secret_zero.sub_id == 0:
            secrets = Secret.objects.filter(tenant=secret_zero.tenant)
        else:
            secrets = [secret_zero]
        del secret_zero
        template = "metrics_secret"
        secret_text = secrets[0].__str__()
    else:
        secrets = Secret.objects.all()
        template = "metrics_all"
        secret_text = "all metrics."

    metric_count = 0

    context = {
        "nodes": [],
        "secret_limits": [],
        "tenant_limits": [],
        "metrics": {},
        "metric_helps": {x[0]: x[1] for x in Metric.NAME_CHOICES},
        "metric_gauges": Metric.GAUGES,
    }

    if not secret_uuid:
        nodes = Node.objects.all()
        for node in nodes:
            context["nodes"].append([node.slug, node.cluster.name, node.load])

    for secret in secrets:
        tenant_slug = secret.tenant.slug
        if secret.sub_id == 0:
            secret_slug = tenant_slug
            context["secret_limits"].append([secret_slug, secret.attendee_limit, secret.meeting_limit])
            context["tenant_limits"].append([secret_slug, secret.tenant.attendee_limit, secret.tenant.meeting_limit])
        else:
            secret_slug = secret.__str__()
            context["secret_limits"].append([secret_slug, secret.attendee_limit, secret.meeting_limit])
        if secret.sub_id != 0:
            metrics = Metric.objects.filter(secret=secret)
        else:
            metrics = Metric.objects.filter(secret__tenant=secret.tenant)

        # group metrics by name
        for metric in metrics:
            if metric.name not in context["metrics"]:
                context["metrics"][metric.name] = {
                    "name_choice": context["metric_helps"][metric.name],
                    "secrets": {}
                }

            if secret_slug in context["metrics"][metric.name]["secrets"]:
                context["metrics"][metric.name]["secrets"][secret_slug]["value"] += metric.value
            else:
                if secret_uuid:
                    context["metrics"][metric.name]["secrets"][secret_slug] = {"value": metric.value}
                else:
                    context["metrics"][metric.name]["secrets"][secret_slug] = {"tenant": tenant_slug, "value": metric.value}
                metric_count += 1

    if secret_uuid:
        with transaction.atomic():
            obj, created = SecretMetricsList.objects.update_or_create(secret=secrets[0], defaults={'metrics': render_to_string(template_name=template, context=context)})
    else:
        with transaction.atomic():
            obj, created = SecretMetricsList.objects.update_or_create(secret=None, defaults={'metrics': render_to_string(template_name=template, context=context)})

    mode = "Update"
    if created:
        mode = "Create"
    return f"{mode} list with {metric_count} metrics for {secret_text}."

def update_tenant_statistics(tenant_uuid):
    stats_combination = []
    try:
        tenant = Tenant.objects.get(uuid=tenant_uuid)
    except ObjectDoesNotExist:
        return {}

    result = {tenant.slug: {}}

    stats = Stats.objects.filter(tenant=tenant)
    meetings_all = Meeting.objects.filter(secret__tenant=tenant)
    statistics = MeetingStats()

    # update existing stats
    for stat in stats:
        meetings_filter = meetings_all.filter(bbb_origin=stat.bbb_origin, bbb_origin_server_name=stat.bbb_origin_server_name)
        stats_combination.append([stat.bbb_origin, stat.bbb_origin_server_name])

        statistics.__init__()

        for meeting in meetings_filter:
            if not meeting.node.has_errors:
                statistics.add_meeting_stats(meeting.attendees, meeting.listenerCount, meeting.voiceParticipantCount, meeting.moderatorCount, meeting.videoCount)
            meetings_all = meetings_all.exclude(id=meeting.id)

        stat.update_values(statistics)

        if stat.bbb_origin_server_name not in result[tenant.slug]:
            result[tenant.slug][stat.bbb_origin_server_name] = {}
            if stat.bbb_origin not in result[tenant.slug][stat.bbb_origin_server_name]:
                result[tenant.slug][stat.bbb_origin_server_name][stat.bbb_origin] = statistics.get_values()

    # add new stats combinations
    new_combinations = []
    for meeting in meetings_all:
        if [meeting.bbb_origin, meeting.bbb_origin_server_name] not in stats_combination and meeting.bbb_origin_server_name and meeting.bbb_origin and not meeting.node.has_errors:
            new_combinations.append([meeting.bbb_origin, meeting.bbb_origin_server_name])
            stat = Stats(tenant=tenant, bbb_origin=meeting.bbb_origin, bbb_origin_server_name=meeting.bbb_origin_server_name)
            stat.save()
            stats_combination.append([meeting.bbb_origin, meeting.bbb_origin_server_name])

    # fill new combinations with data
    for new_combination in new_combinations:
        bbb_origin = new_combination[0]
        bbb_origin_server_name = new_combination[1]
        stat = Stats.objects.get(tenant=tenant, bbb_origin=bbb_origin, bbb_origin_server_name=bbb_origin_server_name)
        meetings_filter = meetings_all.filter(bbb_origin=stat.bbb_origin, bbb_origin_server_name=stat.bbb_origin_server_name)

        statistics.__init__()

        for meeting in meetings_filter:
            if not meeting.node.has_errors:
                statistics.add_meeting_stats(meeting.attendees, meeting.listenerCount, meeting.voiceParticipantCount, meeting.moderatorCount, meeting.videoCount)

        stat.update_values(statistics)

        if stat.bbb_origin_server_name not in result[tenant.slug]:
            result[tenant.slug][stat.bbb_origin_server_name] = {}
            if stat.bbb_origin not in result[tenant.slug][stat.bbb_origin_server_name]:
                result[tenant.slug][stat.bbb_origin_server_name][stat.bbb_origin] = statistics.get_values()

    return result
