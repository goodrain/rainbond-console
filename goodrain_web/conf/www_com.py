import os

DEBUG = False

TEMPLATE_DEBUG = False

ZMQ_LOG_ADDRESS = 'tcp://10.0.1.11:9341'

DEFAULT_HANDLERS = ['zmq_handler']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'smtp.ym.163.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'no-reply@goodrain.com'
EMAIL_HOST_PASSWORD = 'Thaechee3moo'
EMAIL_USE_SSL = True


DISCOURSE_SECRET_KEY = 'c2GZHIg8pcF2Pg5M'

ALLOWED_HOSTS = ['.goodrain.com', '.goodrain.io', '.goodrain.me']

REGION_TOKEN = "Token 5ca196801173be06c7e6ce41d5f7b3b8071e680a"

WILD_DOMAIN = ".goodrain.net"

STREAM_DOMAIN = False

STREAM_DOMAIN_URL = {
    "ali-sh": "",
    "aws-jp-1": "",
    "ucloud-bj-1": "",
    "xunda-bj": ""
}

WILD_DOMAINS = {
    "ali-sh": ".ali-sh.goodrain.net",
    "aws-jp-1": ".aws-jp-1.goodrain.net",
    "ucloud-bj-1": ".ucloud-bj-1.goodrain.net",
    "xunda-bj": ".xunda-bj.goodrain.net"
}

WILD_PORTS = {
    "ali-sh": "10080",
    "aws-jp-1": "80",
    "ucloud-bj-1": "10080",
    "xunda-bj": "10080",
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
    }
}

HTTP_PROXY = {
    'ali_hk_proxy': {'type': 'http', 'host': '203.88.170.137', 'port': 18888}
}

REGION_SERVICE_API = [{
    'url': 'http://api.ucloud-bj-1.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'ucloud-bj-1'
}, {
    'url': 'http://api.aws-jp-1.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'aws-jp-1'
}, {
    'url': 'http://api.ali-sh.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'ali-sh'
}, {
    'url': 'http://api.xunda-bj.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'xunda-bj'
}]

APP_SERVICE_API = {
    'url': 'http://app.goodrain.com:80',
    'apitype': 'app service'
}

WEBSOCKET_URL = {
    'ucloud-bj-1': 'wss://mpush-ucloud-bj-1.goodrain.com:6060/websocket',
    'aws-jp-1': 'wss://mpush-aws-jp-1.goodrain.com:6060/websocket',
    'ali-sh': 'wss://mpush-ali-sh.goodrain.com:6060/websocket',
    'xunda-bj': 'wss://mpush-xunda-bj.goodrain.com:6060/websocket',
}

REGION_RULE = {
    'ucloud-bj-1': {'personal_money': 0.083, 'company_money': 0.332, 'personal_month_money': 60, 'company_month_money': 120},
    'aws-jp-1': {'personal_money': 0.173, 'company_money': 0.692, 'personal_month_money': 125, 'company_month_money': 250},
    'ali-sh': {'personal_money': 0.069, 'company_money': 0.276, 'personal_month_money': 50, 'company_month_money': 100},
    'xunda-bj': {'personal_money': 0.069, 'company_money': 0.276, 'personal_month_money': 50, 'company_month_money': 100},
}

REGION_FEE_RULE = {
    'ucloud-bj-1': {'memory_money': 0.083, 'disk_money': 0.0069, 'net_money': 0.8},
    'aws-jp-1': {'memory_money': 0.173, 'disk_money': 0.0041, 'net_money': 0.89},
    'ali-sh': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money': 0.8},
    'xunda-bj': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money': 0.8},
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


SESSION_ENGINE = "www.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = 'session'
# SESSION_COOKIE_DOMAIN = '.goodrain.com'
# SESSION_COOKIE_AGE = 3600

MODULES = {
    "Owned_Fee": True,
    "Memory_Limit": True,
    "GitLab_Project": True,
    "GitLab_User": True,
    "Git_Hub": True,
    "Git_Code_Manual": False,
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
    "WeChat_Module": True,
    "Docker_Console": False,
    "Publish_YunShi": True,
    "Publish_Service": False,
}

REGIONS = (
    {"name": "xunda-bj", "label": u'\u8fc5\u8fbe\u4e91[\u5317\u4eac]', "enable": True},
    {"name": "ali-sh", "label": u'\u963f\u91cc\u4e91[\u4e0a\u6d77]', "enable": True},
    {"name": "aws-jp-1", "label": u'\u4e9a\u9a6c\u900a[\u65e5\u672c]', "enable": True},
)


# logo path
MEDIA_ROOT = '/data/media'
# log domain
LOG_DOMAIN = {
    "ali-sh": "ali-sh.download.goodrain.com",
    "aws-jp-1": "aws-jp-1.download.goodrain.com",
    "ucloud-bj-1": "ucloud-bj-1.download.goodrain.com",
    "xunda-bj": "xunda-bj.download.goodrain.com",
}
# open api
IS_OPEN_API = True

WECHAT_CALLBACK = {
    "console": "http://user.goodrain.com/wechat/callback",
    "console_bind": "http://user.goodrain.com/wechat/callbackbind",
    "console_goodrain": "http://user.goodrain.com/wechat/callback",
    "console_bind_goodrain": "http://user.goodrain.com/wechat/callbackbind",
    "index": "http://www.goodrain.com/product/",
}

DOCKER_WSS_URL = {
    'is_wide_domain': True,
    'type': 'wss',
    'ucloud-bj-1': 'ucloud-bj-1-ws.goodrain.com:8088',
    'aws-jp-1': 'aws-jp-1-ws.goodrain.com:8088',
    'ali-sh': 'ali-sh-ws.goodrain.com:8088',
    'xunda-bj': 'xunda-bj-ws.goodrain.com:8088',
}

OAUTH2_APP = {
    'CLIENT_ID': 'goodrain',
    'CLIENT_SECRET': 'fMnql3q1UAiR',
}

SN = '30b2owNzc8rJE-Ncmti1aHddSDjZQ3soGyeQ3grb43pCK8Q8_3FdV80fxpFmWeZeKziCl_a3zZiAdO6pmy9xtzCHTPX73yAEa4KuY6Yvu97mS88ID4R0ZAsksxoBvtfIKc7lxMX4ILh7xQoDn9r8QOsb6PQZFwa08373_nKoiIu6JPAZ8srwnpySkzUQilQ4gQGSuwG-NDGV8zJAHwfLc2zCIWtLvOLMEL-5jkq23rrEgfGmyUKln9yFMvRqyaL8ZO025oi901'

TENANT_VALID_TIME = 7
