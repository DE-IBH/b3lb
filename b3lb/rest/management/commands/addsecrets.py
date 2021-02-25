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
from rest.models import Tenant, Secret
from django.core.exceptions import ObjectDoesNotExist
import re
import json


class Command(BaseCommand):
    help = 'Add new tenant secret(s).'

    def add_arguments(self, parser):
        parser.add_argument('--tenant-slug', action='store', help='Slug', required=True)
        parser.add_argument('--sub-id', action='store', help='Ids from N-M or single id, with 0 <= N, M < 1000', required=True)

    def handle(self, *args, **options):
        slug = options['tenant_slug']
        sub_id_string = options['sub_id']
        result = {}

        sub_id_search = re.search(r'^(\d+?)[-](\d+?)$', sub_id_string)
        if sub_id_search:
            lower_sub_id = int(sub_id_search.group(1))
            higher_sub_id = int(sub_id_search.group(2))
            if lower_sub_id < 1000 and higher_sub_id < 1000:
                sub_ids = range(min(lower_sub_id, higher_sub_id), max(lower_sub_id, higher_sub_id) + 1)
            elif lower_sub_id >= 1000 and higher_sub_id >= 1000:
                return "No sub_id's over 999 possible!"
            else:
                sub_ids = range(min(lower_sub_id, higher_sub_id), 1000)
        else:
            sub_id_search = re.search(r'^(\d+?)$', sub_id_string)
            if sub_id_search:
                sub_ids = [int(sub_id_search.group(1))]
                if sub_ids[0] > 999:
                    return "No sub_id's over 999 possible!"
            else:
                return "Please use correct format for --sub-id!"

        try:
            tenant = Tenant.objects.get(slug=slug)
        except ObjectDoesNotExist:
            return "Tenant with Slug {} doesn't exists!".format(slug)

        for sub_id in sub_ids:
            try:
                secret = Secret.objects.get(tenant=tenant, sub_id=sub_id)
            except ObjectDoesNotExist:
                secret = Secret(tenant=tenant, sub_id=sub_id)
                secret.save()
                result[secret.__str__()] = secret.secret

        return json.dumps(result)
