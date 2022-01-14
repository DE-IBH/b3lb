from django.db import transaction
from rest.models import Node, Meeting, Metric, Secret, SecretMetricsList, Stats, Tenant
from rest.utils import load_template


def celery_statistic_fill_by_tenant(tenant_uuid):
    stats_combination = []
    try:
        tenant = Tenant.objects.get(uuid=tenant_uuid)
    except Tenant.DoesNotExist:
        return {}

    result = {tenant.slug: {}}

    stats = Stats.objects.filter(tenant=tenant)
    meetings_all = Meeting.objects.filter(secret__tenant=tenant)

    # update existing stats
    for stat in stats:
        meetings_filter = meetings_all.filter(bbb_origin=stat.bbb_origin, bbb_origin_server_name=stat.bbb_origin_server_name)
        stats_combination.append([stat.bbb_origin, stat.bbb_origin_server_name])

        attendees = 0
        meetings = 0
        listener_count = 0
        voice_participant_count = 0
        moderator_count = 0
        video_count = 0

        for meeting in meetings_filter:
            if not meeting.node.has_errors:
                attendees += meeting.attendees
                meetings += 1
                listener_count += meeting.listenerCount
                voice_participant_count += meeting.voiceParticipantCount
                moderator_count += meeting.moderatorCount
                video_count += meeting.videoCount
            meetings_all = meetings_all.exclude(id=meeting.id)

        stat.attendees = attendees
        stat.meetings = meetings
        stat.listenerCount = listener_count
        stat.voiceParticipantCount = voice_participant_count
        stat.moderatorCount = moderator_count
        stat.videoCount = video_count
        stat.save()

        if stat.bbb_origin_server_name not in result[tenant.slug]:
            result[tenant.slug][stat.bbb_origin_server_name] = {}
            if stat.bbb_origin not in result[tenant.slug][stat.bbb_origin_server_name]:
                result[tenant.slug][stat.bbb_origin_server_name][stat.bbb_origin] = [meetings, attendees, listener_count, voice_participant_count, moderator_count, video_count]

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

        attendees = 0
        meetings = 0
        listener_count = 0
        voice_participant_count = 0
        moderator_count = 0
        video_count = 0

        for meeting in meetings_filter:
            if not meeting.node.has_errors:
                attendees += meeting.attendees
                meetings += 1
                listener_count += meeting.listenerCount
                voice_participant_count += meeting.voiceParticipantCount
                moderator_count += meeting.moderatorCount
                video_count += meeting.videoCount

        stat.attendees = attendees
        stat.meetings = meetings
        stat.listenerCount = listener_count
        stat.voiceParticipantCount = voice_participant_count
        stat.moderatorCount = moderator_count
        stat.videoCount = video_count
        stat.save()

        if stat.bbb_origin_server_name not in result[tenant.slug]:
            result[tenant.slug][stat.bbb_origin_server_name] = {}
            if stat.bbb_origin not in result[tenant.slug][stat.bbb_origin_server_name]:
                result[tenant.slug][stat.bbb_origin_server_name][stat.bbb_origin] = [meetings, attendees, listener_count, voice_participant_count, moderator_count, video_count]

    return result


def celery_update_metrics(secret_uuid):
    if secret_uuid:
        secret_zero = Secret.objects.get(uuid=secret_uuid)
        if secret_zero.sub_id == 0:
            secrets = Secret.objects.filter(tenant=secret_zero.tenant)
        else:
            secrets = [secret_zero]
        del secret_zero
        template = load_template("metrics_secret")
        secret_text = secrets[0].__str__()
    else:
        secrets = Secret.objects.all()
        template = load_template("metrics_all")
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
            obj, created = SecretMetricsList.objects.update_or_create(secret=secrets[0], defaults={'metrics': template.render(context)})
    else:
        with transaction.atomic():
            obj, created = SecretMetricsList.objects.update_or_create(secret=None, defaults={'metrics': template.render(context)})

    if created:
        return "Create list with {} metrics for {}.".format(metric_count, secret_text)
    else:
        return "Update list with {} metrics for {}.".format(metric_count, secret_text)
