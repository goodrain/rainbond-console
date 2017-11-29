#!/bin/bash
if [ "$1" = "bash" ];then
    exec /bin/bash
elif [ "$1" = "version" ];then
    echo ${RELEASE_DESC}
else
    ./console_app -b 0.0.0.0:${PORT:-7070} --max-requests=5000 --reload --debug --workers=4 --log-file - --access-logfile - --error-logfile -
fi
