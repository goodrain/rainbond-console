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
    # check database
    if mysql -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASS} -e "use console;" > /dev/null; then
        lockfile=/app/lock/entrypoint.lock
        if [ ! -f "$lockfile" ]; then
            touch "$lockfile"
            mysql -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASS} -e "select * from console.region_info" || ./entrypoint.sh init && echo -e "\033[32;1mDatabase initialization completed\033[0m"
            python default_region.py
            #TODO: support  upgrade
            #python upgrade.py
            rm -rf "$lockfile"
        else
            echo "Database is already initializing."
        fi
        exec gunicorn goodrain_web.wsgi -b 0.0.0.0:${PORT:-7070} --max-requests=5000 -k gevent --reload --debug --workers=4 --log-file - --access-logfile - --error-logfile -
    else
        echo -e "\033[32;1mDatabase not ready\033[0m"
        exit 1
    fi
fi
