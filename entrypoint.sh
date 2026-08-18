#!/bin/bash

RED='\033[0;31m'
GREEN='\033[32;1m'
YELLOW='\033[33;1m'
NC='\033[0m' # No Color

function database_empty() {
  python scripts/database_state.py empty
}

function wait_for_database() {
  while ! python scripts/database_state.py ready; do
    echo -e "${RED}ERROR: Database not ready, will waiting${NC}"
    sleep 3
  done
}

function init_database() {
  # Wait for database to be ready
  wait_for_database
  if [ "${DB_TYPE:-sqlite3}" == "sqlite3" ]; then
    if ! python scripts/database_state.py sqlite-wal; then
      echo -e "${RED}ERROR: failed to enable SQLite WAL mode${NC}"
      exit 1
    fi
  fi

  # Initialize database schema
  echo -e "${GREEN}INFO: Start initializing database${NC}"
  if ! python manage.py makemigrations www; then
    echo -e "${RED}ERROR: failed to makemigrations www${NC}"
    exit 1
  fi
  if ! python manage.py makemigrations console; then
    echo -e "${RED}ERROR: failed to makemigrations console${NC}"
    exit 1
  fi
  if ! python manage.py repair_legacy_schema --apps authtoken,www,console; then
    echo -e "${RED}ERROR: failed to repair legacy schema${NC}"
    exit 1
  fi
  if ! python manage.py migrate --fake-initial --noinput; then
    echo -e "${RED}ERROR: failed to migrate${NC}"
    exit 1
  fi
  echo -e "${GREEN}INFO: Database initialization completed${NC}"
}

function init_region() {
  init_database
  # Initialize default region data
  if ! python scripts/init_default_region.py; then
    echo -e "${RED}ERROR: failed to initialize default region${NC}"
    exit 1
  fi
}

if [ "$1" = "debug" -o "$1" = "bash" ]; then
  exec /bin/bash
elif [ "$1" = "version" ]; then
  echo "${RELEASE_DESC}"
else
  if (database_empty); then
    init_region
  else
    init_database
  fi
  # python upgrade.py
  exec gunicorn goodrain_web.wsgi -b 0.0.0.0:${PORT:-7070} --max-requests=${MAX_REQUESTS:-5000} -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker --workers=${WORKERS:-4} --timeout=75 --log-file - --access-logfile - --error-logfile -
fi
