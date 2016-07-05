import os

DEBUG = False

TEMPLATE_DEBUG = True

ZMQ_LOG_ADDRESS = 'tcp://10.16.1.103:9341'

DEFAULT_HANDLERS = ['zmq_handler']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'xxxx.xxx.xxx'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'xxx@xxx.com'
EMAIL_HOST_PASSWORD = 'xxxx'
EMAIL_USE_SSL = True

DISCOURSE_SECRET_KEY = 'xxxxx'

ALLOWED_HOSTS = ['.yjzycp.net']

REGION_TOKEN = ""

WILD_DOMAIN = ".yjzycp.net"

STREAM_DOMAIN = True

STREAM_DOMAIN_URL = {
    "dev": "10.16.1.211"
}

WILD_DOMAINS = {
    "dev":".yjzycp.net"
}

WILD_PORTS = {
    "dev":"80"
}

REST_FRAMEWORK = {
    # 'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PERMISSION_CLASSES': (),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
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
        'NAME': 'console',
        'USER': 'writer',
        'PASSWORD': 'B7n4mrP4T2',
        'HOST': '10.16.1.103',
        'PORT': 3306,
    },
}


REGION_SERVICE_API = [{
    'url': 'http://10.16.1.103:8888',
    'apitype': 'region service',
    'region_name': 'dev'
}]


WEBSOCKET_URL = {
    'dev': 'ws://console.yjzycp.net:6060/websocket',
}

GITLAB_SERVICE_API = {
    'url': 'http://cc.goodrain.com/',
    'admin_user': 'cc',
    'admin_email': 'cc@goodrain.com',
    'admin_password': 'cc',
    'apitype': 'gitlab service',
}

APP_SERVICE_API = {
    'url': 'http://app.goodrain.com:80',
    'apitype': 'app service'
}

GITHUB_SERVICE_API = {
    'client_id': 'gg',
    'redirect_uri': 'https://gg.goodrain.com/oauth/githup',
    'client_secret': 'gg',
}


REGION_RULE = {
    'dev': {'personal_money': 0.069, 'company_money': 0.276, 'personal_month_money': 50, 'company_month_money': 100},
}

REGION_FEE_RULE = {
    'dev': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money': 0.8},
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '10.16.1.103:11211',
    },
}


SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = 'session'
# SESSION_COOKIE_DOMAIN = '.goodrain.com'
# SESSION_COOKIE_AGE = 3600
MODULES = {
    "Owned_Fee" : False,
    "Memory_Limit" : False,
    "GitLab_Project" : False,
    "GitLab_User" : False,
    "Git_Hub" : False,
    "Git_Code_Manual":True,
    "Finance_Center" : False,
    "Team_Invite" : False,
    "Monitor_Control" : False,
    "User_Register" : False,
    "Sms_Check" : False,
    "Email_Invite" : False,
    "Package_Show" : False,
    "RegionToken" : False,
    "Add_Port": True,
    "License_Center":False,
    "WeChat_Module": False,
    "Docker_Console": True,
    "Publish_YunShi": False,
    "Publish_Service": False,
}

REGIONS = (
    {"name": "dev", "label": 'dev', "enable": True},
)

# logo path
MEDIA_ROOT = '/data/media'

CLOUD_ASSISTANT = 'yjcp'

# log domain
LOG_DOMAIN = {
    "dev": "dev.download.yjzycp.net"
}

IS_OPEN_API = False

WECHAT_CALLBACK = {
    "console": "",
    "console_bind": "",
    "console_goodrain": "",
    "console_bind_goodrain": "",
    "index": "",
}

DOCKER_WSS_URL = {
    'dev': '',
}