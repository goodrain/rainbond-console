#!/usr/bin/env bash

export MYSQL_PASS=9e67fedf
export MYSQL_PORT=20053
export MEMCACHED_PORT=11211
export PYTHONUNBUFFERED=1
export MYSQL_USER=admin
export MEMCACHED_HOST=127.0.0.1
export REGION_TAG=test_ali
export MYSQL_DB=console
export MYSQL_HOST=gr8d5d72.goodrain.ali-hz-s1.goodrain.net
export DEBUG=True
python manage.py runserver 0.0.0.0:8000
