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


from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from rest.models import Meeting, Metric, Node, ClusterGroupRelation, Secret, Tenant
from urllib.parse import urlencode
from random import randint
import re
from django.db import transaction
from django.db.models import F, Sum
import base64
import hashlib
from django.conf import settings


##
# CONSTANTS
##
slug_regex = re.compile(r'([a-z]{2,10})(-(\d{3}))?\.' + re.escape(settings.API_BASE_DOMAIN) + '$')
forwarded_host_regex = re.compile(r'([^:]+)(:\d+)?$')


##
# Routines
##
def check_auth_token(auth_token, forwarded_host):

    try:
        tenant = Tenant.objects.get(stats_token=auth_token)
        if tenant.hostname == forwarded_host:
            return True
        else:
            return False
    except ObjectDoesNotExist:
        return False
    except ValidationError:
        return False


@sync_to_async
def check_meeting_existence(meeting_id, secret):
    if meeting_id is None:
        return get_node_params_by_lowest_workload(secret.tenant.cluster_group)

    with transaction.atomic():
        try:
            meeting = Meeting.objects.get(id=meeting_id, secret=secret)
            return meeting.node
        except ObjectDoesNotExist:
            return get_node_params_by_lowest_workload(secret.tenant.cluster_group)


def check_tenant(secret, checksum, endpoint, params):
    if secret:
        sha_1 = hashlib.sha1()
        parameter_str = ""

        if params:
            parameter_str += "{}".format(urlencode(params, safe=settings.SAFE_QUOTE_SYMBOLS))

        sha_1.update("{}{}{}".format(endpoint, parameter_str, secret).encode())
        if sha_1.hexdigest() == checksum:
            return True
        return False
    else:
        return False


def del_metric(name, secret, node):
    Metric.objects.filter(name=name, secret=secret, node=node).delete()


def get_endpoint_str(endpoint, params, secret):
    parameter_str = ""

    if params:
        parameter_str += "{}".format(urlencode(params, safe=settings.SAFE_QUOTE_SYMBOLS))

    sha_1 = hashlib.sha1()
    sha_1.update("{}{}{}".format(endpoint, parameter_str, secret).encode())

    if params:
        return "{}?{}&checksum={}".format(endpoint, parameter_str, sha_1.hexdigest())
    else:
        return "{}?checksum={}".format(endpoint, sha_1.hexdigest())


def get_forwarded_host(request):
    forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST', request.META.get('HTTP_HOST'))
    return forwarded_host_regex.sub(r'\1', forwarded_host)


@sync_to_async
def get_node_by_meeting_id(meeting_id, secret):
    if meeting_id is None:
        return None
    try:
        meeting = Meeting.objects.get(id=meeting_id, secret=secret)
        if meeting.node.has_errors:
            return None
        else:
            return meeting.node
    except ObjectDoesNotExist:
        return None


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


def get_slide_body_for_post(slide):
    slide_path = "rest/slides/{}".format(slide)
    try:
        slide_file = open(slide_path, "rb")
        body = '<modules><module name="presentation"><document name="{}">{}</document></module></modules>'.format(slide, base64.b64encode(slide_file.read()).decode())
        slide_file.close()
    except FileNotFoundError:
        body = None
    return body


def incr_metric(name, secret, node, incr=1):
    metric, created = Metric.objects.get_or_create(name=name, secret=secret, node=node)
    metric.value = (F("value") + incr) % settings.METRIC_BIGINT_MODULO
    metric.save(update_fields=["value"])


@sync_to_async
def limit_check(secret):
    if secret.tenant.meeting_limit > 0 and not Meeting.objects.filter(secret__tenant=secret.tenant).count() < secret.tenant.meeting_limit:
        return False

    if secret.meeting_limit > 0 and not Meeting.objects.filter(secret=secret).count() < secret.meeting_limit:
        return False

    if secret.tenant.attendee_limit > 0:
        attendee_sum = Meeting.objects.filter(secret__tenant=secret.tenant).aggregate(Sum('attendees'))["attendees__sum"]
        # Aggregation sum can return None or [0, inf).
        # Only check for limit if aggregation sum is an integer.
        if isinstance(attendee_sum, int) and not attendee_sum < secret.tenant.attendee_limit:
            return False

    if secret.attendee_limit > 0:
        attendee_sum = Meeting.objects.filter(secret=secret).aggregate(Sum('attendees'))["attendees__sum"]
        # Same as above
        if isinstance(attendee_sum, int) and not attendee_sum < secret.attendee_limit:
            return False
    return True


def parse_endpoint(forwarded_host, get_secret=False):
    regex_search = slug_regex.search(forwarded_host)
    if regex_search:
        try:
            if get_secret:
                return Secret.objects.select_related("tenant", "tenant__slide").get(tenant__slug=regex_search.group(1).upper(), sub_id=int(regex_search.group(3) or 0))
            else:
                return Tenant.objects.get(slug=regex_search.group(1).upper())
        except ObjectDoesNotExist:
            return None
    else:
        return None


def set_metric(name, secret, node, value):
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


def xml_escape(string):
    if isinstance(string, str):
        escape_symbols = [
            ("&", "&amp;"),
            ("<", "&lt;"),
            (">", "&gt;"),
            ("'", "&apos;"),
            ('"', "&quot;")
        ]
        for symbol, escape in escape_symbols:
            string = string.replace(symbol, escape)
        return string
    else:
        return ""
