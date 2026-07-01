# -*- coding: utf-8 -*-
"""Tests for collect_install_hostname_remap and apply_hostname_remap."""
import collections
import os
import sys
import typing
from types import ModuleType
from unittest.mock import patch

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

from console.exception.bcode import ErrK8sServiceNameExists  # noqa: E402
from console.services.app_config.port_service import AppPortService  # noqa: E402
from console.services.market_app.utils import apply_hostname_remap, collect_install_hostname_remap  # noqa: E402


def _port(name, container_port=5432):
    return {"k8s_service_name": name, "container_port": container_port}


def _env(name, value):
    return {"attr_name": name, "attr_value": value, "name": name, "is_change": True}


def _app(ports=None, inner=None, outer=None, volumes=None):
    return {
        "port_map_list": ports or [],
        "service_env_map_list": inner or [],
        "service_connect_info_map_list": outer or [],
        "service_volume_map_list": volumes or [],
    }


class CollectInstallHostnameRemapTests:

    def test_collision_builds_remap_and_updates_port(self):
        apps = [_app(ports=[_port("db-postgres-tpl")])]

        with patch.object(
                AppPortService, "check_k8s_service_name",
                side_effect=ErrK8sServiceNameExists):
            remap = collect_install_hostname_remap("tenant1", apps)

        assert len(remap) == 1
        assert "db-postgres-tpl" in remap
        new_name = remap["db-postgres-tpl"]
        assert new_name.startswith("db-postgres-tpl-")
        assert len(new_name) == len("db-postgres-tpl-") + 4
        assert apps[0]["port_map_list"][0]["k8s_service_name"] == new_name

    def test_no_collision_returns_empty(self):
        apps = [_app(ports=[_port("db-postgres")])]

        with patch.object(AppPortService, "check_k8s_service_name"):
            remap = collect_install_hostname_remap("tenant1", apps)

        assert remap == {}
        assert apps[0]["port_map_list"][0]["k8s_service_name"] == "db-postgres"

    def test_empty_apps(self):
        assert collect_install_hostname_remap("t", []) == {}
        assert collect_install_hostname_remap("t", None) == {}  # type: ignore[arg-type]

    def test_same_name_across_apps_reuses_remap(self):
        apps = [
            _app(ports=[_port("shared-svc", 8080)]),
            _app(ports=[_port("shared-svc", 9090)]),
        ]

        with patch.object(
                AppPortService, "check_k8s_service_name",
                side_effect=ErrK8sServiceNameExists) as mock_check:
            remap = collect_install_hostname_remap("tenant1", apps)

        assert len(remap) == 1
        new_name = remap["shared-svc"]
        assert apps[0]["port_map_list"][0]["k8s_service_name"] == new_name
        assert apps[1]["port_map_list"][0]["k8s_service_name"] == new_name
        mock_check.assert_called_once()

    def test_multiple_ports_multiple_collisions(self):
        apps = [_app(ports=[_port("api-tpl", 5001), _port("redis-tpl", 6379)])]

        with patch.object(
                AppPortService, "check_k8s_service_name",
                side_effect=ErrK8sServiceNameExists):
            remap = collect_install_hostname_remap("tenant1", apps)

        assert len(remap) == 2
        assert "api-tpl" in remap
        assert "redis-tpl" in remap
        assert apps[0]["port_map_list"][0]["k8s_service_name"] == remap["api-tpl"]
        assert apps[0]["port_map_list"][1]["k8s_service_name"] == remap["redis-tpl"]

    def test_mixed_collision_and_no_collision(self):
        apps = [_app(ports=[_port("collides", 80), _port("unique-name", 443)])]

        def selective_check(tenant_id, name):
            if name == "collides":
                raise ErrK8sServiceNameExists
        with patch.object(
                AppPortService, "check_k8s_service_name",
                side_effect=selective_check):
            remap = collect_install_hostname_remap("tenant1", apps)

        assert len(remap) == 1
        assert "collides" in remap
        assert apps[0]["port_map_list"][0]["k8s_service_name"] == remap["collides"]
        assert apps[0]["port_map_list"][1]["k8s_service_name"] == "unique-name"

    def test_empty_k8s_service_name_skipped(self):
        apps = [_app(ports=[{"k8s_service_name": "", "container_port": 80}])]

        with patch.object(
                AppPortService, "check_k8s_service_name") as mock_check:
            remap = collect_install_hostname_remap("tenant1", apps)

        assert remap == {}
        mock_check.assert_not_called()


