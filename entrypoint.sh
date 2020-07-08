#!/bin/bash

RED='\033[0;31m'
GREEN='\033[32;1m'
NC='\033[0m' # No Color

function database_ready(){
    if mysql -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASS} -e "use console;" > /dev/null; then
        return 0 # 0 = true
    fi
    return 1 # 1 = false
}

if [ "$1" = "debug" -o "$1" = "bash" ];then
    exec /bin/bash
elif [ "$1" = "version" ];then
    echo ${RELEASE_DESC}
elif [ "$1" = "init" ];then
    if !(database_ready);then
        echo -e "${RED}Database not ready${NC}"
        exit 1
    fi

    if mysql -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASS} -e "select * from console.region_info" 2> /dev/null; then
        echo -e "${GREEN}Database already initiated${NC}"
        exit 0
    fi

    echo -e "${GREEN}Start initializing database${NC}"
    python manage.py makemigrations www
    python manage.py makemigrations console
    python manage.py migrate
    python default_region.py
    echo -e "${GREEN}Database initialization completed${NC}"
else
    # check database
    if !(database_ready);then
        echo -e "${RED}Database not ready${NC}"
        exit 1
    fi
    
    #TODO: support  upgrade
    # python upgrade.py
    exec gunicorn goodrain_web.wsgi -b 0.0.0.0:${PORT:-7070} --max-requests=5000 -k gevent --reload --debug --workers=4 --timeout=120 --log-file - --access-logfile - --error-logfile -
fi
