"""
Django settings for goodrain_web project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS as TCP

SETTING_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

ZMQ_LOG_ADDRESS = 'tcp://127.0.0.1:9341'

DEFAULT_HANDLERS = ['file_handler']

PROJECT_NAME = SETTING_DIR.split('/')[-1]

IS_OPEN_API = False

DEBUG = False

conf_file = '{0}/conf/{1}.py'.format(SETTING_DIR, "www_com")

if os.path.exists(conf_file):
    execfile(conf_file)
else:
    raise Exception("config file not found: {}".format(conf_file))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'hd_279hu4@3^bq&8w5hm_l$+xrip$_r8vh5t%ru(q8#!rauoj1'

# SECURITY WARNING: don't run with debug turned on in production!

AUTHENTICATION_BACKENDS = ('www.auth.backends.GoodRainSSOModelBackend',
                           'www.auth.backends.ModelBackend',
                           'www.auth.backends.PartnerModelBackend',
                           'www.auth.backends.WeChatModelBackend',
                           'django.contrib.auth.backends.ModelBackend')

LOGIN_URL = '/login'

# Application definition
if IS_OPEN_API:
    INSTALLED_APPS = ('django.contrib.admin', 'django.contrib.auth',
                      'django.contrib.contenttypes', 'django.contrib.sessions',
                      'django.contrib.messages', 'django.contrib.staticfiles',
                      'crispy_forms', 'rest_framework','rest_framework_jwt',
                      'rest_framework.authtoken', 'rest_framework_swagger',
                      'www', 'api', 'openapi', 'oauth2_provider', 'cadmin',
                      'share', 'backends', 'marketapi','corsheaders','console')
    OAUTH2_PROVIDER = {
        'SCOPES': {
            'read': 'Read scope',
            'write': 'Write scope',
            'groups': 'Access to your groups'
        },
    }
else:
    INSTALLED_APPS = ('django.contrib.auth', 'django.contrib.contenttypes',
                      'django.contrib.sessions', 'django.contrib.messages',
                      'django.contrib.staticfiles', 'crispy_forms',
                      'rest_framework', 'rest_framework.authtoken', 'rest_framework_jwt',
                      'rest_framework_swagger', 'www', 'api', 'cadmin',
                      'share', 'backends', 'marketapi','corsheaders', 'console')

MIDDLEWARE_CLASSES = (
    'goodrain_web.middleware.ErrorPage',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'www.auth.middleware.AuthenticationMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', )

ROOT_URLCONF = 'goodrain_web.urls'

WSGI_APPLICATION = 'goodrain_web.wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS = TCP + (
    'django.core.context_processors.request', )
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
            'format':
            "%(asctime)s [%(levelname)s] localhost [%(funcName)s] %(pathname)s:%(lineno)s %(message)s",
            'datefmt':
            "%Y-%m-%d %H:%M:%S"
        },
        'zmq_formatter': {
            'format':
            "%(asctime)s [%(levelname)s] %(hostname)s [%(funcName)s] %(pathname)s:%(lineno)s %(message)s",
            'datefmt':
            "%Y-%m-%d %H:%M:%S"
        },
    },
    'handlers': {
        'file_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/goodrain.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'request_api': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/request.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'zmq_handler': {
            'level': "DEBUG",
            'class': 'goodrain_web.log.ZmqHandler',
            'address': ZMQ_LOG_ADDRESS,
            'root_topic': 'goodrain_web',
            'formatter': 'zmq_formatter',
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
        }
    }
}

#LICENSE = ""

# original is True
CORS_ORIGIN_ALLOW_ALL = False
# add this for solve cross domain
CORS_ALLOW_CREDENTIALS = True

CORS_ORIGIN_WHITELIST = (
    "localhost:8000",
    "127.0.0.1:8000",
    "localhost:9001",
    "127.0.0.1:9001",
)

CORS_ALLOW_METHODS = (
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
)

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = default_headers + (
    'csrftoken',
    'user_id',
    'X_SSO_USER_ID',
    'X_SSO_USER_TOKEN',
    'X_REGION_NAME',
    'X_TEAM_NAME'
)
