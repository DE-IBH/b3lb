# ChangeLog

## 3.3.2 - 2025-06-11

Fixes:
- storing of logos, slides and custom css files in database instead of the filesystem
- use PyObject `3.50.0` instead of `3.52.3` for debian 12 based build

## 3.3.1 - 2025-06-08

Changes:
- bumped python dependencies:
  - Django: `5.2.1` => `5.2.2`

## 3.3.0 - 2025-06-08

Changes:
- add new BBB 3.0 API parameters
  - sendChatMessage
  - allowOverrideClientSettingsOnCreateCall
  - loginURL
  - pluginManifests
  - pluginManifestsFetchUrl
  - presentationConversionCacheEnabled
  - maxNumPages
  - bot
  - enforceLayout
  - logoutURL
  - firstName
  - lastName
  - userdata-bbb_default_layout,
  - userdata-bbb_skip_echotest_if_previous_device
  - userdata-bbb_prefer_dark_theme
  - userdata-bbb_hide_notifications,
  - userdata-bbb_hide_controls
- removed deprecated API parameters
  - breakoutRoomsEnabled
  - learningDashboardEnabled
  - virtualBackgroundsDisabled
  - defaultLayout
- bumped python dependencies:
  - Django: `3.2.25` => `5.2.1`
  - PyGObject: `3.48.2` => `3.52.3`
  - aiohttp: `3.9.5` => `3.12.7`
  - boto3: `1.34.106` => `1.38.28`
  - celery: `5.3.4` => `5.5.3`
  - django-cacheops: `7.0.2` => `7.2`
  - django-celery-beat: `2.6.0` => `2.8.0`
  - django-celery-results: `2.5.1` => `2.6.0`
  - django-environ: `0.11.2` => `0.12.0`
  - django-extensions: `3.2.3` => `4.1`
  - django-storages: `1.14.3` => `1.14.6`
  - pyjwt: `2.8.0` => `2.10.1`
  - psycopg2cffi: `2.9.0` => psycopg: `3.2.6`
  - requests: `2.31.0` = `2.32.3`
  - uvicorn[standard]: `0.29.0` => `0.34.3`
  - xmltodict: `0.13.0` => `0.14.2`

With b3lb 3.3 the minimal support for PostgreSQL is now version 14, which is required by `psycopg`.

## 3.2.6 - 2024-08-21

Changes:
- add new BBB 2.7 API parameters
  - allowPromoteGuestToModerator
  - webcamBackgroundURL

## 3.2.5 - 2024-07-03

Fixes:
- missing check for no clips during rendering task 

## 3.2.4 - 2024-06-16

Fixes:
- fix **security** bug in getRecordings endpoint

This release fixes a security bug that allowed authenticated api requests to manage recordings of any tenants and their secrets.

## 3.2.3 - 2024-05-28

Fixes:
- add possibility to use the same meeting ID for two different secrets.
- return an error message if meeting id is out of range (2 <= id_length <= 100 chars)


## 3.2.2 - 2024-05-23

Fixes:
- fix missing specific POST Header when an asset is sent

## 3.2.1 - 2024-05-21

Changes:
- adjust to BBB 2.7.8 API changes 
  - forbid POST request for `join` endpoint
  - adjustments for POST headers are already handled
- meeting name check:
  - add check for meeting name length for faster response without sending a request to backend systems
  - meeting name length must be between 2 and 256 characters as given by BBB API restrictions

## 3.2.0 - 2024-05-16

Changes:
- add new BBB 2.6 API parameters
  - preUploadedPresentation
  - preUploadedPresentationName
  - errorRedirectUrl
  - userdata-bbb_fullaudio_bridge
- refactor Parameter model
- added python dependencies:
  - pyjwt: `2.8.0`
- bumped python dependencies:
  - Django: `3.2.19` => `3.2.25`
  - PyGObject: `3.44.1` => `3.48.2`
  - aiohttp: `3.8.4` => `3.9.5`
  - boto3: `1.26.163` => `1.34.106`
  - celery: `5.3.1` => `5.3.4`
  - django-cacheops: `7.0.1` => `7.0.2`
  - django-celery-beat: `2.5.0` => `2.6.0`
  - django-db-file-storage: `0.5.5` => `0.5.6.1`
  - django-environ: `0.10.0` => `0.11.2`
  - django-redis: `5.3.0` => `5.4.0`
  - django-storages: `1.13.2` => `1.14.3`
  - uvicorn[standard]: `0.22.0` => `0.29.0`

Fixes:
- fix record ready callback
- fix value check for empty parameters
- fix errors when a very long meeting name (>500 chars) was given

## 3.1.1 - 2023-09-28

Fixes:
- fix getRecordings endpoint when nothing is queried 
- fix ConnectionError exception when sending callback to given url
- fix filter records when no meeting_id or record_id aren't UUIDs


## 3.1.0 - 2023-06-29

