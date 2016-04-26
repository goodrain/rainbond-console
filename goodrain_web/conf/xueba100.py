
DEBUG = True

TEMPLATE_DEBUG = True

ZMQ_LOG_ADDRESS = 'tcp://gr-docker-scheduler-001:9341'

DEFAULT_HANDLERS = ['zmq_handler']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = 'xxxx.xxx.xxx'
EMAIL_PORT = 465
EMAIL_HOST_USER = 'xxx@xxx.com'
EMAIL_HOST_PASSWORD = 'xxxx'
EMAIL_USE_SSL = True

DISCOURSE_SECRET_KEY = 'xxxxx'

ALLOWED_HOSTS = ['.xueba100.net', '.xueba100.com', '.xueba100.com']

REGION_TOKEN = ""

WILD_DOMAIN = ".docker.xueba100.net"

STREAM_DOMAIN = True

STREAM_DOMAIN_URL = "nat.xueba100.net"

WILD_DOMAINS = {
    "xueba100":".docker.xueba100.net"
}

WILD_PORTS= {
    "xueba100":"80"
}

REST_FRAMEWORK = {
    #'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
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
        'PASSWORD': '3x2tRMu72o',
        'HOST': 'gr-docker-scheduler-003',
        'PORT': 3306,
    },
}


REGION_SERVICE_API = [{
    'url': 'http://region.goodrain.me:8888',
    'apitype': 'region service',
    'region_name': 'xueba100'
}]


WEBSOCKET_URL = {
    'xueba100': 'ws://mpush.xueba100.net:6060/websocket',
}

GITLAB_SERVICE_API = {
    'url': 'http://cc.goodrain.com/',
    'admin_user': 'cc',
    'admin_email': 'cc@goodrain.com',
    'admin_password': 'cc',
    'apitype': 'gitlab service',
}

GITHUB_SERVICE_API = {
    'client_id': 'gg',
    'redirect_uri': 'https://gg.goodrain.com/oauth/githup',
    'client_secret': 'gg',
}

REGION_RULE = {
    'xueba100': {'personal_money': 0.069, 'company_money': 0.276, 'personal_month_money': 50, 'company_month_money': 100},
}

REGION_FEE_RULE = {
    'xueba100': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money': 0.8},
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': 'gr-docker-scheduler-001:11211',
    },
}


SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = 'session'
#SESSION_COOKIE_DOMAIN = '.goodrain.com'
#SESSION_COOKIE_AGE = 3600
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
    "RegionToken" : False
}

#"学霸100".decode('UTF-8')
REGIONS = (
    {"name": "xueba100", "label": u'\u5b66\u9738100', "enable": True}
)
