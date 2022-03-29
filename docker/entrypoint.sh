#!/bin/sh

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


CMD="$1"
shift

case "$CMD" in
    addnode)
        exec /usr/bin/env python3 ./manage.py addnode $@
        ;;
    celery-beat)
        exec celery -A loadbalancer beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    celery-tasks)
        exec celery -A loadbalancer worker $@ -l info
        ;;
    loadbalancer)
        /usr/bin/env python3 ./manage.py migrate --no-input --force-color
        exec /usr/bin/env python3 ./manage.py $@
        ;;
    gunicorn)
        /usr/bin/env python3 ./manage.py migrate --no-input --force-color
        exec gunicorn $@ loadbalancer.wsgi:application
        ;;
    uvicorn)
        /usr/bin/env python3 ./manage.py migrate --no-input --force-color
        exec uvicorn $@ loadbalancer.asgi:application
        ;;
    meetingstats)
        exec /usr/bin/env python3 ./manage.py meetingstats
        ;;
    getloadvalues)
        exec /usr/bin/env python3 ./manage.py getloadvalues
        ;;
    gettenantsecrets)
        exec /usr/bin/env python3 ./manage.py gettenantsecrets
        ;;
    listalltenantsecrets)
        exec /usr/bin/env python3 ./manage.py listalltenantsecrets
        ;;
    addsecrets)
        exec /usr/bin/env python3 ./manage.py addsecrets $@
        ;;
    static)
        cd static && exec /usr/bin/env python3 -m http.server 8001
        ;;
    *)
        echo "Unknown command '$CMD'!" 1>&2
        exit 1
        ;;
esac
