DEBUG = True

TEMPLATE_DEBUG = True

DATABASES = {
    #'default': {
    #    'ENGINE': 'django.db.backends.sqlite3',
    #    'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    #}
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'goodrain',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },
}

REGION_SERVICE_API = [{
    'url': 'http://192.168.7.18:8080',
    'apitype': 'region service',
    'region_name': 'ucloud_bj_1'
}]

WEBSOCKET_URL = {
    'ucloud_bj_1': 'ws://123.59.40.70:6060/websocket'
}

GITLAB_SERVICE_API = {
    'url': 'http://code1.goodrain.com/',
    'admin_user': 'app1',
    'admin_email': 'app1@goodrain.com',
    'admin_password': 'gr123465',
    'apitype': 'gitlab service',
}

GITHUB_SERVICE_API = {
    'client_id': 'c2cc316a9e6741e7b74a',
    'redirect_uri': 'https://user.goodrain.com/oauth/githup',
    'client_secret': '25b99d1d03323dd540eb72bfceb0e033062ccbe5',
}

# CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
#        'LOCATION': '192.168.7.11:11211',
#    },
#    'session': {
#        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
#        'LOCATION': '192.168.7.11:11211',
#    }
#}


#SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_DOMAIN = '.goodrain.com'
SESSION_COOKIE_AGE = 3600

# logo path
MEDIA_ROOT = '/data/media'

# cloud market url
CLOUD_MARKET = 'http://app.goodrain.com/'
CLOUD_ASSISTANT = 'goodrain'
