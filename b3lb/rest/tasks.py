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
from loadbalancer.celery import app
from rest.celery.b3lb import celery_run_check_node, celery_update_get_meetings_xml
from rest.celery.housekeeping import celery_cleanup_assets
from rest.celery.records import celery_render_records
from rest.celery.statistics import celery_statistic_fill_by_tenant, celery_update_metrics
from rest.models import Node, Tenant, Secret, RecordSet

logger = get_task_logger(__name__)


@app.task(ignore_result=True, base=Singleton, queue='node')
def check_node(node_uuid):
    return celery_run_check_node(node_uuid)


@app.task(ignore_result=True, base=Singleton, name="Check Node Status", queue='node')
def check_status():
    for node in Node.objects.all():
        check_node.si(str(node.uuid)).apply_async()
    return True


@app.task(ignore_result=True, base=Singleton, name="Cleanup Assets", queue='cleanup')
def cleanup_assets():
    return celery_cleanup_assets()


@app.task(ignore_result=True, base=Singleton, name="Render not rendered Record Sets", queue='recording')
def render_record_sets():
    for record_set in RecordSet.objects.filter(status=RecordSet.UPLOADED):
        celery_render_records(record_set)
    return True


@app.task(ignore_result=True, base=Singleton, queue='secret')
def update_secret_meetings_lists(secret_uuid):
    return celery_update_get_meetings_xml(secret_uuid)


@app.task(ignore_result=True, base=Singleton, queue='secret')
def update_secret_metrics_list(secret_uuid):
    return celery_update_metrics(secret_uuid)


@app.task(ignore_result=True, base=Singleton, name="Update Secrets List", queue='secret')
def update_secrets_lists():
    update_secret_metrics_list.si(None).apply_async()
    for secret in Secret.objects.all():
        update_secret_meetings_lists.si(str(secret.uuid)).apply_async()
        update_secret_metrics_list.si(str(secret.uuid)).apply_async()
    return True


@app.task(ignore_result=True, base=Singleton, name="Update Statistics", queue='statistic')
def update_statistic():
    for tenant in Tenant.objects.all():
        update_tenant_statistic.si(str(tenant.uuid)).apply_async()
    return True


@app.task(ignore_result=True, base=Singleton, name="Update Tenant Statistics", queue='statistic')
def update_tenant_statistic(tenant_uuid):
    return celery_statistic_fill_by_tenant(tenant_uuid)
