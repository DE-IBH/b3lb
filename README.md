# B3LB - BigBlueButton Load Balancer


## About

B3LB is a open source [BigBlueButton API](https://docs.bigbluebutton.org/dev/api.html) load balancer similar to [Scalelite](https://github.com/blindsidenetworks/scalelite). B3LB is based on the [Django](https://www.djangoproject.com/) Python Web framework and is designed to work in large scale-out deployments with 100+ BigBlueButton nodes and high attendee join rates. The project started at [IBH IT-Service GmbH](https://www.ibh.de/) in the fall 2020 and has been published in February 2021 during the second lock down in Germany.

This project uses BigBlueButton and is not endorsed or certified by BigBlueButton Inc. BigBlueButton and the BigBlueButton Logo are trademarks of BigBlueButton Inc.


## Features

General:
- proven for massive scale-out deployment
- extensive caching based on [Redis](https://redis.io/)

Frontend API:
- deployed on ASGI with [uvicorn](https://www.uvicorn.org/)
- multitenancy support:
- multiple API sub secrets per tenant
  (i.e. for multiple LMS)
- API secret rollover
- per tenant customization:
  - start presentation
  - branding logo
- precalculated responses for expensive API calls
  (`getMeetings`)
- prometheus and json metrics:
  - global
  - per tenant
- group BBB nodes into clusters:
  - map tenants to clusters
  - different load balancing factors per cluster

Worker:
- using [Celery](http://celeryproject.org/) for node polling


## Prerequisites

- BBB nodes
- a dedicated DNS domain with a wildcard RR
- wildcard certificate or [Let's Encrypt DNS-01 challange support](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge)
- docker runtime to run frontend, worker and auxiliary services
- PostgreSQL database


## Setup & Documentation

*TODO*
