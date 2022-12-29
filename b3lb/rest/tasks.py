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
import rest.b3lb.tasks as b3lbtasks
from rest.models import Node, RecordSet, Secret, Tenant, SecretRecordProfileRelation

logger = get_task_logger(__name__)


@app.task(ignore_result=True, base=Singleton, queue="b3lb")
def check_node(node_uuid):
    return b3lbtasks.run_check_node(node_uuid)


@app.task(ignore_result=True, base=Singleton, queue="b3lb")
def update_secret_meetings_lists(secret_uuid):
    return b3lbtasks.update_get_meetings_xml(secret_uuid)


@app.task(ignore_result=True, base=Singleton, queue="b3lb")
def update_secret_metrics_list(secret_uuid):
    return b3lbtasks.update_metrics(secret_uuid)


@app.task(name="Update Secrets Lists", ignore_result=True, base=Singleton, queue="b3lb")
def update_secrets_lists():
    update_secret_metrics_list.si(None).apply_async()
    for secret in Secret.objects.all():
        update_secret_meetings_lists.si(str(secret.uuid)).apply_async()
        update_secret_metrics_list.si(str(secret.uuid)).apply_async()
    return True


@app.task(name="Check Status of Nodes", ignore_result=True, base=Singleton, queue="b3lb")
def check_status():
    for node in Node.objects.all():
        check_node.si(str(node.uuid)).apply_async(queue="b3lb")
    return True


@app.task(ignore_result=True, base=Singleton, queue="b3lb")
def update_tenant_statistic(tenant_uuid):
    return b3lbtasks.fill_statistic_by_tenant(tenant_uuid)


@app.task(name="Update Statistics", ignore_result=True, base=Singleton, queue="b3lb")
def update_statistic():
    for tenant in Tenant.objects.all():
        update_tenant_statistic.si(str(tenant.uuid)).apply_async(queue="b3lb")
    return True


@app.task(name="Render non-rendered Records", ignore_result=True, base=Singleton, queue=settings.B3LB_RECORD_TASK_DEFAULT_QUEUE)
def render_record():
    """
    Async starting of rendering tasks.
    """
    for record_set in RecordSet.objects.filter(status=RecordSet.UPLOADED):
        secret_record_profile_relations = SecretRecordProfileRelation.objects.filter(secret=record_set.secret)
        for secret_record_profile_relation in secret_record_profile_relations:
            b3lbtasks.render_record(secret_record_profile_relation.record_profile.uuid, record_set.uuid)
