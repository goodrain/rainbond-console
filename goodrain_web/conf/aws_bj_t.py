import os

DEBUG = True

TEMPLATE_DEBUG = True

ZMQ_LOG_ADDRESS = 'tcp://192.168.8.11:9341'

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
    "aws-bj-t": ""              
}

WILD_DOMAINS = {
    "aws-bj-t": ".aws-bj-t.goodrain.net",
}

WILD_PORTS = {
    "aws-bj-t": "10080",
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PERMISSION_CLASSES': (),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        #'rest_framework.authentication.BasicAuthentication',
        #'rest_framework.authentication.TokenAuthentication',
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
        'PASSWORD': 'aws-bj-test',
        'HOST': '192.168.8.11',
        'PORT': 3306,
    }
}

REGION_SERVICE_API = [{
    'url': 'http://region.goodrain.me:8888',
    'apitype': 'region service',
    'region_name': 'aws-bj-t'
}]

APP_SERVICE_API = {
    'url': 'http://app.goodrain.com:80',
    'apitype': 'app service'
}

WEBSOCKET_URL = {
    'aws-bj-t': 'wss://mpush-aws-bj-t.goodrain.com:6060/websocket',
}

REGION_RULE = {
    'aws-bj-t': {'personal_money': 0.069, 'company_money': 0.276, 'personal_month_money': 50, 'company_month_money': 100},
}

REGION_FEE_RULE = {
    'aws-bj-t': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money': 0.8},
}

GITLAB_SERVICE_API = {
    'url': 'http://code.goodrain.com/',
    'admin_user': 'xxx',
    'admin_email': 'xxx',
    'admin_password': 'xxx',
    'apitype': 'gitlab service',
}

GITHUB_SERVICE_API = {
    'client_id': 'xxxxx',
    'redirect_uri': 'https://user.goodrain.com/oauth/githup',
    'client_secret': 'xxxx',
}

UCLOUD_APP = {
    "secret_key": "xxxxxxx",
    "api_url": "https://api.ucloud.cn"
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '192.168.8.11:11211',
    },
}


SESSION_ENGINE = "www.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = 'session'
# SESSION_COOKIE_DOMAIN = '.goodrain.com'
# SESSION_COOKIE_AGE = 3600

MODULES = {
    "Owned_Fee": True,
    "Memory_Limit": False,
    "GitLab_Project": False,
    "GitLab_User": False,
    "Git_Hub": False,
    "Git_Code_Manual": True,
    "Finance_Center": True,
    "Team_Invite": True,
    "Monitor_Control": True,
    "User_Register": True,
    "Sms_Check": False,
    "Email_Invite": True,
    "Package_Show": True,
    "RegionToken": False,
    "Add_Port": True,
    "License_Center": False,
    "WeChat_Module": False,
    "Docker_Console": True,
}

REGIONS = (
    {"name": "aws-bj-t", "label": u'\u4e9a\u9a6c\u900a[\u5317\u4eac\u6d4b\u8bd5]', "enable": True},
)

# logo path
MEDIA_ROOT = '/data/media'

# cloud market url
CLOUD_ASSISTANT = 'goodrain'

# log domain
LOG_DOMAIN = {
    "aws-bj-t": "aws-bj-t.download.goodrain.com"            
}

# open api
IS_OPEN_API = False

WECHAT_CALLBACK = {
    "console": "",
    "console_bind": "",
    "console_goodrain": "",
    "console_bind_goodrain": "",
    "index": "http://www.goodrain.com/product/",
}


WSS_URL = {
    'aws-bj-t': '',
}