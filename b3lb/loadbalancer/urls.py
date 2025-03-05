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
from rest import views

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^bigbluebutton/api/(?P<endpoint>[0-9.a-zA-Z]*)$', views.bbb_entrypoint),
    path('b3lb/stats', views.stats),
    path('b3lb/metrics', views.metrics),
    path('b3lb/ping', views.ping),
    re_path(r'^b3lb/b/(?P<backend>[a-z]+)/(?P<endpoint>[a-z]+)$', views.backend_endpoint),
    re_path(r'^b3lb/r/(?P<nonce>[a-zA-Z0-9!@*(_)-]+)$', views.recording),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/bbb/api/(?P<endpoint>[0-9.a-zA-Z]*)$', views.bbb_entrypoint),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/stats', views.stats),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/metrics', views.metrics),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})/logo', views.logo),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})/slide', views.slide),
    re_path(r'^b3lb/t/(?P<slug>[a-z]{2,10})/css', views.custom_css),
    # necessary for db-file-storage extension!
    re_path(r'^files/', include('db_file_storage.urls'))
]
