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


from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from rest.models import Metric, Node, Meeting, Slide, Stats, Tenant, Secret, SecretMeetingList, NodeMeetingList, SecretMetricsList
import rest.b3lb.lb as lb
import os
import xml.etree.ElementTree as ElementTree
import requests as rq
import json
from jinja2 import Template

#
# Celery task routines
#
LIMIT_METRICS = [("attendee_limit", "Attendee soft limit"), ("meeting_limit", "Attendee soft limit")]


#
# Celery task routines
#
def run_check_node(uuid):
    meeting_dict = {}
    parameter_list_int = [
        "participantCount",
        "listenerCount",
        "voiceParticipantCount",
        "videoCount",
        "moderatorCount"
    ]

    parameter_list_str = ["bbb-origin", "bbb-origin-server-name"]

    node = Node.objects.get(uuid=uuid)

    try:
        response = rq.get(node.load_base_url, timeout=settings.NODE_REQUEST_TIMEOUT)
        if response.status_code == 200:
            if response.text.find('\n') != -1:
                with transaction.atomic():
                    node_temporary = Node.objects.select_for_update().get(uuid=uuid)
                    node_temporary.cpu_load = int(response.text.split('\n')[0])
                    node_temporary.save()
    except:
        # Do nothing and keep last cpu load value
        pass

    url = node.api_base_url + lb.get_endpoint_str("getMeetings", {}, node.secret)
    has_errors = True
    attendees = 0
    meetings = 0

    try:
        response = rq.get(url, timeout=settings.NODE_REQUEST_TIMEOUT)
        if response.status_code == 200:
            get_meetings_text = response.content.decode('utf-8')
            cache.set(settings.CACHE_NML_PATTERN.format(uuid), get_meetings_text, timeout=settings.CACHE_NML_TIMEOUT)
            with transaction.atomic():
                NodeMeetingList.objects.update_or_create(node=node, defaults={'xml': get_meetings_text})

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
                                    meeting_dict[meeting_id] = {
                                        "participantCount": 0,
                                        "listenerCount": 0,
                                        "voiceParticipantCount": 0,
                                        "videoCount": 0,
                                        "moderatorCount": 0,
                                        "bbb-origin": "",
                                        "bbb-origin-server-name": ""
                                    }
                            for meeting_element in meeting:
                                if meeting_element.tag in parameter_list_int:
                                    meeting_dict[meeting_id][meeting_element.tag] = int(meeting_element.text)
                                if meeting_element.tag == "participantCount":
                                    attendee_dummy = int(meeting_element.text)
                                elif meeting_element.tag == "isBreakout":
                                    if meeting_element.text == "false":
                                        meetings += 1
                                    else:
                                        attendee_dummy = 0
                                elif meeting_element.tag == "metadata":
                                    for cell in meeting_element:
                                        if cell.tag in parameter_list_str:
                                            meeting_dict[meeting_id][cell.tag] = cell.text
                            attendees += attendee_dummy
            has_errors = False
    except:
        pass

    if has_errors:
        cache.set(settings.CACHE_NML_PATTERN.format(uuid), settings.RETURN_STRING_GET_MEETINGS_NO_MEETINGS, timeout=settings.CACHE_NML_TIMEOUT)
        with transaction.atomic():
            NodeMeetingList.objects.update_or_create(node=node, defaults={'xml': settings.RETURN_STRING_GET_MEETINGS_NO_MEETINGS})

    with transaction.atomic():
        node_temporary = Node.objects.select_for_update().get(uuid=node.uuid)
        node_temporary.has_errors = has_errors
        node_temporary.attendees = attendees
        node_temporary.meetings = meetings
        node_temporary.save()
        load = node_temporary.load

    if not has_errors:
        metrics = {}
        metric_keys = [
            Metric.ATTENDEES,
            Metric.LISTENERS,
            Metric.VOICES,
            Metric.VIDEOS,
            Metric.MEETINGS,
        ]

        for meeting in Meeting.objects.filter(node=node):
            if meeting.id in meeting_dict:
                if meeting.secret not in metrics:
                    metrics[meeting.secret] = {k: 0 for k in metric_keys}
                m = metrics[meeting.secret]

                m[Metric.MEETINGS] += 1

                meeting.attendees = meeting_dict[meeting.id]["participantCount"]
                m[Metric.ATTENDEES] += meeting_dict[meeting.id]["participantCount"]

                meeting.listenerCount = meeting_dict[meeting.id]["listenerCount"]
                m[Metric.LISTENERS] += meeting_dict[meeting.id]["listenerCount"]

                meeting.voiceParticipantCount = meeting_dict[meeting.id]["voiceParticipantCount"]
                m[Metric.VOICES] += meeting_dict[meeting.id]["voiceParticipantCount"]

                meeting.videoCount = meeting_dict[meeting.id]["videoCount"]
                m[Metric.VIDEOS] += meeting_dict[meeting.id]["videoCount"]

                meeting.moderatorCount = meeting_dict[meeting.id]["moderatorCount"]

                meeting.bbb_origin = meeting_dict[meeting.id]["bbb-origin"]
                meeting.bbb_origin_server_name = meeting_dict[meeting.id]["bbb-origin-server-name"]
                meeting.save()
            else:
                mci_lifetime = (timezone.now() - meeting.age).seconds
                if mci_lifetime > 5:
                    # delete meeting and update duration metric only for non-zombie meetings
                    # (duration < 12h)
                    if mci_lifetime < 43200:
                        lb.incr_metric(Metric.DURATION_COUNT, meeting.secret, node)
                        lb.incr_metric(Metric.DURATION_SUM, meeting.secret, node, mci_lifetime)
                    meeting.delete()

        for secret in Secret.objects.all():
            if secret in metrics:
                for name in metric_keys:
                    if name in Metric.GAUGES:
                        lb.set_metric(name, secret, node, metrics[secret][name])
                    else:
                        lb.incr_metric(name, secret, node, metrics[secret][name])
            else:
                for name in metric_keys:
                    if name in Metric.GAUGES:
                        lb.set_metric(name, secret, node, 0)

    return json.dumps([node.slug, load, meetings, attendees])


