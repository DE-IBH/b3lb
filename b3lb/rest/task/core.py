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
from django.template.loader import render_to_string
from django.utils import timezone
from json import dumps
from requests import get
from rest.b3lb.contants import RETURN_STRING_GET_MEETINGS_NO_MEETINGS
from rest.b3lb.metrics import incr_metric, set_metric
from rest.b3lb.utils import xml_escape
from rest.classes.checks import NodeCheck
from rest.models import Meeting, Metric, Node, NodeMeetingList, Secret, SecretMeetingList
from xml.etree import ElementTree


def check_node(check: NodeCheck):
    try:
        response = get(check.node.load_base_url, timeout=settings.B3LB_NODE_REQUEST_TIMEOUT)
        if response.status_code == 200:
            if response.text.find('\n') != -1:
                with transaction.atomic():
                    node = Node.objects.select_for_update().get(uuid=check.node.uuid)
                    node.cpu_load = int(response.text.split('\n')[0])
                    node.save()
    except:
        # Do nothing and keep last cpu load value
        pass

    try:
        response = get(check.get_meetings_url(), timeout=settings.B3LB_NODE_REQUEST_TIMEOUT)
        if response.status_code == 200:
            get_meetings_text = response.content.decode('utf-8')
            cache.set(settings.B3LB_CACHE_NML_PATTERN.format(check.node.uuid), get_meetings_text, timeout=settings.B3LB_CACHE_NML_TIMEOUT)
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
        cache.set(settings.B3LB_CACHE_NML_PATTERN.format(check.node.uuid), RETURN_STRING_GET_MEETINGS_NO_MEETINGS, timeout=settings.B3LB_CACHE_NML_TIMEOUT)
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


def generate_secret_get_meetings(secret: Secret):
    if secret.sub_id == 0:
        mcis = Meeting.objects.filter(secret__tenant=secret.tenant)
    else:
        mcis = Meeting.objects.filter(secret=secret)

    meeting_ids = []

    for mci in mcis:
        meeting_ids.append(mci.id)

    context = {"meetings": []}

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
        response = render_to_string(template_name="getMeetings.xml", context=context)
    else:
        response = RETURN_STRING_GET_MEETINGS_NO_MEETINGS

    with transaction.atomic():
        obj, created = SecretMeetingList.objects.update_or_create(secret=secret, defaults={'xml': response})

    mode = "updated"
    if created:
        mode = "created"
    return f"{secret.__str__()} MeetingListXML {mode}."
