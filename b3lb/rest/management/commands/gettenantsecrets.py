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
    help = 'Get secrets, endpoints and if recording is enabled.'

    def handle(self, *args, **options):
        tenant_dict = {}

        for secret in Secret.objects.all():
            tenant_dict["{}-{}".format(secret.tenant.slug, str(secret.sub_id).zfill(3))] = {"secret": secret.secret, "hostname": secret.endpoint, "recording": secret.is_record_enabled}

        self.stdout.write(json.dumps(tenant_dict))
