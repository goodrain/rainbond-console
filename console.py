import os

DEBUG = True

TEMPLATE_DEBUG = False

ZMQ_LOG_ADDRESS = 'tcp://127.0.0.1:9341'

DEFAULT_HANDLERS = ['file_handler']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'xxxx.xxx.xxx'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'xxx@xxx.com'
EMAIL_HOST_PASSWORD = 'xxxx'
EMAIL_USE_SSL = True

DISCOURSE_SECRET_KEY = 'xxxxx'

#ALLOWED_HOSTS = []

REGION_TOKEN = ""


WILD_DOMAIN = ".<domain>"


STREAM_DOMAIN = True


STREAM_DOMAIN_URL = {
    "cloudbang": "10.80.86.19"
}


WILD_DOMAINS = {
    "cloudbang": ".<domain>"
}

WILD_PORTS = {
    "cloudbang": "80"
}


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (),
    'DEFAULT_AUTHENTICATION_CLASSES': (),
    'PAGE_SIZE': 10
}


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': 3306,
    },
}


REGION_SERVICE_API = [{
    'url': 'http://region.goodrain.me:8888',
    'apitype': 'region service',
    'region_name': 'cloudbang'
}]


WEBSOCKET_URL = {
    'cloudbang': 'ws://:/websocket',
}


EVENT_WEBSOCKET_URL = {
    'cloudbang': 'auto',
}


APP_SERVICE_API = {
    'url': 'http://app.goodrain.com:80',
    'apitype': 'app service'
}

REGION_RULE = {
    'dev': {'personal_money': 0.069, 'company_money': 0.276, 'personal_month_money': 50, 'company_month_money': 100},
}

REGION_FEE_RULE = {
    'dev': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money': 0.8},
}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

MODULES = {
    "Owned_Fee": False,
    "Memory_Limit": False,
    "GitLab_Project": False,
    "GitLab_User": False,
    "Git_Hub": False,
    "Git_Code_Manual": True,
    "Finance_Center": False,
    "Team_Invite": True,
    "Monitor_Control": False,
    "User_Register": True,
    "Sms_Check": False,
    "Email_Invite": True,
    "Package_Show": False,
    "RegionToken": False,
    "Add_Port": True,
    "License_Center": False,
    "WeChat_Module": False,
    "Docker_Console": True,
    "Publish_YunShi": False,
    "Publish_Service": False,
}

REGIONS = (
    {"name": "cloudbang", "label": 'cloudbang', "enable": True},
)


# logo path
MEDIA_ROOT = '/data/media'

SN = '01d1S-WMrCLEKypQ_jCW78MEkB-LqhgMIvZIlK3x9vuS-WlUjMkUG5OK8OCe_4KvrfYptfyc8PWe7adI21D57JnbHMU7paNCLxu4xMCK3ACXO97LifX8EBpkJUdjv8AnK0uZ0qXkoe2t0KFr_3cKfsYyG7F--QniyVElkjp6UJTBqXFU5E88easFVqA4YP9ARCGdbcxlp3ga6rfMq1KlRPv3G73hN4diUvcoP_0aOLbD7v17cuWWRXTfIcP5d1JuDTOHc0z-lGjwVQj4iJesBS1QaD5YpgrsJXzKAvI01'

# log domain
LOG_DOMAIN = {
    "cloudbang": "auto"
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
    'is_wide_domain': True,
    'type': 'ws',
    'cloudbang': 'auto',
}


OAUTH2_APP = {
    'CLIENT_ID': '""',
    'CLIENT_SECRET': '""',
}