class ApplyHostnameRemapTests:

    def test_remaps_inner_env_exact_match(self):
        apps = [_app(inner=[_env("DB_HOST", "db-postgres-tpl")])]
        apply_hostname_remap(apps, {"db-postgres-tpl": "db-postgres-tpl-a1b2"})
        assert apps[0]["service_env_map_list"][0]["attr_value"] == "db-postgres-tpl-a1b2"

    def test_remaps_url_embedded_hostname(self):
        apps = [_app(inner=[_env("BROKER", "redis://redis-tpl:6379/1")])]
        apply_hostname_remap(apps, {"redis-tpl": "redis-tpl-c3d4"})
        assert apps[0]["service_env_map_list"][0]["attr_value"] == "redis://redis-tpl-c3d4:6379/1"

    def test_remaps_config_file_content(self):
        nginx_conf = "location / { proxy_pass http://api-tpl:5001; }\nlocation /v1 { proxy_pass http://api-tpl/v1; }"
        apps = [_app(volumes=[{"file_content": nginx_conf, "volume_name": "nginx"}])]
        apply_hostname_remap(apps, {"api-tpl": "api-tpl-e5f6"})
        result = apps[0]["service_volume_map_list"][0]["file_content"]
        assert "http://api-tpl-e5f6:5001" in result
        assert "http://api-tpl-e5f6/v1" in result

    def test_empty_remap_is_noop(self):
        apps = [_app(inner=[_env("X", "foo")])]
        apply_hostname_remap(apps, {})
        assert apps[0]["service_env_map_list"][0]["attr_value"] == "foo"

    def test_skips_non_string_values(self):
        apps = [_app(inner=[_env("PORT", 5432)])]
        apply_hostname_remap(apps, {"db-postgres": "db-postgres-xxxx"})
        assert apps[0]["service_env_map_list"][0]["attr_value"] == 5432

    def test_remaps_connect_info_envs(self):
        apps = [_app(outer=[_env("HOST", "db-postgres-tpl")])]
        apply_hostname_remap(apps, {"db-postgres-tpl": "db-postgres-tpl-a1b2"})
        assert apps[0]["service_connect_info_map_list"][0]["attr_value"] == "db-postgres-tpl-a1b2"

    def test_remaps_hostname_port_without_scheme(self):
        apps = [_app(inner=[_env("BROKER", "redis-tpl:6379")])]
        apply_hostname_remap(apps, {"redis-tpl": "redis-tpl-c3d4"})
        assert apps[0]["service_env_map_list"][0]["attr_value"] == "redis-tpl-c3d4:6379"

    def test_none_apps_safe(self):
        apply_hostname_remap(None, {"x": "y"})  # type: ignore[arg-type]
        apply_hostname_remap([None, None], {"x": "y"})

    def test_multiple_remaps_in_single_value(self):
        apps = [_app(volumes=[{
            "file_content": "proxy_pass http://api-tpl:5001;\nproxy_pass http://db-tpl:5432;",
            "volume_name": "nginx",
        }])]
        apply_hostname_remap(apps, {"api-tpl": "api-tpl-aaaa", "db-tpl": "db-tpl-bbbb"})
        content = apps[0]["service_volume_map_list"][0]["file_content"]
        assert "http://api-tpl-aaaa:5001" in content
        assert "http://db-tpl-bbbb:5432" in content
