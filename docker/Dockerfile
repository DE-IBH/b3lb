# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2025 IBH IT-Service GmbH
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


FROM python:3.12-slim AS build

RUN apt-get update && \
    apt-get install -y libpq-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

COPY requirements ./
RUN pip3 install --no-cache-dir --prefix=/usr/local -r requirements.txt -r requirements_extra.txt


FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y libpq5 && \
    rm -rf /var/lib/apt/lists/*

ARG B3LBUID=8318
ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

COPY --from=build /usr/local /usr/local

COPY b3lb ./

RUN addgroup --gid $B3LBUID b3lb && \
    adduser --uid $B3LBUID --gid $B3LBUID --home /usr/src/app --disabled-password --no-create-home --system b3lb && \
    ENV_FILE=.env.dev ./manage.py check --force-color && \
    ENV_FILE=.env.dev ./manage.py collectstatic --no-input --force-color

USER b3lb:b3lb
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
CMD ["uvicorn", "--host", "0.0.0.0", "--ws", "none", "--use-colors"]
