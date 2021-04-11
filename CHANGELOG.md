# ChangeLog

## 2.0.0 - 2021-04-XX

This is a new major release with breaking changes:
- custom *settings.py* should be replaced by environment settings
  (lookout for changed names)
- assets are now served from the database using blobs, you need to upload
  your file based assets manually
- fixtures have been updated to replace the `checkslides` task by `cleanup_assets`

Changes:
- assets: handle logos and slides by database blobs #16
- api: add support for single domain name usage #23
- docker: use explicit tagged base images and disable pip's caching #29
- parameters: allow to block, set or override most parameters of BBB API create
- pypy: provide **experimental** docker image variant based on pypy,
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
