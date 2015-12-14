DEBUG = False

TEMPLATE_DEBUG = True

ZMQ_LOG_ADDRESS = 'tcp://10.0.1.11:9341'

DEFAULT_HANDLERS = ['zmq_handler']

DATABASES = {
    # 'default': {
    #    'ENGINE': 'django.db.backends.sqlite3',
    #    'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # }
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'goodrain',
        'USER': 'writer',
        'PASSWORD': 'a5bzkEP3bjc',
        'HOST': '127.0.0.1',
        'PORT': '3307',
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
    'ucloud-bj-1': {'memory_money': 0.083, 'disk_money': 0.0069, 'net_money':0.8},
    'aws-bj-1': {'memory_money': 0.243, 'disk_money': 0.0041, 'net_money':0.93},
    'aws-jp-1': {'memory_money': 0.173, 'disk_money': 0.0041, 'net_money':0.89},
    'ali-sh': {'memory_money': 0.069, 'disk_money': 0.0041, 'net_money':0.8},
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
        'LOCATION': '127.0.0.1:11212',
    },
    'session': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11212',
    }
}


SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_DOMAIN = '.goodrain.com'
SESSION_COOKIE_AGE = 3600
