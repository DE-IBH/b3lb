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


from django.db import transaction
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from jinja2 import Template
from json import dumps
from requests import get
from rest.b3lb.metrics import incr_metric, set_metric
from rest.b3lb.utils import xml_escape
from rest.classes.api import RETURN_STRING_GET_MEETINGS_NO_MEETINGS
from rest.classes.checks import NodeCheck
from rest.classes.statistics import MeetingStats
from rest.models import Asset, AssetLogo, AssetSlide, Node, NodeMeetingList, Meeting, Metric, Record, RecordProfile, RecordSet, Secret, SecretMeetingList, SecretMetricsList, Stats, Tenant
from shlex import split
from tempfile import TemporaryDirectory
import os
import subprocess as sp
import xml.etree.ElementTree as ElementTree



#
# Celery task routines
#
def cleanup_assets():
    slides = list(AssetSlide.objects.all())
    logos = list(AssetLogo.objects.all())
    assets = Asset.objects.all()

    for asset in assets:
        for slide_index in range(len(slides)-1, -1, -1):
            if asset.slide.name == slides[slide_index].filename:
                del slides[slide_index]
        for logo_index in range(len(logos)-1, -1, -1):
            if asset.logo.name == logos[logo_index].filename:
                del logos[logo_index]

    del assets

    slides_deleted = 0
    for slide in slides:
        slide.delete()
        slides_deleted += 1
    logos_deleted = 0
    for logo in logos:
        logo.delete()
        logos_deleted += 1

    return "Delete {} slides and {} logos.".format(slides_deleted, logos_deleted)


