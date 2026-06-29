# -*- coding: utf-8 -*-
"""Tests for resolve_none_placeholders: in-place **None** / **None:group** secret resolution."""
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

from console.services.market_app.utils import resolve_none_placeholders  # noqa: E402


def _env(name, value):
    return {"attr_name": name, "attr_value": value, "name": name, "is_change": True}


def _app(svc_key, inner=None, outer=None):
    return {
        "service_key": svc_key,
        "service_env_map_list": inner if inner is not None else [],
        "service_connect_info_map_list": outer if outer is not None else [],
    }


def _values(apps):
    out = {}
    for app in apps:
        for key in ("service_env_map_list", "service_connect_info_map_list"):
            for env in app.get(key) or []:
                out[(app["service_key"], key, env["attr_name"])] = env["attr_value"]
    return out


class ResolveNonePlaceholdersTests:

    def test_grouped_secret_shared_across_components(self):
        apps = [
            _app("db", [_env("POSTGRES_PASSWORD", "**None:db_password**")]),
            _app("api", [_env("DB_PASSWORD", "**None:db_password**")]),
            _app("worker", outer=[_env("DB_PASSWORD", "**None:db_password**")]),
        ]
        resolve_none_placeholders(apps)
        vals = _values(apps)
        pg = vals[("db", "service_env_map_list", "POSTGRES_PASSWORD")]
        api = vals[("api", "service_env_map_list", "DB_PASSWORD")]
        worker = vals[("worker", "service_connect_info_map_list", "DB_PASSWORD")]
        # all replaced and identical across components
        assert pg == api == worker
        assert pg != "**None:db_password**"
        assert pg

    def test_different_groups_get_different_values(self):
        apps = [
            _app("a", [_env("DB_PW", "**None:db_password**"), _env("REDIS_PW", "**None:redis_password**")]),
        ]
        resolve_none_placeholders(apps)
        vals = _values(apps)
        db = vals[("a", "service_env_map_list", "DB_PW")]
        redis = vals[("a", "service_env_map_list", "REDIS_PW")]
        assert db != redis
        assert db and redis

    def test_ungrouped_none_gets_random_and_may_differ(self):
        apps = [
            _app("a", [_env("SECRET1", "**None**"), _env("SECRET2", "**None**")]),
        ]
        resolve_none_placeholders(apps)
        vals = _values(apps)
        s1 = vals[("a", "service_env_map_list", "SECRET1")]
        s2 = vals[("a", "service_env_map_list", "SECRET2")]
        assert s1 != "**None**"
        assert s2 != "**None**"
        # independent random values -> almost certainly differ
        assert s1 != s2

    def test_non_placeholder_values_untouched(self):
        apps = [
            _app("a", [_env("MODE", "production"), _env("EMPTY", ""), _env("HOST", "db.svc")]),
        ]
        resolve_none_placeholders(apps)
        vals = _values(apps)
        assert vals[("a", "service_env_map_list", "MODE")] == "production"
        assert vals[("a", "service_env_map_list", "EMPTY")] == ""
        assert vals[("a", "service_env_map_list", "HOST")] == "db.svc"

    def test_empty_and_missing_env_lists_safe(self):
        apps = [
            _app("a"),
            {"service_key": "b"},  # missing both env keys
            None,  # defensive: None app
        ]
        # should not raise
        resolve_none_placeholders(apps)
        # empty input safe too
        resolve_none_placeholders([])
        resolve_none_placeholders(None)  # type: ignore[arg-type]

    def test_non_string_attr_value_safe(self):
        # Some template envs carry non-string attr_value (e.g. an int); the
        # resolver must skip them instead of raising 'int has no attribute startswith'.
        apps = [_app("a", [
            _env("PORT", 5432),
            _env("PG", "**None:db_password**"),
        ])]
        resolve_none_placeholders(apps)  # must not raise
        vals = _values(apps)
        assert vals[("a", "service_env_map_list", "PORT")] == 5432
        assert vals[("a", "service_env_map_list", "PG")] != "**None:db_password**"

    def test_resolved_values_contain_no_none_marker(self):
        apps = [
            _app("db", [_env("PG", "**None:db_password**")]),
            _app("api", [_env("S", "**None**")], outer=[_env("DB", "**None:db_password**")]),
        ]
        resolve_none_placeholders(apps)
        for value in _values(apps).values():
            assert "**None" not in value
