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


from django.core.management.base import BaseCommand
from rest.models import Secret
import json


class Command(BaseCommand):
    help = 'Get first secret and hostnames of tenants.'

    def handle(self, *args, **options):
        tenant_dict = {}

        for secret in Secret.objects.filter(sub_id=0):
            tenant_dict[secret.tenant.slug] = {"secret": secret.secret, "hostname": secret.endpoint}

        self.stdout.write(json.dumps(tenant_dict))
