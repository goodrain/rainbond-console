export PYTHONUNBUFFERED=1;
export APP_CLOUD_API=http://market.goodrain.com;
export MYSQL_HOST=114.115.183.10;
export MYSQL_PORT=30306;
export MYSQL_USER=root;
export MANAGE_TOKEN=1234567890;
export MYSQL_PASS=9c5f53c4;
export MYSQL_DB=console;
export IS_OPEN_API=true;
export LOG_PATH=$(pwd)/test/log;
export DJANGO_SETTINGS_MODULE=goodrain_web.settings;
export VIRTUAL_ENV=/Users/yangk/python/rainbond-console-cloud-copy/venv3;
export DYLD_LIBRARY_PATH=/usr/local/mysql/lib:$PATH;
export DB_TYPE=mysql;
export OPENAPI_V2=true
python3 manage.py runserver 114.115.183.10:7070