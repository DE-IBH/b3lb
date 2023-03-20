# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2023 IBH IT-Service GmbH
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


from celery_singleton import Singleton
from django.conf import settings
from loadbalancer.celery import app
from rest.classes.checks import NodeCheck
from rest.task.core import check_node, generate_secret_get_meetings
from rest.task.statistics import update_secret_metrics, update_tenant_statistics
from rest.models import Node, RecordSet, Secret

##
# cast following tasks multiple times asynchronous
##

@app.task(ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_CORE)
def core_check_node(node_uuid: str):
    return check_node(NodeCheck(Node.objects.get(uuid=node_uuid)))


@app.task(ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_CORE)
def core_generate_secret_meetings(secret_uuid: str):
    return generate_secret_get_meetings(Secret.objects.get(uuid=secret_uuid))


if settings.B3LB_RENDERING:
    from rest.task.recording import render_record
    @app.task(ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_RECORD)
    def recording_render_record(record_set_uuid: str):
        return render_record(RecordSet.objects.get(uuid=record_set_uuid))


@app.task(ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_STATISTICS)
def statistic_update_secret_metrics(secret_uuid: str):
    return update_secret_metrics(secret_uuid)


@app.task(ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_STATISTICS)
def statistics_update_tenant_statistics(tenant_uuid: str):
    return update_tenant_statistics(tenant_uuid)
