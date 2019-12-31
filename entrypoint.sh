#!/bin/bash

if [ "$1" = "debug" -o "$1" = "bash" ];then
    exec /bin/bash
elif [ "$1" = "version" ];then
    echo ${RELEASE_DESC}
elif [ "$1" = "init" ];then
    python manage.py makemigrations www
    python manage.py makemigrations console
    python manage.py migrate
else
    mysql -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASS} -e "select * from console.region_info" || ./entrypoint.sh init && echo "Database initialization completed"
    python upgrade.py
    exec gunicorn goodrain_web.wsgi -b 0.0.0.0:${PORT:-7070} --max-requests=5000 -k gevent --reload --debug --workers=4 --log-file - --access-logfile - --error-logfile -
fi
