# -*- coding: utf-8 -*-
# creater by: barnett
"""
Django settings for goodrain_web project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys

from corsheaders.defaults import default_headers

SETTING_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# Create log directory
LOG_PATH = os.getenv("LOG_PATH", '/app/logs')
folder = os.path.exists(LOG_PATH)
if not folder:
    os.makedirs(LOG_PATH)

DEFAULT_HANDLERS = ['file_handler', 'console']

PROJECT_NAME = SETTING_DIR.split('/')[-1]

IS_OPEN_API = os.getenv("IS_OPEN_API", False)

DEBUG = os.getenv("DEBUG", False)

conf_file = '{0}/conf/{1}.py'.format(SETTING_DIR, 'www_com')
if os.path.exists(conf_file):
    execfile(conf_file)
else:
    raise Exception("config file not found: {}".format(conf_file))
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'hd_279hu4@3^bq&8w5hm_l$+xrip$_r8vh5t%ru(q8#!rauoj1'

# SECURITY WARNING: don't run with debug turned on in production!

AUTHENTICATION_BACKENDS = ('console.services.auth.backends.GoodRainSSOModelBackend',
                           'console.services.auth.backends.ModelBackend', 'console.services.auth.backends.PartnerModelBackend',
                           'console.services.auth.backends.WeChatModelBackend', 'django.contrib.auth.backends.ModelBackend')

LOGIN_URL = '/login'
INSTALLED_APPS = ('django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages',
                  'django.contrib.staticfiles', 'crispy_forms', 'rest_framework', 'rest_framework.authtoken',
                  'rest_framework_jwt', 'www', 'corsheaders', 'console', 'console.cloud')
# Application definition
if IS_OPEN_API:
    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'crispy_forms',
        'rest_framework',
        'rest_framework.authtoken',
        'rest_framework_jwt',
        'drf_yasg',
        'www',
        'corsheaders',
        'console',
        'openapi',
    )
    OAUTH2_PROVIDER = {
        'SCOPES': {
            'read': 'Read scope',
            'write': 'Write scope',
            'groups': 'Access to your groups'
        },
    }
MIDDLEWARE_CLASSES = (
    'goodrain_web.middleware.ErrorPage',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'console.services.auth.middleware.AuthenticationMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'goodrain_web.urls'

WSGI_APPLICATION = 'goodrain_web.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]
# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

DATABASE_ROUTERS = ['goodrain_web.router.MultiDbRouter']

LANGUAGE_CODE = 'zh-hans'

DEFAULT_CHARSET = 'utf8'

FILE_CHARSET = 'utf8'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = 'static/'
MEDIA_URL = '/data/media/'
MEDIA_ROOT = '/data/media'
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'standard': {
            'format': "%(asctime)s [%(levelname)s] localhost [%(funcName)s] %(pathname)s:%(lineno)s %(message)s",
            'datefmt': "%Y-%m-%d %H:%M:%S"
        }
    },
    'handlers': {
        'file_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_PATH + '/goodrain.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'request_api': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_PATH + '/request.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'standard'
        }
    },
    'loggers': {
        'default': {
            'handlers': DEFAULT_HANDLERS,
            'level': 'DEBUG',
            'propagate': True,
        },
        'request_api': {
            'handlers': ['request_api'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['request_api'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

# LICENSE = ""

# original is True
CORS_ORIGIN_ALLOW_ALL = True
# add this for solve cross domain
CORS_ALLOW_CREDENTIALS = True

CORS_ORIGIN_WHITELIST = ('*')

CORS_ALLOW_METHODS = ('DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT', 'VIEW', 'TRACE', 'CONNECT', 'HEAD')

CORS_ALLOW_HEADERS = default_headers + ('csrftoken', 'user_id', 'csrftoken', 'user_id', 'X_SSO_USER_ID', 'X_SSO_USER_TOKEN',
                                        'X_REGION_NAME', 'X_TEAM_NAME')
SWAGGER_SETTINGS = {'SECURITY_DEFINITIONS': {'Bearer': {'type': 'apiKey', 'name': 'Authorization', 'in': 'header'}}}

conf_file = '{0}/conf/{1}.py'.format(SETTING_DIR, os.environ.get('REGION_TAG', 'www_com').replace('-', '_'))

if os.path.exists(conf_file):
    execfile(conf_file)
else:
    raise Exception("config file not found: {}".format(conf_file))

DEF_IMAGE_REPO = "goodrain.me"

IMAGE_REPO = os.getenv("IMAGE_REPO", DEF_IMAGE_REPO)

RUNNER_IMAGE_NAME = IMAGE_REPO + "/runner"
