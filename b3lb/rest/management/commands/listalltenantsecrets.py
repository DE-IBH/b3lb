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
from rest.models import Secret, Tenant


class Command(BaseCommand):
    help = 'List all secrets of all tenants'

    def handle(self, *args, **options):
        output = "{} | {}\n".format("Endpoint".ljust(32), "Secret".ljust(42))
        output += "{}\n".format("".ljust(78, "="))
        add_hline = False
        for tenant in Tenant.objects.all():
            if add_hline:
                output += "{}+{}\n".format("".ljust(33, "-"), "".ljust(43, "-"))
            else:
                add_hline = True

            for secret in Secret.objects.filter(tenant=tenant):
                output += "{} | {}\n".format(secret.endpoint.ljust(32), secret.secret.ljust(42))

        self.stdout.write(output)
