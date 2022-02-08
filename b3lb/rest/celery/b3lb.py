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
from rest.models import Metric, Node, NodeMeetingList, Meeting, RecordSet, Secret, SecretMeetingList
from rest.utils import load_template
import rest.endpoints.b3lb.lb as lb
import rest.utils as utils
import rest.endpoints.b3lb.constants as constants
import xml.etree.ElementTree as ElementTree
import requests as rq
import json


def celery_run_check_node(uuid):
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
        response = rq.get(node.load_base_url, timeout=settings.B3LB_NODE_REQUEST_TIMEOUT)
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
        response = rq.get(url, timeout=settings.B3LB_NODE_REQUEST_TIMEOUT)
        if response.status_code == 200:
            get_meetings_text = response.content.decode('utf-8')
            cache.set(settings.B3LB_CACHE_NML_PATTERN.format(uuid), get_meetings_text, timeout=settings.B3LB_CACHE_NML_TIMEOUT)
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
        cache.set(settings.B3LB_CACHE_NML_PATTERN.format(uuid), constants.RETURN_STRING_GET_MEETINGS_NO_MEETINGS, timeout=settings.B3LB_CACHE_NML_TIMEOUT)
        with transaction.atomic():
            NodeMeetingList.objects.update_or_create(node=node, defaults={'xml': constants.RETURN_STRING_GET_MEETINGS_NO_MEETINGS})

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
                # delete meeting if endMeetingCallback was received or no meeting on Node and lifetime > 5 seconds
                if mci_lifetime > 5 or not meeting.is_running:
                    # update duration metric only for non-zombie meetings
                    # (duration < 12h)
                    if mci_lifetime < 43200:
                        lb.incr_metric(Metric.DURATION_COUNT, meeting.secret, node)
                        lb.incr_metric(Metric.DURATION_SUM, meeting.secret, node, mci_lifetime)
                    meeting.delete()

        with transaction.atomic():
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


def celery_update_get_meetings_xml(secret_uuid):
    secret = Secret.objects.get(uuid=secret_uuid)
    if secret.sub_id == 0:
        mcis = Meeting.objects.filter(secret__tenant=secret.tenant)
    else:
        mcis = Meeting.objects.filter(secret=secret)

    internal_meeting_ids = {}

    for mci in mcis:
        try:
            recording_ready_url = RecordSet.objects.get(meeting_relation=mci).recording_ready_origin_url
        except RecordSet.DoesNotExist:
            recording_ready_url = ""
        internal_meeting_ids[mci.id] = {
            "external_id": utils.xml_escape(mci.external_id),
            "end_callback_url": utils.xml_escape(mci.end_callback_url),
            "recording_ready_url": utils.xml_escape(recording_ready_url)
        }

    nodes = Node.objects.all()
    context = {"meetings": []}
    template = load_template("getMeetings.xml")

    for node in nodes:
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
                                                element_json[element.tag] = utils.xml_escape(element.text)
                                            meeting_json["attendees"].append(element_json)
                                elif sub_cat.tag == "metadata":
                                    if "metadata" not in meeting_json:
                                        meeting_json["metadata"] = {}
                                    for ssub_cat in sub_cat:
                                        if ssub_cat.tag not in ["{}-recordset".format(settings.B3LB_SITE_SLUG), "endcallbackurl", "bbb-recording-ready-url"]:
                                            meeting_json["metadata"][ssub_cat.tag] = utils.xml_escape(ssub_cat.text)
                                elif sub_cat.tag == "meetingID":
                                    if sub_cat.text not in internal_meeting_ids:
                                        add_to_response = False
                                        break
                                    else:
                                        meeting_json["meetingID"] = internal_meeting_ids[sub_cat.text]["external_id"]
                                        if internal_meeting_ids[sub_cat.text]["end_callback_url"]:
                                            if "metadata" not in meeting_json:
                                                meeting_json["metadata"] = {
                                                    "endcallbackurl": internal_meeting_ids[sub_cat.text]["end_callback_url"],
                                                    "bbb-recording-ready-url": internal_meeting_ids[sub_cat.text]["recording_ready_url"]
                                                }
                                            else:
                                                meeting_json["metadata"]["endcallbackurl"] = utils.xml_escape(internal_meeting_ids[sub_cat.text]["end_callback_url"])
                                else:
                                    meeting_json[sub_cat.tag] = utils.xml_escape(sub_cat.text)

                            if add_to_response:
                                context["meetings"].append(meeting_json)
        except:
            continue

    if context["meetings"]:
        response = template.render(context)
    else:
        response = constants.RETURN_STRING_GET_MEETINGS_NO_MEETINGS

    with transaction.atomic():
        obj, created = SecretMeetingList.objects.update_or_create(secret=secret, defaults={'xml': response})

    if created:
        return "{} MeetingListXML created.".format(secret.__str__())
    else:
        return "{} MeetingListXML updated.".format(secret.__str__())
