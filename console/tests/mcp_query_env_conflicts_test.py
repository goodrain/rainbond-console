# -*- coding: utf-8 -*-
"""Service-level tests for the analyze_env_conflicts MCP tool.

Detects the same env attr_name supplied by more than one source (component
self-define vs dependency-injected) and/or with diverging values — the M0
<ALIAS>_PORT 412 collision class. Backed by
env_var_service.get_all_envs_incloud_depend_env, mocked here.
"""
import os
import sys
from types import ModuleType
from unittest.mock import patch

import django
from django.test import SimpleTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
django.setup()

from console.services.mcp_query_service import mcp_query_service


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _team():
    return Obj(tenant_name="team1", tenant_id="tid-1", enterprise_id="eid-1")


def _app():
    return Obj(ID=7, region_name="rg")


def _service():
    return Obj(service_id="svc-self", service_alias="gr1234", service_region="rg", tenant_id="tid-1")


def _env(attr_name, attr_value, service_id, scope="inner"):
    return Obj(attr_name=attr_name, attr_value=attr_value, service_id=service_id,
               scope=scope, name=attr_name, container_port=0)


class EnvConflictTests(SimpleTestCase):

    # capability_id: console.mcp.env-conflicts
    def test_same_name_diff_value_is_conflict(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-self"}
        envs = [_env("SANDBOX_PORT", "8194", "svc-self"),
                _env("SANDBOX_PORT", "9999", "svc-self")]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.env_var_service.get_all_envs_incloud_depend_env",
                       return_value=iter(envs)):
                result = mcp_query_service.analyze_env_conflicts(Obj(nick_name="t"), args)
        self.assertEqual(result["total"], 1)
        c = result["conflicts"][0]
        self.assertEqual(c["attr_name"], "SANDBOX_PORT")
        self.assertEqual(len(c["sources"]), 2)

    # capability_id: console.mcp.env-conflicts
    def test_self_vs_dependency_cross_source_conflict(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-self"}
        envs = [_env("DB_HOST", "db-postgres", "svc-self"),
                _env("DB_HOST", "old-host", "svc-dep")]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.env_var_service.get_all_envs_incloud_depend_env",
                       return_value=iter(envs)):
                result = mcp_query_service.analyze_env_conflicts(Obj(nick_name="t"), args)
        self.assertEqual(result["total"], 1)
        origins = {s["origin"] for s in result["conflicts"][0]["sources"]}
        self.assertEqual(origins, {"self", "dependency"})

    # capability_id: console.mcp.env-conflicts
    def test_same_name_same_value_not_conflict(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-self"}
        envs = [_env("REDIS_HOST", "redis", "svc-self"),
                _env("REDIS_HOST", "redis", "svc-dep")]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.env_var_service.get_all_envs_incloud_depend_env",
                       return_value=iter(envs)):
                result = mcp_query_service.analyze_env_conflicts(Obj(nick_name="t"), args)
        # identical value from two sources is harmless: not flagged
        self.assertEqual(result["total"], 0)

    # capability_id: console.mcp.env-conflicts
    def test_sensitive_value_is_masked_but_conflict_still_flagged(self):
        # A SECRET_KEY/DB_PASSWORD conflict must still be reported, but the raw
        # secret values must NOT leak into the AI-facing response.
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-self"}
        envs = [_env("DB_PASSWORD", "supersecret-A", "svc-self"),
                _env("DB_PASSWORD", "supersecret-B", "svc-dep")]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.env_var_service.get_all_envs_incloud_depend_env",
                       return_value=iter(envs)):
                result = mcp_query_service.analyze_env_conflicts(Obj(nick_name="t"), args)
        self.assertEqual(result["total"], 1)
        values = [s["value"] for s in result["conflicts"][0]["sources"]]
        self.assertEqual(values, ["***", "***"])
        joined = str(result)
        self.assertNotIn("supersecret-A", joined)
        self.assertNotIn("supersecret-B", joined)

    # capability_id: console.mcp.env-conflicts
    def test_no_conflict_unique_names(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7", "service_id": "svc-self"}
        envs = [_env("A", "1", "svc-self"), _env("B", "2", "svc-self")]
        with patch.object(mcp_query_service, "_get_team_app_service_context",
                          return_value=(_team(), _app(), _service())):
            with patch("console.services.mcp_query_service.env_var_service.get_all_envs_incloud_depend_env",
                       return_value=iter(envs)):
                result = mcp_query_service.analyze_env_conflicts(Obj(nick_name="t"), args)
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(result["total"], 0)


class EnvConflictRegistrationTests(SimpleTestCase):
    # capability_id: console.mcp.env-conflicts
    def test_tool_is_listed_and_dispatchable(self):
        user = Obj(user_id=1, enterprise_id="eid-1", nick_name="u", is_enterprise_admin=False)
        names = [t["name"] for t in mcp_query_service.list_tools(user)]
        self.assertIn("rainbond_analyze_env_conflicts", names)
