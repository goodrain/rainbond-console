#!/bin/bash

RED='\033[0;31m'
GREEN='\033[32;1m'
YELLOW='\033[33;1m'
NC='\033[0m' # No Color

function database_empty() {
  # Check if database is empty
  if [ "${DB_TYPE}" == "mysql" ]; then
    tables=$(mysql -h"${MYSQL_HOST:-127.0.0.1}" -P"${MYSQL_PORT:-3306}" -u"${MYSQL_USER}" -p"${MYSQL_PASS}" -D"${MYSQL_DB}" -e "SHOW TABLES;" 2>/dev/null | wc -l)
    if [ "$tables" -le 1 ]; then
      return 0 # Database is empty
    fi
    return 1 # Database is not empty
  else
    tables=$(sqlite3 /app/data/db.sqlite3 "SELECT count(*) FROM sqlite_master WHERE type='table';")
    if [ "$tables" -eq 0 ]; then
      return 0 # Database is empty
    fi
    return 1 # Database is not empty
  fi
}

function init_database() {
  # Wait for database to be ready
  if [ "${DB_TYPE}" == "mysql" ]; then
    while true; do
      if mysql -h"${MYSQL_HOST:-127.0.0.1}" -P"${MYSQL_PORT:-3306}" -u"${MYSQL_USER}" -p"${MYSQL_PASS}" -e "use ${MYSQL_DB};" >/dev/null; then
        break
      else
        echo -e "${RED}ERROR: Database not ready, will waiting${NC}"
        sleep 3
      fi
    done
  else
    sqlite3 /app/data/db.sqlite3 "PRAGMA journal_mode = WAL;"
  fi

  # Initialize database schema
  echo -e "${GREEN}INFO: Start initializing database${NC}"
  if ! (python manage.py makemigrations www 2>/dev/null); then
    echo -e "${RED}ERROR: failed to makemigrations www${NC}"
    exit 1
  fi
  if ! (python manage.py makemigrations console 2>/dev/null); then
    echo -e "${RED}ERROR: failed to makemigrations console${NC}"
    exit 1
  fi
  if ! (python manage.py migrate >/dev/null); then
    echo -e "${RED}ERROR: failed to migrate${NC}"
    exit 1
  fi
  echo -e "${GREEN}INFO: Database initialization completed${NC}"

  # Initialize default region data
  if [ "${DB_TYPE}" == "mysql" ]; then
    if ! (python default_region.py 2> /dev/null); then
      echo -e "${RED}ERROR: failed to default_region${NC}"
      exit 1
    fi
  else
    if ! (python default_region_sqlite.py 2> /dev/null); then
      echo -e "${YELLOW}WARN: failed to default_region${NC}"
    fi
  fi
}

if [ "$1" = "debug" -o "$1" = "bash" ]; then
  exec /bin/bash
elif [ "$1" = "version" ]; then
  echo "${RELEASE_DESC}"
else
  if (database_empty); then
    init_database
  fi
  # python upgrade.py
  exec gunicorn goodrain_web.wsgi -b 0.0.0.0:${PORT:-7070} --max-requests=5000 -k gevent --reload --workers=2 --timeout=75 --log-file - --access-logfile - --error-logfile -
fi
