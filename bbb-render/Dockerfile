FROM python:3.10-slim-bullseye

ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

RUN mkdir out in
RUN apt-get update && \
    apt-get install -y python3-gi gir1.2-ges-1.0 ges1.0-tools python3-intervaltree gstreamer1.0-libav gstreamer1.0-plugins-*

COPY bbb-render/dot.png ./
COPY bbb-render/plug ./plug
COPY bbb-render/make-xges.py ./
COPY entrypoint.sh ./

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