def run_check_node(uuid):
    check = NodeCheck(uuid)
    try:
        response = get(check.node.load_base_url, timeout=settings.B3LB_NODE_REQUEST_TIMEOUT)
        if response.status_code == 200:
            if response.text.find('\n') != -1:
                with transaction.atomic():
                    node = Node.objects.select_for_update().get(uuid=uuid)
                    node.cpu_load = int(response.text.split('\n')[0])
                    node.save()
    except:
        # Do nothing and keep last cpu load value
        pass

    try:
        response = get(check.get_meetings_url(), timeout=settings.B3LB_NODE_REQUEST_TIMEOUT)
        if response.status_code == 200:
            get_meetings_text = response.content.decode('utf-8')
            cache.set(settings.B3LB_CACHE_NML_PATTERN.format(uuid), get_meetings_text, timeout=settings.B3LB_CACHE_NML_TIMEOUT)
            with transaction.atomic():
                NodeMeetingList.objects.update_or_create(node=check.node, defaults={'xml': get_meetings_text})

            xml = ElementTree.fromstring(get_meetings_text)

            del get_meetings_text  # remove plain xml text from RAM

            for body in xml:
                if body.tag == "error" or (body.tag == "returncode" and body.text == "FAILED"):
                    raise Exception("Error detected in xml return code")
                if body.tag == "meetings":
                    for meeting in body:
                        if meeting.tag == "meeting":
                            attendee_dummy = 0
                            meeting_id = ""
                            for meeting_element in meeting:
                                if meeting_element.tag == "meetingID":
                                    meeting_id = meeting_element.text
                                    check.add_meeting_to_stats(meeting_id)
                            for meeting_element in meeting:
                                if meeting_element.tag in check.PARAMETERS_INT:
                                    check.meeting_stats[meeting_id][meeting_element.tag] = int(meeting_element.text)
                                if meeting_element.tag == "participantCount":
                                    attendee_dummy = int(meeting_element.text)
                                elif meeting_element.tag == "isBreakout":
                                    if meeting_element.text == "false":
                                        check.meetings += 1
                                    else:
                                        attendee_dummy = 0
                                elif meeting_element.tag == "metadata":
                                    for cell in meeting_element:
                                        if cell.tag in check.PARAMETERS_STR:
                                            check.meeting_stats[meeting_id][cell.tag] = cell.text
                            check.attendees += attendee_dummy
            check.has_errors = False
    except:
        pass

    if check.has_errors:
        cache.set(settings.B3LB_CACHE_NML_PATTERN.format(uuid), RETURN_STRING_GET_MEETINGS_NO_MEETINGS, timeout=settings.B3LB_CACHE_NML_TIMEOUT)
        with transaction.atomic():
            NodeMeetingList.objects.update_or_create(node=check.node, defaults={'xml': RETURN_STRING_GET_MEETINGS_NO_MEETINGS})

    with transaction.atomic():
        node = Node.objects.select_for_update().get(uuid=check.node.uuid)
        node.has_errors = check.has_errors
        node.attendees = check.attendees
        node.meetings = check.meetings
        node.save()
        load = node.load

    if not check.has_errors:
        metrics = {}
        metric_keys = [
            Metric.ATTENDEES,
            Metric.LISTENERS,
            Metric.VOICES,
            Metric.VIDEOS,
            Metric.MEETINGS,
        ]

        for meeting in Meeting.objects.filter(node=check.node):
            if meeting.id in check.meeting_stats:
                if meeting.secret not in metrics:
                    metrics[meeting.secret] = {k: 0 for k in metric_keys}
                m = metrics[meeting.secret]

                m[Metric.MEETINGS] += 1

                meeting.attendees = check.meeting_stats[meeting.id]["participantCount"]
                m[Metric.ATTENDEES] += check.meeting_stats[meeting.id]["participantCount"]

                meeting.listenerCount = check.meeting_stats[meeting.id]["listenerCount"]
                m[Metric.LISTENERS] += check.meeting_stats[meeting.id]["listenerCount"]

                meeting.voiceParticipantCount = check.meeting_stats[meeting.id]["voiceParticipantCount"]
                m[Metric.VOICES] += check.meeting_stats[meeting.id]["voiceParticipantCount"]

                meeting.videoCount = check.meeting_stats[meeting.id]["videoCount"]
                m[Metric.VIDEOS] += check.meeting_stats[meeting.id]["videoCount"]

                meeting.moderatorCount = check.meeting_stats[meeting.id]["moderatorCount"]

                meeting.bbb_origin = check.meeting_stats[meeting.id]["bbb-origin"]
                meeting.bbb_origin_server_name = check.meeting_stats[meeting.id]["bbb-origin-server-name"]
                meeting.save()
            else:
                mci_lifetime = (timezone.now() - meeting.age).seconds
                if mci_lifetime > 5:
                    # delete meeting and update duration metric only for non-zombie meetings
                    # (duration < 12h)
                    if mci_lifetime < 43200:
                        incr_metric(Metric.DURATION_COUNT, meeting.secret, check.node)
                        incr_metric(Metric.DURATION_SUM, meeting.secret, check.node, mci_lifetime)
                    meeting.delete()

        with transaction.atomic():
            for secret in Secret.objects.all():
                if secret in metrics:
                    for name in metric_keys:
                        if name in Metric.GAUGES:
                            set_metric(name, secret, check.node, metrics[secret][name])
                        else:
                            incr_metric(name, secret, check.node, metrics[secret][name])
                else:
                    for name in metric_keys:
                        if name in Metric.GAUGES:
                            set_metric(name, secret, check.node, 0)

    return dumps([check.node.slug, load, check.meetings, check.attendees])


def fill_statistic_by_tenant(tenant_uuid):
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

        statistics.reinit()

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

        statistics.reinit()

        for meeting in meetings_filter:
            if not meeting.node.has_errors:
                statistics.add_meeting_stats(meeting.attendees, meeting.listenerCount, meeting.voiceParticipantCount, meeting.moderatorCount, meeting.videoCount)

        stat.update_values(statistics)

        if stat.bbb_origin_server_name not in result[tenant.slug]:
            result[tenant.slug][stat.bbb_origin_server_name] = {}
            if stat.bbb_origin not in result[tenant.slug][stat.bbb_origin_server_name]:
                result[tenant.slug][stat.bbb_origin_server_name][stat.bbb_origin] = statistics.get_values()

    return result


# ToDo: Use django-template instead of jinja2 -> Needs to update the templates, because of DjangoTemplateErrors
def load_template(file_name):
    with open(f"rest/templates/{file_name}") as template_file:
        return Template(template_file.read())


