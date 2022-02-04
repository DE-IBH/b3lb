FROM python:3.9-bullseye

ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

RUN mkdir -p /usr/src/app/outdir /usr/src/app/indir
COPY LICENSE ./
RUN apt-get update && \
    apt-get install -y python3-gi gir1.2-ges-1.0 ges1.0-tools python3-intervaltree gstreamer1.0-libav gstreamer1.0-plugins-*

COPY ../../../BBB/b3lb/bbb-render/entrypoint.sh ./
COPY dot.png ./
COPY plug ./plug
COPY make-xges.py ./


ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
