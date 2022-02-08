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


import hashlib
import re
import rest.utils as utils
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F, Sum
from django.conf import settings
from random import randint
from rest.models import ClusterGroupRelation, Meeting, Metric, Node, Parameter, RecordSet, Secret, Tenant
from rest.utils import load_template
from urllib.parse import urlencode
from xml.etree import ElementTree


##
# CONSTANTS
##
slug_regex = re.compile(r'([a-z]{2,10})(-(\d{3}))?\.' + re.escape(settings.B3LB_API_BASE_DOMAIN) + '$')

# symbols not to be encoded to match bbb's checksum calculation
SAFE_QUOTE_SYMBOLS = '*'

# wrap metric counters
METRIC_BIGINT_MODULO = 9223372036854775808


##
# Routines
##
@sync_to_async
def check_meeting_node(meeting):
    return meeting and meeting.node and not meeting.node.has_errors


def check_parameter(params, tenant, join=False):
    parameters = Parameter.objects.filter(tenant=tenant)

    if join:
        endpoint_parameters = Parameter.PARAMETERS_JOIN
    else:
        endpoint_parameters = Parameter.PARAMETERS_CREATE

    for parameter in parameters:
        if parameter.parameter in endpoint_parameters:
            if parameter.parameter in params:
                if parameter.mode == Parameter.BLOCK:
                    del params[parameter.parameter]
                elif parameter.mode == Parameter.OVERRIDE:
                    params[parameter.parameter] = parameter.value
            elif parameter.mode in [Parameter.SET, Parameter.OVERRIDE]:
                params[parameter.parameter] = parameter.value

    return params


@sync_to_async
def check_tenant(secret, checksum, endpoint, query_string):
    if secret:
        sha_1 = hashlib.sha1()

        query_string = query_string.replace("&checksum=" + checksum, "")
        query_string = query_string.replace("checksum=" + checksum + "&", "")
        query_string = query_string.replace("checksum=" + checksum, "")

        sha_1.update("{}{}{}".format(endpoint, query_string, secret).encode())
        if sha_1.hexdigest() == checksum:
            return True
        return False
    else:
        return False


def del_metric(name, secret, node):
    Metric.objects.filter(name=name, secret=secret, node=node).delete()


@sync_to_async
def get_cluster_group_from_secret(secret):
    return secret.tenant.cluster_group


def get_endpoint_str(endpoint, params, secret):
    parameter_str = ""

    if params:
        parameter_str = urlencode(params, safe=SAFE_QUOTE_SYMBOLS)

    sha_1 = hashlib.sha1()
    sha_1.update("{}{}{}".format(endpoint, parameter_str, secret).encode())

    if params:
        return "{}?{}&checksum={}".format(endpoint, parameter_str, sha_1.hexdigest())
    else:
        return "{}?checksum={}".format(endpoint, sha_1.hexdigest())


@sync_to_async
def get_internal_id(secret, external_id):
    encoded_string = "{}\0{}\0".format(settings.B3LB_SITE_SLUG, secret.uuid, external_id).encode()
    return hashlib.sha256(encoded_string).hexdigest()


@sync_to_async
def get_meeting_node(meeting):
    if not meeting:
        return None
    if meeting.node.has_errors:
        return None
    return meeting.node


@sync_to_async
def get_node_params_by_lowest_workload(cluster_group):
    lowest = 10000000
    lowest_node_list = []
    for cluster_relation in ClusterGroupRelation.objects.filter(cluster_group=cluster_group):
        for node in Node.objects.filter(cluster=cluster_relation.cluster):
            if 0 <= node.load <= lowest:
                if node.load == lowest:
                    lowest_node_list.append(node)
                else:
                    lowest_node_list = [node]
                    lowest = node.load

    # return randomized node if multiple are possible
    if lowest_node_list:
        return lowest_node_list[randint(0, len(lowest_node_list) - 1)]
    else:
        return None


def get_slug(request, slug, sub_id):
    if slug is None:
        host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST'))
        host = utils.forwarded_host_regex.sub(r'\1', host)

        regex_search = slug_regex.search(host)
        if regex_search:
            return regex_search.group(1).upper(), int(regex_search.group(3) or 0)
        else:
            return None, None
    else:
        return slug, int(sub_id)


def get_request_secret(request, slug, sub_id):
    (slug, sub_id) = get_slug(request, slug, sub_id)
    if not slug:
        return None

    try:
        return Secret.objects.select_related("tenant", "tenant__asset").get(tenant__slug=slug, sub_id=sub_id)
    except ObjectDoesNotExist:
        return None


def get_request_tenant(request, slug, sub_id):
    (slug, sub_id) = get_slug(request, slug, sub_id)
    if not slug:
        return None

    try:
        return Tenant.objects.get(slug=slug)
    except ObjectDoesNotExist:
        return None


@sync_to_async
def get_running_meeting(internal_id):
    """
    Get running meeting or returns None when meeting is non-existing.
    """
    if internal_id is None:
        return None

    with transaction.atomic():
        try:
            meeting = Meeting.objects.get(id=internal_id)
            return meeting
        except ObjectDoesNotExist:
            return None


