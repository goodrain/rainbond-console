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
        'USER': 'writer',
        'PASSWORD': 'a5bzkEP3bjc',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },
}

INFLEXDB ={
    "host" : "10.3.1.2",
    "port": 8086,
    "user": "root",
    "password": "root",
}

ETCD = {
    "host": "172.30.42.1",
    "port": 4001
}

BEANSTALKD = {
    "host": "10.3.1.2",
    "port": 11300,
    "tube": "default"
}

REGION_SERVICE_API = {
    'url': 'http://region.goodrain.me:8888',
    'apitype': 'region service',
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
    'redirect_uri': 'http://debug.goodrain.com/oauth/githup',
    'client_secret':'25b99d1d03323dd540eb72bfceb0e033062ccbe5',
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
#SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_DOMAIN = '.goodrain.com'
SESSION_COOKIE_AGE = 3600