def run_check_slides():
    slide_dir = "rest/slides/"
    slide_files = os.listdir(slide_dir)
    slide_files.append(settings.NO_CUSTOM_SLIDE_STRING)
    slides = {}

    # check for new slide files
    for slide_file in slide_files:
        try:
            Slide.objects.get(name=slide_file)
        except ObjectDoesNotExist:
            slide = Slide(name=slide_file)
            slide.save()
            slides[slide_file] = "added"

    # check for deleted slide files
    for slide in Slide.objects.all():
        if slide.name not in slide_files:
            slide.delete()
            slides[slide.name] = "deleted"
        else:
            slides[slide.name] = "keeping"

    return slides


def fill_statistic_by_tenant(tenant_uuid):
    stats_combination = []
    try:
        tenant = Tenant.objects.get(uuid=tenant_uuid)
    except ObjectDoesNotExist:
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


def load_template(file_name):
    with open("rest/templates/{}".format(file_name)) as template_file:
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

    nodes = Node.objects.all()
    context = {"meetings": []}
    template = load_template("getMeetings.xml")

    for node in nodes:
        try:
            try:
                node_meeting = cache.get(settings.CACHE_NML_PATTERN.format(node.uuid))
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
                                                element_json[element.tag] = lb.xml_escape(element.text)
                                            meeting_json["attendees"].append(element_json)
                                elif sub_cat.tag == "metadata":
                                    meeting_json["metadata"] = {}
                                    for ssub_cat in sub_cat:
                                        meeting_json["metadata"][ssub_cat.tag] = lb.xml_escape(ssub_cat.text)
                                else:
                                    meeting_json[sub_cat.tag] = lb.xml_escape(sub_cat.text)

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
        response = settings.RETURN_STRING_GET_MEETINGS_NO_MEETINGS

    with transaction.atomic():
        obj, created = SecretMeetingList.objects.update_or_create(secret=secret, defaults={'xml': response})

    if created:
        return "{} MeetingListXML created.".format(secret.__str__())
    else:
        return "{} MeetingListXML updated.".format(secret.__str__())


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

    if created:
        return "Create list with {} metrics for {}.".format(metric_count, secret_text)
    else:
        return "Update list with {} metrics for {}.".format(metric_count, secret_text)
