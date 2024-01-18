# -*- coding: utf-8 -*-
# creater by: barnett
"""
Django settings for goodrain_web project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""
import datetime
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys

from corsheaders.defaults import default_headers

from goodrain_web.mac_hash import get_hash_mac

# rainbond version
VERSION = "5.3.0"
DEFAULT_ENTERPRISE_ID_PATH = "/app/data/ENTERPRISE_ID"

APPEND_SLASH = True
SETTING_DIR = os.path.dirname(__file__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HOME_DIR = os.getenv("HOME_DIR", BASE_DIR)

DATA_DIR = os.path.join(HOME_DIR, 'data')
DATA_DIR = os.getenv("DATA_DIR", DATA_DIR)
# Create log directory
LOG_PATH = os.getenv("LOG_PATH", os.path.join(HOME_DIR, 'logs'))
folder = os.path.exists(LOG_PATH)
if not folder:
    os.makedirs(LOG_PATH)

MEDIA_URL = '/data/media/'
MEDIA_ROOT = os.path.join(DATA_DIR, 'media')

DEFAULT_HANDLERS = ['file_handler', 'console']

PROJECT_NAME = SETTING_DIR.split('/')[-1]

IS_OPEN_API = os.getenv("IS_OPEN_API", True)

debug = os.environ.get('DEBUG')
if debug:
    DEBUG = (debug.lower() == "true")
else:
    DEBUG = False

TEMPLATE_DEBUG = os.environ.get('TEMPLATE_DEBUG') or False

SECRET_KEY = get_hash_mac()
DEFAULT_HANDLERS = [os.environ.get('DEFAULT_HANDLERS') or 'file_handler']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", default="*").split(",", -1)

MANAGE_SECRET_KEY = os.environ.get('MANAGE_SECRET_KEY', "")

EMAIL_HOST = '***'
EMAIL_PORT = 465
EMAIL_HOST_USER = '***'
EMAIL_HOST_PASSWORD = '***'
EMAIL_USE_SSL = True

GITLAB_ADMIN_NAME = "app"
GITLAB_ADMIN_ID = 2

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated', ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'EXCEPTION_HANDLER':
    'console.views.base.custom_exception_handler',
}

DATABASE_TYPE = os.environ.get('DB_TYPE') or 'sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DATA_DIR, 'db.sqlite3'),
        # The lifetime of a database connection, in seconds. Use 0 to close database connections at the end of each request
        # — Django’s historical behavior — and None for unlimited persistent connections.
        # Refer: https://docs.djangoproject.com/en/2.2/ref/settings/#conn-max-age
        # If you use sqlite's wal mode, you need to establish a persistent connection
        # Make database in wal mode ahead of time in shell script, Refer: https://code.djangoproject.com/ticket/24018#comment:8
        'CONN_MAX_AGE': None,
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

if DATABASE_TYPE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('MYSQL_DB') or "console",
            'USER': os.environ.get('MYSQL_USER') or "root",
            'PASSWORD': os.environ.get('MYSQL_PASS') or "",
            'HOST': os.environ.get('MYSQL_HOST') or "127.0.0.1",
            'PORT': os.environ.get('MYSQL_PORT') or "3306",
        }
    }

APP_SERVICE_API = {'url': os.environ.get('APP_CLOUD_API', 'http://api.goodrain.com:80'), 'apitype': 'app service'}

SSO_LOGIN = os.getenv("SSO_LOGIN", "").upper()
MODULES = {
    "Owned_Fee": True,
    "Memory_Limit": True,
    "Finance_Center": True,
    "Team_Invite": True,
    "Monitor_Control": True,
    "User_Register": True,
    "Sms_Check": True,
    "Email_Invite": True,
    "Package_Show": True,
    "RegionToken": True,
    "Add_Port": False,
    "License_Center": True,
    "WeChat_Module": False,
    "Docker_Console": True,
    "Publish_YunShi": True,
    "Publish_Service": False,
    "Privite_Github": False,
    "SSO_LOGIN": SSO_LOGIN == "TRUE",
}

TENANT_VALID_TIME = 7

JWT_AUTH = {
    'JWT_ENCODE_HANDLER': 'rest_framework_jwt.utils.jwt_encode_handler',
    'JWT_DECODE_HANDLER': 'rest_framework_jwt.utils.jwt_decode_handler',
    'JWT_PAYLOAD_HANDLER': 'rest_framework_jwt.utils.jwt_payload_handler',
    'JWT_PAYLOAD_GET_USER_ID_HANDLER': 'rest_framework_jwt.utils.jwt_get_user_id_from_payload_handler',
    'JWT_RESPONSE_PAYLOAD_HANDLER': 'rest_framework_jwt.utils.jwt_response_payload_handler',
    'JWT_SECRET_KEY': SECRET_KEY,
    'JWT_GET_USER_SECRET_KEY': None,
    'JWT_PUBLIC_KEY': None,
    'JWT_PRIVATE_KEY': None,
    'JWT_ALGORITHM': 'HS256',
    'JWT_VERIFY': True,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_LEEWAY': 0,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=15),
    'JWT_AUDIENCE': None,
    'JWT_ISSUER': None,
    'JWT_ALLOW_REFRESH': False,
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=15),
    'JWT_AUTH_HEADER_PREFIX': 'GRJWT',
    'JWT_AUTH_COOKIE': "token",
}

# 以下参数待去除
LICENSE = ""

WILD_PORTS = {}

WILD_DOMAINS = {}

REGION_RULE = {}

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

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
CRISPY_TEMPLATE_PACK = 'bootstrap3'

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

# original is True
CORS_ORIGIN_ALLOW_ALL = True
# add this for solve cross domain
CORS_ALLOW_CREDENTIALS = True

CORS_ORIGIN_WHITELIST = ('*')

CORS_ALLOW_METHODS = ('DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT', 'VIEW', 'TRACE', 'CONNECT', 'HEAD')

CORS_ALLOW_HEADERS = default_headers + ('csrftoken', 'user_id', 'csrftoken', 'user_id', 'X_SSO_USER_ID', 'X_SSO_USER_TOKEN',
                                        'X_REGION_NAME', 'X_TEAM_NAME')
SWAGGER_SETTINGS = {'SECURITY_DEFINITIONS': {'Bearer': {'type': 'apiKey', 'name': 'Authorization', 'in': 'header'}}}

DEF_IMAGE_REPO = "goodrain.me"

IMAGE_REPO = os.getenv("IMAGE_REPO", DEF_IMAGE_REPO)

RUNNER_IMAGE_NAME = IMAGE_REPO + "/runner"