Changes:
- add new BBB 2.6 API parameters
  - notifyRecordingIsOn
  - prsentationUploadExternalUrl
  - prsentationUploadExternalDescription
  - recordFullDurationMedia (v2.6.9)
  - disabledFeaturesExclude(2.6.9)
  - userdata-bbb_hide_presentation_on_join
- move configuration of checksum hash function from `ClusterGroups` to `Clusters`
- bumped python dependencies:
  - boto3: `1.26.119` => `1.26.163`
  - celery: `5.2.7` => `5.3.1`
  - Django: `3.2.18` => `3.2.19`
  - django-extensions: `3.2.1` => `3.2.3`
  - requests: `2.28.2` => `2.31.0`
  - django-cacheops: `7.0` => `7.0.1`
  - django-celery-results: `2.5.0` => `2.5.1`
  - django-redis: `5.2.0` => `5.3.0`
  - uvicorn: `0.21.1` => `0.22.0`

## 3.0.7 - 2023-06-02

Fixes:
- fix generated xml response

## 3.0.6 - 2023-05-22

Fixes:
- fix missing custom slide in POST create request from client


## 3.0.5 - 2023-05-19

Fixes:
- fix slide xml miss-format


## 3.0.4 - 2023-05-19

Fixes:
- fix cluster group filtering check in node status check routine
- add check for meeting existence, before continuing in pass through routine

## 3.0.3 - 2023-05-18

Fixes:
- missing statements: fix missing statements in pass through routines and metric endpoint

## 3.0.2 - 2023-05-18

Fixes:
- sha_algorithm: fix get sha algorithm if node is in multiple cluster groups

## 3.0.1 - 2023-05-11

Fixes:
- migration: fix unique nonce for meetings

## 3.0.0 - 2023-05-10

Features:
- recording: add BBB recording support
  - secret & tenant wise enabling/disabling of recording
  - local (needs to be shared by all b3lb instances) and S3 storage support
  - rendering based on [bbb-render](https://github.com/plugorgau/bbb-render/blob/master/make-xges.py)
  - rendering profile support
  - limitations:
    - no html video player
    - no podcast support

Changes:
- api:
  - refactoring api endpoint routines
  - update parameters for BigBlueButton API v2.5
  - new endpoints:
    - getRecordings
    - publishRecordings
    - deleteRecordings
    - updateRecordings (partial, only for `meta_name` and `meta_gl-listed`)
  - add alternative secret hash support (backend and frontend):
    - supported hashes: `sha1`, `sha256`, `sha384`, `sha512`
    - configurable frontend hash support
    - per cluster hash backend setting (default: `sha256`)
  - additional non-BBB endpoints:
    - raw recording upload (`b3lb-push` script)
    - download of rendered records
- worker:
  - queues now configurable via environment variable
    - core tasks
    - statistical tasks
    - recording (rendering) tasks
    - housekeeping tasks
- admin:
  - `Tenants`
    - added recording option (default: `false`)
    - added record holding time
  - `Secrets`
    - added recording option (default: `false`)
    - added record holding time
    - added APIMate Links
- nodes:
  - added `b3lb-push` script for recording push to B3LB backend

- added python dependencies:
  - boto3: `1.26.119`
  - django-storages: `1.13.2`
  - PyGObject: `3.44.1`
  - xmltodict: `0.13.0`
- bumped python dependencies:
  - aiohttp: `3.8.1` => `3.8.4`
  - Django: `3.2.15` => `3.2.18`
  - django-extensions: `3.2.0` => `3.2.1`
  - requests: `2.28.1` => `2.28.2`
  - django-cacheops: `6.1` => `7.0`
  - django-celery-beat: `2.3.0` => `2.5.0`
  - django-celery-results: `2.4.0` => `2.5.0`
  - django-environ: `0.9.0` => `0.10.0`
  - uvicorn: `0.18.2` => `0.21.1`
- dropped python dependencies:
  - django-split-settings
  - jinja2
- docker images
  - alpine: `3.16` => `3.17`
  - caddy: `2.5.2-alpine` => `2.6-alpine`
  - pypy: `3.9-7-slim` => `3.9-slim`
  - python: `3.10-slim` added

With b3lb 3.0 the support for redis 6 has been dropped! Redis 7 is now required by `django-cacheops`.

## 2.3.1 - 2022-08-11

Fixes:
- api: fix race condition on create code path

## 2.3.0 - 2022-08-09

Changes:
- adopt new BBB 2.5 API features
  - add insertDocument API call
  - add new API parameters
    - disabledFeatures
    - groups
    - lockSettingsHideViewersCursor
    - meetingExpireIfNoUserJoinedInMinutes
    - meetingExpireWhenLastUserLeftInMinutes
    - meta_fullaudio-bridge
    - preUploadedPresentationOverrideDefault
  - drop legacy API parameters
    - learningDashboardEnabled

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
