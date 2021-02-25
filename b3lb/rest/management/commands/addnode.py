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
from rest.models import Node, Cluster
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
    help = 'Add new BBB cluster node.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', action='store', help='hostname', required=True)
        parser.add_argument('--secret', action='store', help='BBB API secret', required=True)
        parser.add_argument('--cluster', action='store', help='cluster name', required=True)

    def handle(self, *args, **options):
        slug = options['slug']
        secret = options['secret']
        cluster = options['cluster']
        try:
            node = Node.objects.get(slug=slug)
            return "Node {} already exists".format(slug)
        except ObjectDoesNotExist:
            try:
                cluster_object = Cluster.objects.get(name=cluster)
            except ObjectDoesNotExist:
                return "Cluster {} doesn't exists".format(cluster)

            try:
                node = Node(slug=slug, secret=secret, cluster=cluster_object)
                node.maintenance = True
                node.save()
                return "Node {} added".format(slug)
            except:
                return "Error during add Node to database"
