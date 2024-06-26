#!/bin/bash

RED='\033[0;31m'
GREEN='\033[32;1m'
NC='\033[0m' # No Color

function database_ready() {
    if [ "${DB_TYPE}" == "mysql" ]; then
        if mysql -h${MYSQL_HOST:-127.0.0.1} -P${MYSQL_PORT:-3306} -u${MYSQL_USER} -p${MYSQL_PASS} -e "use ${MYSQL_DB};" >/dev/null; then
            return 0 # 0 = true
        fi
        return 1 # 1 = false
    fi
    sqlite3 /app/data/db.sqlite3 <<EOF
PRAGMA journal_mode = WAL;
EOF
    return 0
}

function init_database() {
    for i in {1..4}; do
        if ! (database_ready); then
            echo -e "${RED}Database not ready, will waiting${NC}"
            sleep 3
        else
            break
        fi
    done
    if ! (database_ready); then
        echo -e "${RED}Database not ready, will exit.${NC}"
        return 1
    fi

    echo -e "${GREEN}Start initializing database${NC}"
    if ! (python manage.py makemigrations www 2>/dev/null); then
        echo -e "${RED}failed to makemigrations www${NC}"
        return 1
    fi
    if ! (python manage.py makemigrations console 2>/dev/null); then
        echo -e "${RED}failed to makemigrations console${NC}"
        return 1
    fi
    if ! (python manage.py migrate >/dev/null); then
        echo -e "${RED}failed to migrate${NC}"
        return 1
    fi
    echo -e "${GREEN}Database initialization completed${NC}"
    return 0
}

use_sqlite() {
    # shellcheck disable=SC1035
    if !(python default_region_sqlite.py 2> /dev/null); then
      echo -e "${RED}failed to default_region${NC}"
      exit 1
    fi
}

use_mysql() {
    if !(python default_region.py 2> /dev/null); then
      echo -e "${RED}failed to default_region${NC}"
      exit 1
    fi
}

if [ "$1" = "debug" -o "$1" = "bash" ]; then
    exec /bin/bash
elif [ "$1" = "version" ]; then
    echo "${RELEASE_DESC}"
else
    if ! (init_database); then
      exit 1
    fi
    if [ "${INSTALL_TYPE}" != "allinone" ]; then
      if [ "$DB_TYPE" != "mysql" ]; then
        use_sqlite
      else
        use_mysql
      fi
    fi
    # python upgrade.py
    exec gunicorn goodrain_web.wsgi -b 0.0.0.0:${PORT:-7070} --max-requests=5000 -k gevent --reload --workers=2 --timeout=75 --log-file - --access-logfile - --error-logfile -
fi
