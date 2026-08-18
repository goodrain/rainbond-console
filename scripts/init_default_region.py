#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create the built-in region through Django's configured database backend."""

import os
import sys
import uuid


REGION_NAME = "rainbond"
REGION_SSL_DIR = "/app/region/ssl"


def make_uuid():
    return uuid.uuid4().hex


def read_required_file(path):
    with open(path, encoding="utf-8") as file_object:
        return file_object.read()


def get_default_region_text():
    if os.environ.get("DB_TYPE", "sqlite3") == "mysql":
        return "默认集群", "当前集群是默认安装添加的集群"
    return "Built-in Cluster", "The current cluster is the default built-in cluster"


def get_default_region_data():
    region_alias, description = get_default_region_text()
    return {
        "region_id": make_uuid(),
        "region_alias": region_alias,
        "url": os.environ.get("REGION_URL"),
        "status": "1",
        "desc": description,
        "wsurl": "ws://rbd-api-websocket:6060",
        "httpdomain": os.environ.get("REGION_HTTP_DOMAIN"),
        "tcpdomain": os.environ.get("REGION_TCP_DOMAIN"),
        "scope": "default",
        "ssl_ca_cert": read_required_file(os.path.join(REGION_SSL_DIR, "ca.pem")),
        "cert_file": read_required_file(os.path.join(REGION_SSL_DIR, "client.pem")),
        "key_file": read_required_file(os.path.join(REGION_SSL_DIR, "client.key.pem")),
    }


def get_region_model():
    repository_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
    import django

    django.setup()

    from console.models.main import RegionConfig

    return RegionConfig


def initialize_default_region(region_model=None):
    region_model = region_model or get_region_model()
    if region_model.objects.exists():
        return False

    _, created = region_model.objects.get_or_create(region_name=REGION_NAME, defaults=get_default_region_data())
    return created


def main():
    if initialize_default_region():
        print("Initialized default region")
    else:
        print("Default region already exists")


if __name__ == "__main__":
    main()
