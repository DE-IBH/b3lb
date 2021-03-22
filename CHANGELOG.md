# ChangeLog

## 1.2.0 - 2021-03-23

Fixes:
- github: build docker images on release #20

Changes:
- metrics: prevent high DB load due to a high number of transactions #19
- celery: use *celery-singleton* to prevent task backlogs due to high load #18

## 1.1.0 - 2021-03-09

Changes:
- metrics: add limit metrics for tenants and secrets #10
- models: attendee and meeting limits for tenants and secrets #10
- models: make default value of Node's domain configurable #6
- docker: add github action to build docker images
- scripts: add b3lb-cleaner auxiliary script #8

## 1.0.1 - 2021-02-26

Fixes:
- metrics: fix meetings gauge #1
- metrics: fix gauge type hint #1
- aiohttp: bump to 3.7.4 #2

## 1.0.0 - 2021-02-25

Initial release.
