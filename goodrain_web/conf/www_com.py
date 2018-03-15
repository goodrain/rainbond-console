# -*- coding: utf8 -*-
import os
import datetime

DEBUG = os.environ.get('DEBUG') or False

TEMPLATE_DEBUG = os.environ.get('TEMPLATE_DEBUG') or False

ZMQ_LOG_ADDRESS = 'tcp://10.0.1.11:9341'

SECRET_KEY = 'hd_279hu4@3^bq&8w5hm_l$+xrip$_r8vh5t%ru(q8#!rauoj1'

DEFAULT_HANDLERS = [os.environ.get('DEFAULT_HANDLERS') or 'zmq_handler']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

ALLOWED_HOSTS = ['.goodrain.com', '.goodrain.io', '.goodrain.me', '.goodrain.org']

EMAIL_HOST = '***'
EMAIL_PORT = 465
EMAIL_HOST_USER = '***'
EMAIL_HOST_PASSWORD = '***'
EMAIL_USE_SSL = True

GITLAB_ADMIN_NAME = "app"
GITLAB_ADMIN_ID = 2

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'EXCEPTION_HANDLER': 'console.views.base.custom_exception_handler',
    'PAGE_SIZE': 10
}

DATABASES = {
    # 'default': {
    #    'ENGINE': 'django.db.backends.sqlite3',
    #    'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # }
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MYSQL_DB'),
        'USER': os.environ.get('MYSQL_USER'),
        'PASSWORD': os.environ.get('MYSQL_PASS'),
        'HOST': os.environ.get('MYSQL_HOST'),
        'PORT': os.environ.get('MYSQL_PORT'),
    }
}

APP_SERVICE_API = {
    'url': 'http://api.goodrain.com:80',
    'apitype': 'app service'
}


SESSION_ENGINE = "www.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = 'session'
# SESSION_COOKIE_DOMAIN = '.goodrain.com'
# SESSION_COOKIE_AGE = 3600

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
    "SSO_LOGIN": True,
}

if MODULES["SSO_LOGIN"]:
    CACHES = {
        'default': {
            'BACKEND':
                'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION':
                '{}:{}'.format(
                    os.environ.get('MEMCACHED_HOST'),
                    os.environ.get('MEMCACHED_PORT')),
        },
        'session': {
            'BACKEND':
                'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION':
                '{}:{}'.format(
                    os.environ.get('MEMCACHED_HOST'),
                    os.environ.get('MEMCACHED_PORT')),
        }
    }

# logo path
MEDIA_ROOT = '/data/media'

# open api
IS_OPEN_API = True

WECHAT_CALLBACK = {
    "console": "http://user.goodrain.com/wechat/callback",
    "console_bind": "http://user.goodrain.com/wechat/callbackbind",
    "console_goodrain": "http://user.goodrain.com/wechat/callback",
    "console_bind_goodrain": "http://user.goodrain.com/wechat/callbackbind",
    "index": "http://www.goodrain.com/product/",
}

OAUTH2_APP = {
    'CLIENT_ID': 'goodrain',
    'CLIENT_SECRET': 'fMnql3q1UAiR',
}

TENANT_VALID_TIME = 7

JWT_AUTH = {
    'JWT_ENCODE_HANDLER':
    'rest_framework_jwt.utils.jwt_encode_handler',
    'JWT_DECODE_HANDLER':
    'rest_framework_jwt.utils.jwt_decode_handler',
    'JWT_PAYLOAD_HANDLER':
    'rest_framework_jwt.utils.jwt_payload_handler',
    'JWT_PAYLOAD_GET_USER_ID_HANDLER':
    'rest_framework_jwt.utils.jwt_get_user_id_from_payload_handler',
    'JWT_RESPONSE_PAYLOAD_HANDLER':
    'rest_framework_jwt.utils.jwt_response_payload_handler',
    'JWT_SECRET_KEY':
    SECRET_KEY,
    'JWT_GET_USER_SECRET_KEY':
    None,
    'JWT_PUBLIC_KEY':
    None,
    'JWT_PRIVATE_KEY':
    None,
    'JWT_ALGORITHM':
    'HS256',
    'JWT_VERIFY':
    True,
    'JWT_VERIFY_EXPIRATION':
    True,
    'JWT_LEEWAY':
    0,
    'JWT_EXPIRATION_DELTA':
    datetime.timedelta(days=15),
    'JWT_AUDIENCE':
    None,
    'JWT_ISSUER':
    None,
    'JWT_ALLOW_REFRESH':
    False,
    'JWT_REFRESH_EXPIRATION_DELTA':
    datetime.timedelta(days=15),
    'JWT_AUTH_HEADER_PREFIX':
    'GRJWT',
    'JWT_AUTH_COOKIE':
    None,
}

# 以下参数待去除
LICENSE = ""

WILD_PORTS = {}

WILD_DOMAINS = {}

REGION_RULE = {}


