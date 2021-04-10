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
from django.core.exceptions import ObjectDoesNotExist
from rest.models import Meeting, Metric, Node, ClusterGroupRelation, Secret, Tenant, Parameter
from urllib.parse import urlencode
from random import randint
import re
from django.db import transaction
from django.db.models import F, Sum
import hashlib
from django.conf import settings
import rest.b3lb.utils as utils


##
# CONSTANTS
##
slug_regex = re.compile(r'([a-z]{2,10})(-(\d{3}))?\.' + re.escape(settings.B3LP_API_BASE_DOMAIN) + '$')

# symbols not to be encoded to match bbb's checksum calculation
SAFE_QUOTE_SYMBOLS = '*'

# wrap metric counters
METRIC_BIGINT_MODULO = 9223372036854775808

##
# Routines
##
@sync_to_async
def check_meeting_existence(meeting_id, secret):
    if meeting_id is None:
        return get_node_params_by_lowest_workload(secret.tenant.cluster_group), True

    with transaction.atomic():
        try:
            meeting = Meeting.objects.get(id=meeting_id, secret=secret)
            return meeting.node, False
        except ObjectDoesNotExist:
            return get_node_params_by_lowest_workload(secret.tenant.cluster_group), True


def check_parameter(params, tenant):
    parameters = Parameter.objects.filter(tenant=tenant)

    for parameter in parameters:
        if parameter.parameter in params:
            if parameter.mode == Parameter.BLOCK:
                del params[parameter.parameter]
            elif parameter.mode == Parameter.OVERRIDE:
                params[parameter.parameter] = parameter.value
        elif parameter.mode in [Parameter.SET, Parameter.OVERRIDE]:
            params[parameter.parameter] = parameter.value

    return params


def check_tenant(secret, checksum, endpoint, params):
    if secret:
        sha_1 = hashlib.sha1()
        parameter_str = ""

        if params:
            parameter_str = urlencode(params, safe=SAFE_QUOTE_SYMBOLS)

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
        parameter_str = urlencode(params, safe=SAFE_QUOTE_SYMBOLS)

    sha_1 = hashlib.sha1()
    sha_1.update("{}{}{}".format(endpoint, parameter_str, secret).encode())

    if params:
        return "{}?{}&checksum={}".format(endpoint, parameter_str, sha_1.hexdigest())
    else:
        return "{}?checksum={}".format(endpoint, sha_1.hexdigest())


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


def get_request_tenant(request, slug, sub_id):
    (slug, sub_id) = get_slug(request, slug, sub_id)
    if not slug:
        return None

    try:
        return Tenant.objects.get(slug=slug)
    except ObjectDoesNotExist:
        return None


def get_request_secret(request, slug, sub_id):
    (slug, sub_id) = get_slug(request, slug, sub_id)
    if not slug:
        return None

    try:
        return Secret.objects.select_related("tenant", "tenant__slide").get(tenant__slug=slug, sub_id=sub_id)
    except ObjectDoesNotExist:
        return None


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
