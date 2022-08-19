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


"""
Django settings for loadbalancer project.

Generated by 'django-admin startproject' using Django 3.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import os
import sys
import environ
import email.utils
import urllib.parse

# reading .env file
env = environ.Env()
environ.Env.read_env(env.str('ENV_FILE', default='.env'))


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from psycopg2cffi import compat
    compat.register()
except Exception as ex:
    print("Failed to register psycopg2cffi compat: {}".format(ex), file=sys.stderr)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

SECRET_KEY = env.str('SECRET_KEY')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

DATABASES = {
    'default': env.db()
}
CACHES = {
    'default': env.cache(default="locmemcache://b3lb-default-cache")
}

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'db_file_storage',

    'django_celery_beat',
    'django_celery_results',

    'cacheops',

    'rest',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'loadbalancer.urls'

DEFAULT_FILE_STORAGE = 'db_file_storage.storage.DatabaseFileStorage'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'loadbalancer.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configure Celery to use the django-celery-results backend.

CELERY_IGNORE_RESULT = True

CELERY_RESULT_BACKEND = 'django-db'

# Expire task results after 1h

CELERY_RESULT_EXPIRES = 3600

# Lock expiry time in second for singleton task locks.

CELERY_SINGLETON_LOCK_EXPIRY = 300

# Celery Broker

CELERY_BROKER_URL = urllib.parse.urlunparse(env.url('CELERY_BROKER_URL'))

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGE_CODE = env.str('LANGUAGE_CODE', default='en-us')
TIME_ZONE = env.str('TIME_ZONE', default='UTC')


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static")


# enable ORM caching for the rest app
CACHEOPS = {
    # cache all models up to 15s
    'rest.*': {'ops': 'all', 'timeout': 15},

    # cache assets up to 60s
    'rest.asset': {'ops': 'all', 'timeout': 60},
    'rest.assetlogo': {'ops': 'all', 'timeout': 60},
    'rest.assetslide': {'ops': 'all', 'timeout': 60},

    # we shall not cache any Meeting instances
    'rest.meeting': None,
}

# redis db for cacheops
CACHEOPS_REDIS = env.str('CACHEOPS_REDIS', default='redis://redis/2')

# fail gracefully if redis breaks
CACHEOPS_DEGRADE_ON_FAILURE = env.bool('CACHEOPS_DEGRADE_ON_FAILURE', True)


# Email settings
SERVER_EMAIL = env.str('SERVER_EMAIL', default='root@localhost')

EMAIL_CONFIG = env.email_url('EMAIL_URL', default='dummymail://')
vars().update(EMAIL_CONFIG)


# set Django admins for error notification
ADMINS = email.utils.getaddresses([env.str('DJANGO_ADMINS', '')])


######
# B3LB Base Settings
######

B3LB_API_BASE_DOMAIN = env.str('B3LB_API_BASE_DOMAIN')

B3LB_NODE_PROTOCOL = env.str('B3LB_NODE_PROTOCOL', default='https://')
B3LB_NODE_DEFAULT_DOMAIN = env.str('B3LB_NODE_DEFAULT_DOMAIN', default='bbbconf.de')
B3LB_NODE_BBB_ENDPOINT = env.str('B3LB_NODE_BBB_ENDPOINT', default='bigbluebutton/api/')
B3LB_NODE_LOAD_ENDPOINT = env.str('B3LB_NODE_LOAD_ENDPOINT', default='b3lb/load')
B3LB_NODE_REQUEST_TIMEOUT = env.int('B3LB_NODE_REQUEST_TIMEOUT', default=5)

B3LB_NO_SLIDES_TEXT = env.str('B3LB_NO_SLIDES_TEXT', default='<default>')

B3LB_CACHE_NML_PATTERN = env.str('B3LB_CACHE_NML_PATTERN', default='NML#{}')
B3LB_CACHE_NML_TIMEOUT = env.int('B3LB_CACHE_NML_TIMEOUT', default=30)

B3LB_API_MATE_BASE_URL = env.str('B3LB_API_MATE_BASE_URL', default='https://mconf.github.io/api-mate/')
B3LB_API_MATE_PW_LENGTH = env.int('B3LB_API_MATE_PW_LENGTH', default=13)

######
# B3LB Storage Setting
######

# MEDIA_ROOT for local storage
MEDIA_ROOT = env.path("B3LB_MEDIA_ROOT", default="/media_root")
B3LB_RECORD_STORAGE = env.str('B3LB_RECORD_STORAGE', default='local')
B3LB_S3_ACCESS_KEY = env.str('B3LB_S3_ACCESS_KEY', default=env.str('AWS_S3_ACCESS_KEY_ID', default=env.str('AWS_S3_SECRET_ACCESS_KEY', default='')))
B3LB_S3_BUCKET_NAME = env.str('B3LB_S3_BUCKET_NAME', 'raw')
B3LB_S3_ENDPOINT_URL = env.str('B3LB_S3_ENDPOINT_URL', default=env.str('AWS_S3_ENDPOINT_URL', default=''))
B3LB_S3_SECRET_KEY = env.str('B3LB_S3_SECRET_KEY', default=env.str('AWS_ACCESS_KEY_ID', default=env.str('AWS_SECRET_ACCESS_KEY', default='')))
B3LB_S3_URL_PROTOCOL = env.str('B3LB_S3_URL_PROTOCOL', default=env.str('AWS_S3_URL_PROTOCOL', default='https:'))

# Filesystem configuration
# max len is 26
# HIERARCHY_LEN * HIERARCHY_DEPHT < 26
B3LB_RECORD_PATH_HIERARCHY_WIDTH = env.int('B3LB_RECORD_PATH_HIERARCHY_WIDTH', default=2)
B3LB_RECORD_PATH_HIERARCHY_DEPHT = env.int('B3LB_RECORD_PATH_HIERARCHY_DEPHT', default=3)

######
# B3LB Celery Settings
######


B3LB_SCHEDULE_TASK_CHECK_NODES_QUEUE = env.str("B3LB_SCHEDULE_TASK_CHECK_NODES_QUEUE", default="b3lb")
B3LB_SCHEDULE_TASK_CLEANUP_ASSETS_QUEUE = env.str("B3LB_SCHEDULE_TASK_CLEANUP_ASSETS_QUEUE", default="b3lb")
B3LB_SCHEDULE_TASK_UPDATE_SECRET_LISTS_QUEUE = env.str("B3LB_SCHEDULE_TASK_UPDATE_SECRET_LISTS_QUEUE", default="b3lb")
B3LB_SCHEDULE_TASK_UPDATE_STATISTICS_QUEUE = env.str("B3LB_SCHEDULE_TASK_UPDATE_STATISTICS_QUEUE", default="b3lb")
B3LB_RECORD_TASK_DEFAULT_QUEUE = env.str("B3LB_RECORD_TASK_QUEUE", default="b3lb")
B3LB_RECORD_TASK_TEMPLATE_FOLDER = env.path("B3LB_RECORD_TASK_TEMPLATE_FOLDER", default="/templates").root
