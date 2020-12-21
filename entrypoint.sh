#!/bin/bash

RED='\033[0;31m'
GREEN='\033[32;1m'
NC='\033[0m' # No Color

function database_ready() {
    if [ "${DB_TYPE}" == "mysql" ]; then
        if mysql -h${MYSQL_HOST:-127.0.0.1} -P${MYSQL_PORT:-3306} -u${MYSQL_USER} -p${MYSQL_PASS} -e "use console;" >/dev/null; then
            return 0 # 0 = true
        fi
        return 1 # 1 = false
    fi
    return 0
}

if [ "$1" = "debug" -o "$1" = "bash" ]; then
    exec /bin/bash
elif [ "$1" = "version" ]; then
    echo "${RELEASE_DESC}"
else
    if ! (database_ready); then
        echo -e "${RED}Database not ready${NC}"
        exit 1
    fi

    echo -e "${GREEN}Start initializing database${NC}"
    if ! (python manage.py makemigrations www 2>/dev/null); then
        echo -e "${RED}failed to makemigrations www${NC}"
        exit 1
    fi
    if ! (python manage.py makemigrations console 2>/dev/null); then
        echo -e "${RED}failed to makemigrations console${NC}"
        exit 1
    fi
    if ! (python manage.py migrate >/dev/null); then
        echo -e "${RED}failed to migrate${NC}"
        exit 1
    fi

    echo -e "${GREEN}Database initialization completed${NC}"

    # python upgrade.py
    exec gunicorn goodrain_web.wsgi -b 0.0.0.0:${PORT:-7070} --max-requests=5000 -k gevent --reload --workers=4 --timeout=75 --log-file - --access-logfile - --error-logfile -
fi
