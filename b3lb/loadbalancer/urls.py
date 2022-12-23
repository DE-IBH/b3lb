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
from django.urls import path, include
from django.conf.urls import url
from rest import views

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^bigbluebutton/api/(?P<endpoint>[0-9.a-zA-Z]*)$', views.bbb_entrypoint),
    path('b3lb/stats', views.stats),
    path('b3lb/metrics', views.metrics),
    path('b3lb/ping', views.ping),
    path('b3lb/b/meeting/end', views.backend_end_meeting_callback),
    path('b3lb/b/record/upload', views.backend_record_upload),
    url(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/bbb/api/(?P<endpoint>[0-9.a-zA-Z]*)$', views.bbb_entrypoint),
    url(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/stats', views.stats),
    url(r'^b3lb/t/(?P<slug>[a-z]{2,10})(-(?P<sub_id>\d{3}))?/metrics', views.metrics),
    url(r'^b3lb/t/(?P<slug>[a-z]{2,10})/logo', views.logo),
    url(r'^b3lb/t/(?P<slug>[a-z]{2,10})/slide', views.slide),
    url(r'^b3lb/t/(?P<slug>[a-z]{2,10})/css', views.custom_css),
    # necessary for db-file-storage extension!
    url(r'^files/', include('db_file_storage.urls'))
]
