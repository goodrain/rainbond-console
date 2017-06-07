import os
DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'console',
        'USER': 'build',
        'PASSWORD': 'build',
        'HOST': os.environ.get('MYSQL_HOST', '127.0.0.1'),
        'PORT': 3306,
    }
}

REGION_TOKEN = ''

STREAM_DOMAIN_URL = {
    "ali-sh": "",
    "aws-jp-1": "",
    "ucloud-bj-1": "",
    "xunda-bj": ""
}

WILD_DOMAINS = {
    "ali-sh": ".ali-sh.goodrain.net",
}

WILD_PORTS = {
    "ali-sh": "10080",
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

REGION_SERVICE_API = [{
    'url': 'http://api.ali-sh.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'ali-sh'
}]

APP_SERVICE_API = {
    'url': 'http://app.goodrain.com:80',
    'apitype': 'app service'
}

WEBSOCKET_URL = {
    'ali-sh': 'wss://mpush-ali-sh.goodrain.com:6060/websocket',
}

REGION_RULE = {
    'ali-sh': {'personal_money': 0.069, 'company_money': 0.276, 'personal_month_money': 50, 'company_month_money': 100},
}

REGION_FEE_RULE = {
    'ali-sh': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money': 0.8},
}

QING_CLOUD_APP = {
    "app_id": "app-1", "secret_app_key": "1"
}

UCLOUD_APP = {
    "secret_key": "bbb",
    "api_url": "https://api.ucloud.cn"
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
    "WeChat_Module": True,
    "Docker_Console": False,
    "Publish_YunShi": True,
    "Publish_Service": False,
    "Privite_Github": False,
}

REGIONS = (
    {"name": "ali-sh", "label": u'\u963f\u91cc\u4e91[\u4e0a\u6d77]', "enable": True},
)
