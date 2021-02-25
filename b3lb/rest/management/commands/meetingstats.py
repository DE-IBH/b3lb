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
from rest.models import Meeting, Tenant
import json


class Command(BaseCommand):
    help = 'Get status information of tenant and meetings'

    def handle(self, *args, **options):
        mci_list = {"meetings": 0, "attendees": 0}
        for record in Tenant.objects.all():
            if record.slug not in mci_list:
                mci_list[record.slug] = {"meetings": 0, "attendees": 0}

        for record in Meeting.objects.all():
            mci_list[record.secret.tenant.slug]["meetings"] += 1
            mci_list[record.secret.tenant.slug]["attendees"] += record.attendees
            mci_list["meetings"] += 1
            mci_list["attendees"] += record.attendees

        self.stdout.write(json.dumps(mci_list))
