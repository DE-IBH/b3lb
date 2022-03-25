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


from django.contrib import admin
from rest.models import *


admin.site.register(Asset, AssetAdmin)
admin.site.register(AssetCustomCSS, AssetCustomCSSAdmin)
admin.site.register(AssetLogo, AssetLogoAdmin)
admin.site.register(AssetSlide, AssetSlideAdmin)
admin.site.register(Cluster, ClusterAdmin)
admin.site.register(ClusterGroup, ClusterGroupAdmin)
admin.site.register(ClusterGroupRelation, ClusterGroupRelationAdmin)
admin.site.register(Meeting, MeetingAdmin)
admin.site.register(Metric, MetricAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(NodeMeetingList, NodeMeetingListAdmin)
admin.site.register(Parameter, ParameterAdmin)
admin.site.register(Record, RecordAdmin)
admin.site.register(RecordProfile, RecordProfileAdmin)
admin.site.register(RecordSet, RecordSetAdmin)
admin.site.register(Secret, SecretAdmin)
admin.site.register(SecretMeetingList, SecretMeetingListAdmin)
admin.site.register(SecretMetricsList, SecretMetricsListAdmin)
admin.site.register(Stats, StatsAdmin)
admin.site.register(Tenant, TenantAdmin)
