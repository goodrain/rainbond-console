import os

DEBUG = False

TEMPLATE_DEBUG = False

ZMQ_LOG_ADDRESS = 'tcp://10.0.1.11:9341'

DEFAULT_HANDLERS = ['file_handler']

EMAIL_HOST = 'smtp.ym.163.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'no-reply@goodrain.com'
EMAIL_HOST_PASSWORD = 'Thaechee3moo'
EMAIL_USE_SSL = True

DISCOURSE_SECRET_KEY = 'c2GZHIg8pcF2Pg5M'

ALLOWED_HOSTS = ['.goodrain.com', '.goodrain.io']

REGION_TOKEN = "Token 5ca196801173be06c7e6ce41d5f7b3b8071e680a"

WILD_DOMAIN = ".goodrain.net"

STREAM_DOMAIN = False

STREAM_DOMAIN_URL = ""

WILD_DOMAINS = {
    "ali-sh":".ali-sh.goodrain.net",
    "aws-bj-1":".ali-sh.goodrain.net",
    "aws-jp-1":".ali-sh.goodrain.net",
    "ucloud-bj-1":".ali-sh.goodrain.net"
}

WILD_PORTS= {
    "ali-sh":"10080",
    "aws-bj-1":"10080",
    "aws-jp-1":"80",
    "ucloud-bj-1":"10080"
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    # 'DEFAULT_PERMISSION_CLASSES': (),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'PAGE_SIZE': 10
}

DATABASES = {
    # 'default': {
    #    'ENGINE': 'django.db.backends.sqlite3',
    #    'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # }
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'goodrain',
        'USER': os.environ.get('MYSQL_USER'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD'),
        'HOST': os.environ.get('MYSQL_HOST'),
        'PORT': os.environ.get('MYSQL_PORT'),
    },
    'stack': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'stack',
        'USER': os.environ.get('MYSQL_USER'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD'),
        'HOST': os.environ.get('MYSQL_HOST'),
        'PORT': os.environ.get('MYSQL_PORT'),
    },
}

HTTP_PROXY = {
    'ali_hk_proxy': {'type': 'http', 'host': '203.88.170.137', 'port': 18888}
}

REGION_SERVICE_API = [{
    'url': 'http://api.ucloud-bj-1.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'ucloud-bj-1'
}, {
    'url': 'http://api.aws-bj-1.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'aws-bj-1'
}, {
    'url': 'http://api.aws-jp-1.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'aws-jp-1',
    # 'proxy': HTTP_PROXY['ali_hk_proxy'],
    # 'proxy_priority': True,
}, {
    'url': 'http://api.ali-sh.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'ali-sh'
}]


WEBSOCKET_URL = {
    'ucloud-bj-1': 'wss://mpush-ucloud-bj-1.goodrain.com:6060/websocket',
    'aws-bj-1': 'wss://mpush-aws-bj-1.goodrain.com:6060/websocket',
    'aws-jp-1': 'wss://mpush-aws-jp-1.goodrain.com:6060/websocket',
    'ali-sh': 'wss://mpush-ali-sh.goodrain.com:6060/websocket',
}

REGION_RULE = {
    'ucloud-bj-1': {'personal_money': 0.083, 'company_money': 0.332, 'personal_month_money': 60, 'company_month_money': 120},
    'aws-bj-1': {'personal_money': 0.243, 'company_money': 0.972, 'personal_month_money': 175, 'company_month_money': 350},
    'aws-jp-1': {'personal_money': 0.173, 'company_money': 0.692, 'personal_month_money': 125, 'company_month_money': 250},
    'ali-sh': {'personal_money': 0.069, 'company_money': 0.276, 'personal_month_money': 50, 'company_month_money': 100},
}

REGION_FEE_RULE = {
    'ucloud-bj-1': {'memory_money': 0.083, 'disk_money': 0.0069, 'net_money': 0.8},
    'aws-bj-1': {'memory_money': 0.243, 'disk_money': 0.0041, 'net_money': 0.93},
    'aws-jp-1': {'memory_money': 0.173, 'disk_money': 0.0041, 'net_money': 0.89},
    'ali-sh': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money': 0.8},
}

GITLAB_SERVICE_API = {
    'url': 'http://code.goodrain.com/',
    'admin_user': 'app',
    'admin_email': 'app@goodrain.com',
    'admin_password': 'gr123465',
    'apitype': 'gitlab service',
}

GITHUB_SERVICE_API = {
    'client_id': 'c2cc316a9e6741e7b74a',
    'redirect_uri': 'https://user.goodrain.com/oauth/githup',
    'client_secret': '25b99d1d03323dd540eb72bfceb0e033062ccbe5',
}

QING_CLOUD_APP = {
    "app_id": "app-9x7m7zht", "secret_app_key": "XEmWiKVbXGSIu7c3LW5mkHBXdnpkKoUC2aTh8Gwl"
}

UCLOUD_APP = {
    "secret_key": "b701f150c808b2b067692ab3580e719d3d88f0ce",
    "api_url": "https://api.ucloud.cn"
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '{}:{}'.format(os.environ.get('MEMCACHED_HOST'), os.environ.get('MEMCACHED_PORT')),
    },
    'session': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '{}:{}'.format(os.environ.get('MEMCACHED_HOST'), os.environ.get('MEMCACHED_PORT')),
    }
}


SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_DOMAIN = '.goodrain.com'
SESSION_COOKIE_AGE = 3600

MODULES = {
    "Owned_Fee" : True,
    "Memory_Limit" : True,
    "GitLab_Project" : True,
    "GitLab_User" : True,
    "Git_Hub" : True,
    "Git_Code_Manual":False,
    "Finance_Center" : True,
    "Team_Invite" : True,
    "Multi_Region" : True,
    "Monitor_Control" : True,
    "User_Register" : True,
    "Sms_Check" : True,
    "Email_Invite" : True,
    "Package_Show" : True
}



