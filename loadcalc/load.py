#!/usr/bin/env python3

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

from time import sleep
import os

LONG_TERM_ITERATIONS = 6
INTERVAL_LENGTH = 10

last_idle = 0
last_total = 0
idle_deltas = [0] * LONG_TERM_ITERATIONS
total_deltas = [1] * LONG_TERM_ITERATIONS
index = 0

if not os.path.isdir('/run/b3lb'):
    os.mkdir('/run/b3lb')

while True:
    with open('/proc/stat') as f:
        fields = [float(column) for column in f.readline().strip().split()[1:]]

    idle = fields[3]
    total = sum(fields[:8])

    idle_deltas[index] = idle - last_idle
    total_deltas[index] = total - last_total
    last_idle = idle
    last_total = total

    utilisation_short = int(10000 * (1.0 - idle_deltas[index] / total_deltas[index]))
    utilisation_long = int(10000 * (1.0 - sum(idle_deltas) / sum(total_deltas)))

    utilisation = max(utilisation_long, utilisation_short)

    with open('/run/b3lb/load.new', 'w') as f:
        f.write('{}\n'.format(utilisation))
    os.replace('/run/b3lb/load.new', '/run/b3lb/load')

    index = (index + 1) % LONG_TERM_ITERATIONS
    sleep(INTERVAL_LENGTH)
