DEBUG = False

TEMPLATE_DEBUG = True

ZMQ_LOG_ADDRESS = 'tcp://10.3.1.2:9341'

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
        'PORT': '3306',
    },
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
    'region_name': 'aws-jp-1'
}, {
    'url': 'http://api.ali-sh.goodrain.com:8888',
    'apitype': 'region service',
    'region_name': 'ali-sh'
}]


WEBSOCKET_URL = {
    'ucloud-bj-1': 'ws://mpush.ucloud-bj-1.goodrain.com:6060/websocket',
    'aws-bj-1': 'ws://mpush.aws-bj-1.goodrain.com:6060/websocket',
    'aws-jp-1': 'ws://mpush.aws-jp-1.goodrain.com:6060/websocket',
    'ali-sh': 'ws://mpush.ali-sh.goodrain.com:6060/websocket',
}

REGION_RULE = {
    'ucloud-bj-1': {'personal_money': 0.083, 'company_money': 0.208, 'personal_month_money': 60, 'company_month_money': 150},
    'aws-bj-1': {'personal_money': 0.243, 'company_money': 0.555, 'personal_month_money': 175, 'company_month_money': 400},
    'aws-jp-1': {'personal_money': 0.173, 'company_money': 0.417, 'personal_month_money': 125, 'company_month_money': 300},
    'ali-sh': {'personal_money': 0.069, 'company_money': 0.173, 'personal_month_money': 50, 'company_month_money': 125},
}

OPENTSDB_API = {
    'ucloud-bj-1': 'http://10.3.1.3:4242/api/query',
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
    'redirect_uri': 'http://user.goodrain.com/oauth/githup',
    'client_secret': '25b99d1d03323dd540eb72bfceb0e033062ccbe5',
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
    },
    'session': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
    }
}


SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_DOMAIN = '.goodrain.com'
SESSION_COOKIE_AGE = 3600
