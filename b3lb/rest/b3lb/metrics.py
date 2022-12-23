# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2022 IBH IT-Service GmbH
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

from rest.models import Metric, Node, Secret
from django.db.models import F


METRIC_BIGINT_MODULO = 9223372036854775808

def del_metric(name, secret, node):
    Metric.objects.filter(name=name, secret=secret, node=node).delete()


def incr_metric(name: str, secret: Secret, node: Node, incr: int = 1):
    if Metric.objects.filter(name=name, secret=secret, node=node).update(value=(F("value") + incr) % METRIC_BIGINT_MODULO) == 0:
        Metric.objects.update_or_create(name=name, secret=secret, node=node, defaults={"value": (F("value") + incr) % METRIC_BIGINT_MODULO})


def set_metric(name, secret, node, value):
    if Metric.objects.filter(name=name, secret=secret, node=node).update(value=value) == 0:
        metric, created = Metric.objects.get_or_create(name=name, secret=secret, node=node)
        metric.value = value
        metric.save(update_fields=["value"])


def update_create_metrics(secret, node):
    # add penalty points for a new meeting on the node
    node = Node.objects.get(uuid=node.uuid)
    node.attendees = F("attendees") + 1
    node.meetings = F("meetings") + 1
    node.save(update_fields=["attendees", "meetings"])

    # update metric stats
    incr_metric(Metric.CREATED, secret, node)
