#!/bin/bash
if [ $1 = "openshell" ];then
    exec /bin/bash
elif [ $1 = "version" ];then
    echo $RELEASE_TAG
else
    gunicorn goodrain_web.wsgi --max-requests=5000 --reload --debug --workers=4 --log-file - --access-logfile - --error-logfile -
fi
