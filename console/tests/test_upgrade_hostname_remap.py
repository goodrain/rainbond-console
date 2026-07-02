# -*- coding: utf-8 -*-
"""Tests for hostname remap during template upgrade.

On install, k8s_service_name collisions are resolved by suffixing the name
(e.g. api-tpl -> api-tpl-cfd0). When the app is later upgraded, the template
still carries the raw template hostnames. AppUpgrade must rewrite the template
to the installed names before computing the diff/apply, otherwise the upgrade
would revert inner-env host values and config-file content back to the raw
template names that no longer exist in the namespace.
"""
import collections
import os
import sys
import typing
from types import ModuleType
from unittest.mock import MagicMock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))
if not hasattr(typing, "NotRequired"):
    try:
        from typing_extensions import NotRequired
        typing.NotRequired = NotRequired  # type: ignore[attr-defined]
    except ImportError:
        typing.NotRequired = lambda item: item  # type: ignore[attr-defined]

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.db.models.query import QuerySet  # noqa: E402

if not hasattr(QuerySet, "__class_getitem__"):
    QuerySet.__class_getitem__ = classmethod(lambda cls, item: cls)  # type: ignore[assignment]

from console.services.market_app.app_upgrade import AppUpgrade  # noqa: E402


class _Port(object):
    def __init__(self, container_port, k8s_service_name):
        self.container_port = container_port
        self.k8s_service_name = k8s_service_name


def _make_component(service_key, ports):
    cpt = MagicMock()
    cpt.component.service_key = service_key
    cpt.ports = ports
    return cpt


def _port_tmpl(k8s_name, container_port):
    return {"k8s_service_name": k8s_name, "container_port": container_port}


class BuildInstallRemapTests:

    def test_collision_builds_remap(self):
        original = [
            _make_component("api-svc", [_Port(5001, "api-tpl-cfd0")]),
            _make_component("db-svc", [_Port(5432, "db-postgres-tpl-de98")]),
        ]
        app_template = {
            "apps": [
                {"service_key": "api-svc", "port_map_list": [_port_tmpl("api-tpl", 5001)]},
                {"service_key": "db-svc", "port_map_list": [_port_tmpl("db-postgres-tpl", 5432)]},
            ]
        }

        remap = AppUpgrade._build_install_remap(original, app_template)

        assert remap == {"api-tpl": "api-tpl-cfd0", "db-postgres-tpl": "db-postgres-tpl-de98"}

    def test_no_collision_empty_remap(self):
        original = [_make_component("api-svc", [_Port(5001, "api-tpl")])]
        app_template = {
            "apps": [
                {"service_key": "api-svc", "port_map_list": [_port_tmpl("api-tpl", 5001)]},
            ]
        }

        remap = AppUpgrade._build_install_remap(original, app_template)

        assert remap == {}

    def test_no_apps_empty_remap(self):
        assert AppUpgrade._build_install_remap([], {}) == {}

    def test_unmatched_template_skipped(self):
        original = [_make_component("api-svc", [_Port(5001, "api-tpl-cfd0")])]
        app_template = {
            "apps": [
                {"service_key": "other-svc", "port_map_list": [_port_tmpl("other-tpl", 9000)]},
            ]
        }

        assert AppUpgrade._build_install_remap(original, app_template) == {}

    def test_missing_port_skipped(self):
        original = [_make_component("api-svc", [_Port(5001, "api-tpl-cfd0")])]
        app_template = {
            "apps": [
                {"service_key": "api-svc", "port_map_list": [_port_tmpl("api-tpl", 9999)]},
            ]
        }

        assert AppUpgrade._build_install_remap(original, app_template) == {}


class ApplyInstallRemapToTemplateTests:

    def test_collision_rewrites_template_in_place(self):
        original = [
            _make_component("api-svc", [_Port(5001, "api-tpl-cfd0")]),
            _make_component("db-svc", [_Port(5432, "db-postgres-tpl-de98")]),
        ]
        app_template = {
            "apps": [
                {
                    "service_key": "api-svc",
                    "port_map_list": [_port_tmpl("api-tpl", 5001)],
                    "service_env_map_list": [{"attr_name": "DB_HOST", "attr_value": "db-postgres-tpl"}],
                    "service_connect_info_map_list": [],
                    "service_volume_map_list": [{
                        "volume_type": "config-file",
                        "volume_name": "nginx-conf",
                        "file_content": "proxy_pass http://api-tpl:5001;",
                    }],
                },
                {
                    "service_key": "db-svc",
                    "port_map_list": [_port_tmpl("db-postgres-tpl", 5432)],
                    "service_env_map_list": [],
                    "service_connect_info_map_list": [],
                    "service_volume_map_list": [],
                },
            ]
        }

        remap = AppUpgrade._build_install_remap(original, app_template)
        AppUpgrade._apply_install_remap_to_template(app_template, remap)

        api_app = app_template["apps"][0]
        assert api_app["service_env_map_list"][0]["attr_value"] == "db-postgres-tpl-de98"
        assert api_app["service_volume_map_list"][0]["file_content"] == "proxy_pass http://api-tpl-cfd0:5001;"

    def test_no_collision_is_noop(self):
        original = [_make_component("api-svc", [_Port(5001, "api-tpl")])]
        app_template = {
            "apps": [
                {
                    "service_key": "api-svc",
                    "port_map_list": [_port_tmpl("api-tpl", 5001)],
                    "service_env_map_list": [{"attr_name": "DB_HOST", "attr_value": "db-postgres-tpl"}],
                    "service_connect_info_map_list": [],
                    "service_volume_map_list": [{
                        "volume_type": "config-file",
                        "volume_name": "nginx-conf",
                        "file_content": "proxy_pass http://api-tpl:5001;",
                    }],
                },
            ]
        }

        remap = AppUpgrade._build_install_remap(original, app_template)
        AppUpgrade._apply_install_remap_to_template(app_template, remap)

        api_app = app_template["apps"][0]
        assert remap == {}
        assert api_app["service_env_map_list"][0]["attr_value"] == "db-postgres-tpl"
        assert api_app["service_volume_map_list"][0]["file_content"] == "proxy_pass http://api-tpl:5001;"

    def test_empty_remap_skips_template(self):
        app_template = {
            "apps": [
                {"service_key": "api-svc", "service_env_map_list": [{"attr_name": "X", "attr_value": "api-tpl"}]},
            ]
        }
        AppUpgrade._apply_install_remap_to_template(app_template, {})
        assert app_template["apps"][0]["service_env_map_list"][0]["attr_value"] == "api-tpl"

    def test_connect_info_remapped(self):
        remap = {"api-tpl": "api-tpl-cfd0"}
        app_template = {
            "apps": [
                {
                    "service_key": "api-svc",
                    "service_connect_info_map_list": [{"attr_name": "API_URL", "attr_value": "http://api-tpl:5001"}],
                },
            ]
        }
        AppUpgrade._apply_install_remap_to_template(app_template, remap)
        assert app_template["apps"][0]["service_connect_info_map_list"][0]["attr_value"] == "http://api-tpl-cfd0:5001"
