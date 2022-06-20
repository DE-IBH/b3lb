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
from django.urls import path, include, re_path
from rest.views import api_pass_through, stats, ping, metrics, slide, logo, custom_css

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^bigbluebutton/api/(?P<endpoint>[0-9.a-zA-Z]*)$', api_pass_through),
    path('b3lb/stats', stats),
    path('b3lb/metrics', metrics),
    path('b3lb/ping', ping),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/bbb/api/(?P<endpoint>[0-9.a-zA-Z]*)$', api_pass_through),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/stats', stats),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/metrics', metrics),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})/logo', logo),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})/slide', slide),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})/css', custom_css),
    # necessary for db-file-storage extension!
    re_path(r'^files/', include('db_file_storage.urls'))
]
