#!/bin/bash

if [ "$1" = "debug" -o "$1" = "bash" ];then
    exec /bin/bash
elif [ "$1" = "version" ];then
    echo ${RELEASE_DESC}
else
    if [ ! -f "/initdata/.inited" ];then
        echo "init db"
        python /app/ui/manage.py migrate && touch /initdata/.inited
    fi  
    exec gunicorn goodrain_web.wsgi -b 0.0.0.0:${PORT:-7070} --max-requests=5000 -k gevent --reload --debug --workers=4 --log-file - --access-logfile - --error-logfile -
fi