def update_get_meetings_xml(secret_uuid):
    secret = Secret.objects.get(uuid=secret_uuid)
    if secret.sub_id == 0:
        mcis = Meeting.objects.filter(secret__tenant=secret.tenant)
    else:
        mcis = Meeting.objects.filter(secret=secret)

    meeting_ids = []

    for mci in mcis:
        meeting_ids.append(mci.id)

    context = {"meetings": []}
    template = load_template("getMeetings.xml")

    for node in Node.objects.all():
        try:
            try:
                node_meeting = cache.get(settings.B3LB_CACHE_NML_PATTERN.format(node.uuid))
                if node_meeting is None:
                    node_meeting = NodeMeetingList.objects.get(node=node).xml
            except ObjectDoesNotExist:
                continue

            xml = ElementTree.fromstring(node_meeting)
            for top in xml:
                if top.tag == "meetings":
                    for category in top:
                        if category.tag == "meeting":
                            meeting_json = {}
                            add_to_response = True
                            for sub_cat in category:
                                if sub_cat.tag == "attendees":
                                    meeting_json["attendees"] = []
                                    for ssub_cat in sub_cat:
                                        if ssub_cat.tag == "attendee":
                                            element_json = {}
                                            for element in ssub_cat:
                                                element_json[element.tag] = xml_escape(element.text)
                                            meeting_json["attendees"].append(element_json)
                                elif sub_cat.tag == "metadata":
                                    meeting_json["metadata"] = {}
                                    for ssub_cat in sub_cat:
                                        meeting_json["metadata"][ssub_cat.tag] = xml_escape(ssub_cat.text)
                                else:
                                    meeting_json[sub_cat.tag] = xml_escape(sub_cat.text)

                                if sub_cat.tag == "meetingID":
                                    if sub_cat.text not in meeting_ids:
                                        add_to_response = False
                                        break
                            if add_to_response:
                                context["meetings"].append(meeting_json)
        except:
            continue

    if context["meetings"]:
        response = template.render(context)
    else:
        response = RETURN_STRING_GET_MEETINGS_NO_MEETINGS

    with transaction.atomic():
        obj, created = SecretMeetingList.objects.update_or_create(secret=secret, defaults={'xml': response})

    mode = "updated"
    if created:
        mode = "created"
    return f"{secret.__str__()} MeetingListXML {mode}."


def update_metrics(secret_uuid):
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

    mode = "Update"
    if created:
        mode = "Create"
    return f"{mode} list with {metric_count} metrics for {secret_text}."


# ToDo: S3 Test
def render_record(record_profile: RecordProfile, record_set: RecordSet):
    record, created = Record.objects.get_or_create(record_set=record_set, profile=record_profile)
    with TemporaryDirectory(dir="/data") as tempdir:
        template = load_template(f"render/{record_profile.backend_profile}")
        os.mkdir(f"{tempdir}/in")
        os.mkdir(f"{tempdir}/out")

        # generate backend profile (docker-compose.yml) in tmpdir
        with open(f"{tempdir}/docker-compose.yml", "w") as docker_file:
            docker_file.write(template.render({"tmpdir": f"{tempdir}", "extension": record_profile.file_extension, "commands": split(record_profile.command)}))

        # download raw.tar. ToDo: testing for local storage
        with open(f"{tempdir}/raw.tar", "wb") as raw:
            raw.write(record_set.recording_archive.file.read())

        # unpack tar to IN folder
        sp.Popen(["tar", "-xf", f"{tempdir}/raw.tar", "-C", f"{tempdir}/in/"], stdin=sp.DEVNULL, stdout=sp.PIPE, close_fds=True).wait()

        # render with given profile
        sp.Popen(["docker-compose", "-f", f"{tempdir}/docker-compose.yml", "up"]).wait()

        # check result
        if not os.path.isfile(f"{tempdir}/out/video.{record_profile.file_extension}"):
            raise Exception("No video output")

        # create record entry
        with open(f"{tempdir}/out/video.{record_profile.file_extension}", "rb") as video_file:
            if not created:
                record.file.delete()
            record.file.save(name=f"{record_set.file_path}/{record_profile.name}.{record_profile.file_extension}", content=video_file)
        record.save()
