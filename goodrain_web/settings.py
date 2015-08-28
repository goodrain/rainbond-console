"""
Django settings for goodrain_web project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import sys
import os
SETTING_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PROJECT_NAME = SETTING_DIR.split('/')[-1]

REGION_TAG = os.environ.get('REGION_TAG')

DEBUG = False
if not DEBUG and (REGION_TAG is None or REGION_TAG == ""):
    REGION_TAG = "www_com"

conf_name = '{0}.conf.{1}'.format(PROJECT_NAME, REGION_TAG)
__import__(conf_name)
conf_mod = sys.modules[conf_name]

for k in dir(conf_mod):
    if k.startswith('_'):
        pass
    else:
        v = getattr(conf_mod, k)
        if isinstance(v, str):
            exec "{0} = '{1}'".format(k, v)
        elif isinstance(v, (list, dict, tuple)):
            exec "{0} = {1}".format(k, v)
        elif isinstance(v, bool):
            exec "{0} = {1}".format(k, v)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'hd_279hu4@3^bq&8w5hm_l$+xrip$_r8vh5t%ru(q8#!rauoj1'

# SECURITY WARNING: don't run with debug turned on in production!
ALLOWED_HOSTS = ['.goodrain.com', '.goodrain.io']

AUTHENTICATION_BACKENDS = ('www.auth.backends.ModelBackend',)

LOGIN_URL = '/login'

# Application definition

INSTALLED_APPS = (
    #'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'rest_framework',
    'rest_framework_swagger',
    'www',
    'api',
)

MIDDLEWARE_CLASSES = (
    'goodrain_web.middleware.ErrorPage',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    'www.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'goodrain_web.urls'

WSGI_APPLICATION = 'goodrain_web.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

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

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.ym.163.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'no-reply@goodrain.com'
EMAIL_HOST_PASSWORD = 'Thaechee3moo'
EMAIL_USE_SSL = True

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

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
        },
    },
    'handlers': {
        'file_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/goodrain.log',
            'maxBytes': 1024*1024*5,
            'backupCount': 5,
            'formatter': 'standard',
        },
    },
    'loggers': {
        'default': {
            'handlers': ['file_handler'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}
