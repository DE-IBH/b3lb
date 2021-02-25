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
from rest.models import Node
import json


class Command(BaseCommand):
    help = 'Get calculated load values of nodes'

    def handle(self, *args, **options):
        load_list = {}
        for record in Node.objects.all():
            if record.slug not in load_list:
                load_list["{}.{}".format(record.slug, record.domain)] = [record.load, record.cpu_load]

        self.stdout.write(json.dumps(load_list))
