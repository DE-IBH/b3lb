# ChangeLog

## 2.2.5 - 2022-08-09

Changes:
- adopt new BBB 2.5 API features
  - add insertDocument API call
  - add meta_fullaudio-bridge API parameter
- bump python dependencies:
  - celery `5.2.6` => `5.2.7`
  - Django `3.2.13` => `3.2.15`
  - jinja2 `3.1.1` => `3.1.2`
  - Pillow `9.1.0`=>  `9.2.0`
  - uvicorn `0.17.6`=>  `0.18.2`
  - requests `2.27.1` => `2.28.1`

## 2.2.4 - 2022-04-12

Fixes:
- stats: fix regex for retrieving secret for metrics and stats url (#85)

Changes:
- bump python dependencies:
  - celery `5.2.3` => `5.2.6`
  - Django `3.2.12` => `3.2.13`
  - jinja2 `3.0.3` => `3.1.1`
  - Pillow `9.0.1`=>  `9.1.0`
  - uvicorn `0.17.5`=>  `0.17.6`

## 2.2.3 - 2022-03-04

Changes:
- admin: add filters, links and search
- bump python dependencies:
  - Django `3.2.10` => `3.2.12`
  - Pillow `8.4.0`=>  `9.0.1`
  - requests `2.26.0` => `2.27.1`
  - uvicorn `0.16.0`=>  `0.17.5`

## 2.2.2 - 2021-12-29

Fixes:
- api: change checksum validation to match upstream implementation (#54)

Changes:
- api: support overriding more (new) BBB 2.4 [parameters](https://docs.bigbluebutton.org/dev/api.html#api-calls) (#58)
  - `excludeFromDashboard`
  - `learningDashboardCleanupDelayInMinutes`
  - `learningDashboardEnabled`
  - `meetingLayout`
  - `moderatorOnlyMessage`
  - `role`
  - `welcome`
- bump python dependencies:
  - Django `3.2.7` => `3.2.10` (CVE-2021-44420)
  - django-environ `0.5.0` => `0.8.1`
  - django-redis `5.0.0`=>  `5.2.0`
  - uvicorn `0.15.0`=>  `0.16.0`
  - aiohttp `3.7.4`=>  `3.8.1`
- docker: bump to alpine 3.15


## 2.2.1 - 2021-09-01

Fixes:
- api: fix internal server error if end meeting is called for a non-existing meeting

Changes:
- bump python dependencies:
  - Django `3.2.5` => `3.2.7`
  - django-environ `0.4.5` => `0.5.0`
  - django-split-settings `1.0.1`=>  `1.1.0`
  - uvicorn `0.14.0`=>  `0.15.0`
- docker: bump to alpine 3.14.2

## 2.2.0 - 2021-07-27

Fixes:
- api: failed to join meetings for tenants without Asset object #45
- api: do not add custom_style_url parameters if no AssetCss is set #46

Changes:
- django: add settings for email based error notification

## 2.1.0 - 2021-07-26

Changes:
- admin: add admin command for cluster maintenance
- api: add [html5 custom parameters](https://docs.bigbluebutton.org/admin/customize.html#passing-custom-parameters-to-the-client-on-join) support
- api: add custom css asset
- bump python dependencies:
  - Django `3.2.2` => `3.2.5`
  - celery `5.0.5` => `5.1.2`
  - django-redis `4.12.1` => `5.0.0`
  - uvicorn `0.13.4`=>  `0.14.0`
- docker: bump to alpine 3.14, python3.9, pypy 3.7-7.3.5

## 2.0.1 - 2021-05-09

Changes:
- bump python dependencies for Python 3.9 compatibility and fix
  [CVE-2021-32052](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-32052) on Python 3.9.5+:
  - Django `3.2` => `3.2.2`
  - django-extensions `3.1.2` => `3.1.3`
  - django-cacheops `5.1` => `6.0`

The published docker images were shipped with Python 3.8
from Alpine Linux 3.13 and should not be affected by
[CVE-2021-32052](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-32052).

## 2.0.0 - 2021-04-16

This is a new major release with breaking changes:
- custom *settings.py* should be replaced by environment settings or
  an `.env` settings file (check for changed settings names)
- assets are now served from the database using blobs, you need to upload
  your file based logo and slide assets manually
- fixtures have been updated to replace the `checkslides` task by `cleanup_assets`

Changes:
- assets: handle logos and slides by database blobs #16
- api: add support for single domain name usage #23
- docker: use explicit tagged base images and disable pip's caching #29
- parameters: allow to block, set or override most parameters of BBB API create
- pypy: provide **highly experimental** docker image variant based on pypy,
        switch from *psycopq2* to *psycopq2cffi* to be pypy compatible
        (increases worker performance) #22
- settings: allow configuration via environment using django-environ #12
- settings: refactor custom settings with B3LB_ prefix #11

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