def get_slide_body_for_post(secret):
    slide_base64 = secret.tenant.asset.slide_base64
    if slide_base64:
        return '<modules><module name="presentation"><document name="{}">{}</document></module></modules>'.format(secret.tenant.asset.s_filename, slide_base64)
    else:
        return '<modules><module name="presentation"><document url="{}" filename="{}"></document></module></modules>'.format(secret.tenant.asset.slide_url, secret.tenant.asset.s_filename)


def incr_metric(name, secret, node=None, incr=1):
    if Metric.objects.filter(name=name, secret=secret, node=node).update(value=(F("value") + incr) % METRIC_BIGINT_MODULO) == 0:
        metric, created = Metric.objects.get_or_create(name=name, secret=secret, node=node)
        metric.value = (F("value") + incr) % METRIC_BIGINT_MODULO
        metric.save(update_fields=["value"])


@sync_to_async
def limit_check(secret):
    if secret.tenant.meeting_limit > 0 and not Meeting.objects.filter(secret__tenant=secret.tenant).count() < secret.tenant.meeting_limit:
        incr_metric(Metric.MEETING_LIMIT_HITS, Secret.objects.get(tenant=secret.tenant, sub_id=0))
        return False

    if secret.meeting_limit > 0 and not Meeting.objects.filter(secret=secret).count() < secret.meeting_limit:
        incr_metric(Metric.MEETING_LIMIT_HITS, secret)
        return False

    if secret.tenant.attendee_limit > 0:
        attendee_sum = Meeting.objects.filter(secret__tenant=secret.tenant).aggregate(Sum('attendees'))["attendees__sum"]
        # Aggregation sum can return None or [0, inf).
        # Only check for limit if aggregation sum is an integer.
        if isinstance(attendee_sum, int) and not attendee_sum < secret.tenant.attendee_limit:
            incr_metric(Metric.ATTENDEE_LIMIT_HITS, Secret.objects.get(tenant=secret.tenant, sub_id=0))
            return False

    if secret.attendee_limit > 0:
        attendee_sum = Meeting.objects.filter(secret=secret).aggregate(Sum('attendees'))["attendees__sum"]
        # Same as above
        if isinstance(attendee_sum, int) and not attendee_sum < secret.attendee_limit:
            incr_metric(Metric.ATTENDEE_LIMIT_HITS, secret)
            return False
    return True


@sync_to_async
def replace_information_in_xml(response, endpoint, meeting):
    response_json = {"response": {}}
    if response and meeting and endpoint == "getMeetingInfo":
        try:
            recording_ready_url = utils.xml_escape(RecordSet.objects.get(meeting_relation=meeting).recording_ready_origin_url)
        except RecordSet.DoesNotExist:
            recording_ready_url = ""
        xml = ElementTree.fromstring(response)
        template = load_template("getMeetingInfo.xml")
        for category in xml:
            if category.tag == "attendees":
                response_json["response"]["attendees"] = []
                for sub_cat in category:
                    if sub_cat.tag == "attendee":
                        element_json = {}
                        for element in sub_cat:
                            element_json[element.tag] = utils.xml_escape(element.text)
                        response_json["response"]["attendees"].append(element_json)
            elif category.tag == "meetingID":  # replace internal with external id
                response_json["response"]["meetingID"] = utils.xml_escape(meeting.external_id)
            elif category.tag == "metadata":
                response_json["response"]["metadata"] = {}
                for sub_cat in category:  # filter b3lb specific meta data information
                    if sub_cat.tag not in ["{}-recordset".format(settings.B3LB_SITE_SLUG), "endcallbackurl", "bbb-recording-ready-url"]:
                        response_json["response"]["metadata"][sub_cat.tag] = utils.xml_escape(sub_cat.text)
                    elif sub_cat.tag == "endcallbackurl":
                        if meeting.end_callback_url:
                            response_json["response"]["metadata"][sub_cat.tag] = utils.xml_escape(meeting.end_callback_url)
                    elif sub_cat.tag == "bbb-recording-ready-url":
                        if recording_ready_url:
                            response_json["response"]["metadata"][sub_cat.tag] = utils.xml_escape(recording_ready_url)
            else:
                response_json["response"][category.tag] = utils.xml_escape(category.text)
        if recording_ready_url:
            if "metadata" in response_json["response"]:
                response_json["response"]["metadata"]["bbb-recording-ready-url"] = recording_ready_url
            else:
                response_json["response"]["metadata"] = {"bbb-recording-ready-url": recording_ready_url}
        return template.render(response_json)
    elif response and meeting and endpoint == "create":
        xml = ElementTree.fromstring(response)
        template = load_template("create.xml")
        for category in xml:
            if category.tag == "meetingID":  # replace internal with external id
                response_json["response"]["meetingID"] = utils.xml_escape(meeting.external_id)
            else:
                response_json["response"][category.tag] = utils.xml_escape(category.text)
        return template.render(response_json)
    return response


def set_metric(name, secret, node, value):
    if Metric.objects.filter(name=name, secret=secret, node=node).update(value=value) == 0:
        metric, created = Metric.objects.get_or_create(name=name, secret=secret, node=node)
        metric.value = value
        metric.save(update_fields=["value"])


@sync_to_async
def update_create_metrics(secret, node):
    # add penalty points for a new meeting on the node
    node = Node.objects.get(uuid=node.uuid)
    node.attendees = F("attendees") + 1
    node.meetings = F("meetings") + 1
    node.save(update_fields=["attendees", "meetings"])

    # update metric stats
    incr_metric(Metric.CREATED, secret, node)
