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


from celery.utils.log import get_task_logger
from celery_singleton import Singleton
from django.conf import settings
from loadbalancer.celery import app
from rest.models import Node, RecordSet, Secret, Tenant
import rest.task.b3lb as b3lbtask


logger = get_task_logger(__name__)


@app.task(name="Update Secrets Lists", ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_CORE)
def update_secrets_lists():
    """
    Async starting of secret list update tasks.
    """
    b3lbtask.statistic_update_secret_metrics.si("").apply_async()
    for secret in Secret.objects.all():
        b3lbtask.statistic_update_secret_metrics.si(str(secret.uuid)).apply_async(queue=settings.B3LB_TASK_QUEUE_STATISTICS)
        b3lbtask.core_generate_secret_meetings.si(str(secret.uuid)).apply_async(queue=settings.B3LB_TASK_QUEUE_CORE)
    return True


@app.task(name="Check Status of Nodes", ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_CORE)
def check_status():
    """
    Async starting of node check tasks.
    """
    for node in Node.objects.all():
        b3lbtask.core_check_node.si(str(node.uuid)).apply_async(queue=settings.B3LB_TASK_QUEUE_CORE)
    return True


@app.task(name="Update Statistics", ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_STATISTICS)
def update_statistic():
    """
    Async starting of tenant statistic update.
    """
    for tenant in Tenant.objects.all():
        b3lbtask.statistics_update_tenant_statistics.si(str(tenant.uuid)).apply_async(queue=settings.B3LB_TASK_QUEUE_STATISTICS)
    return True

@app.task(name="Render Records from RecordSets", ignore_result=True, base=Singleton, queue=settings.B3LB_TASK_QUEUE_RECORD)
def render_record():
    """
    Async starting of rendering tasks.
    """
    for record_set in RecordSet.objects.filter(status=RecordSet.UPLOADED):
        b3lbtask.recording_render_record.si(str(record_set.uuid)).apply_async(queue=settings.B3LB_TASK_QUEUE_RECORD)
