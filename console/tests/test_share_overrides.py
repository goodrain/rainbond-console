# -*- coding: utf-8 -*-
"""Tests for _apply_share_overrides: merge env overrides into full component data."""
import collections
import os
import sys
import typing
from types import ModuleType

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

from console.services.app_version_service import AppVersionService  # noqa: E402


def _svc(svc_id, svc_key, cname, envs=None):
    return {
        "service_id": svc_id,
        "service_key": svc_key,
        "service_cname": cname,
        "image": "test:latest",
        "share_image": "internal:latest",
        "service_env_map_list": envs or [],
        "service_connect_info_map_list": [],
        "port_map_list": [],
        "dep_service_map_list": [],
    }


def _env(name, value):
    return {"attr_name": name, "attr_value": value, "name": name, "is_change": True}


class TestApplyShareOverrides:

    def test_override_replaces_matching_env(self):
        services = [_svc("s1", "k1", "api", [_env("SECRET", "old"), _env("MODE", "api")])]
        overrides = [{"service_key": "k1", "service_env_map_list": [_env("SECRET", "**None**")]}]
        result = AppVersionService._apply_share_overrides(services, overrides)
        envs = {e["attr_name"]: e["attr_value"] for e in result[0]["service_env_map_list"]}
        assert envs["SECRET"] == "**None**"
        assert envs["MODE"] == "api"

    def test_non_overridden_components_unchanged(self):
        services = [
            _svc("s1", "k1", "api", [_env("SECRET", "old")]),
            _svc("s2", "k2", "redis", [_env("PORT", "6379")]),
        ]
        overrides = [{"service_key": "k1", "service_env_map_list": [_env("SECRET", "new")]}]
        result = AppVersionService._apply_share_overrides(services, overrides)
        assert result[1]["service_env_map_list"][0]["attr_value"] == "6379"

    def test_preserves_all_component_fields(self):
        services = [_svc("s1", "k1", "api", [_env("X", "1")])]
        overrides = [{"service_key": "k1", "service_env_map_list": [_env("X", "2")]}]
        result = AppVersionService._apply_share_overrides(services, overrides)
        assert result[0]["service_cname"] == "api"
        assert result[0]["image"] == "test:latest"
        assert result[0]["share_image"] == "internal:latest"
        assert result[0]["port_map_list"] == []

    def test_override_by_service_id(self):
        services = [_svc("s1", "k1", "api", [_env("KEY", "old")])]
        overrides = [{"service_id": "s1", "service_env_map_list": [_env("KEY", "new")]}]
        result = AppVersionService._apply_share_overrides(services, overrides)
        envs = {e["attr_name"]: e["attr_value"] for e in result[0]["service_env_map_list"]}
        assert envs["KEY"] == "new"

    def test_override_adds_new_env(self):
        services = [_svc("s1", "k1", "api", [_env("EXISTING", "v1")])]
        overrides = [{"service_key": "k1", "service_env_map_list": [_env("NEW_VAR", "v2")]}]
        result = AppVersionService._apply_share_overrides(services, overrides)
        envs = {e["attr_name"]: e["attr_value"] for e in result[0]["service_env_map_list"]}
        assert envs["EXISTING"] == "v1"
        assert envs["NEW_VAR"] == "v2"

    def test_empty_overrides(self):
        services = [_svc("s1", "k1", "api", [_env("X", "1")])]
        result = AppVersionService._apply_share_overrides(services, [])
        assert result == services

    def test_does_not_mutate_input(self):
        import copy
        services = [_svc("s1", "k1", "api", [_env("X", "old")])]
        original = copy.deepcopy(services)
        overrides = [{"service_key": "k1", "service_env_map_list": [_env("X", "new")]}]
        AppVersionService._apply_share_overrides(services, overrides)
        assert services == original

    def test_multiple_overrides(self):
        services = [
            _svc("s1", "k1", "api", [_env("SECRET", "old"), _env("DB_PW", "old")]),
            _svc("s2", "k2", "db", [_env("PG_PW", "old")]),
        ]
        overrides = [
            {"service_key": "k1", "service_env_map_list": [
                _env("SECRET", "**None:secret**"),
                _env("DB_PW", "**None:db_pw**"),
            ]},
            {"service_key": "k2", "service_env_map_list": [
                _env("PG_PW", "**None:db_pw**"),
            ]},
        ]
        result = AppVersionService._apply_share_overrides(services, overrides)
        api_envs = {e["attr_name"]: e["attr_value"] for e in result[0]["service_env_map_list"]}
        db_envs = {e["attr_name"]: e["attr_value"] for e in result[1]["service_env_map_list"]}
        assert api_envs["SECRET"] == "**None:secret**"
        assert api_envs["DB_PW"] == "**None:db_pw**"
        assert db_envs["PG_PW"] == "**None:db_pw**"

    def test_component_count_preserved(self):
        services = [_svc("s%d" % i, "k%d" % i, "c%d" % i) for i in range(9)]
        overrides = [{"service_key": "k3", "service_env_map_list": [_env("X", "Y")]}]
        result = AppVersionService._apply_share_overrides(services, overrides)
        assert len(result) == 9
