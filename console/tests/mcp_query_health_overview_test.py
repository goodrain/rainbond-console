# -*- coding: utf-8 -*-
"""Service-level tests for the get_app_health_overview MCP tool.

One batched status_multi_service call gives every component's status;
only non-running components are deep-dived (pod warnings + classify).
region_api / repos are mocked so no live region is needed.
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


class _Svc(object):
    def __init__(self, sid, cname, k8s):
        self.service_id = sid
        self.service_cname = cname
        self.k8s_component_name = k8s
        self.service_alias = "gr" + sid
        self.service_region = "rg"

    def to_dict(self):
        return {"service_id": self.service_id, "service_cname": self.service_cname,
                "k8s_component_name": self.k8s_component_name}


class HealthOverviewTests(SimpleTestCase):

    # capability_id: console.mcp.app-health-overview
    def test_all_running_no_blocker_no_deepdive(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7"}
        services = [_Svc("a", "api", "api"), _Svc("b", "db", "db-postgres")]
        status_list = [{"service_id": "a", "status": "running"},
                       {"service_id": "b", "status": "running"}]
        with patch.object(mcp_query_service, "_get_team_app_context",
                          return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.group_service.get_group_services",
                       return_value=services):
                with patch("console.services.mcp_query_service.base_service.status_multi_service",
                           return_value=status_list):
                    with patch.object(mcp_query_service, "_collect_pod_warnings") as deep:
                        result = mcp_query_service.get_app_health_overview(Obj(nick_name="t"), args)
        # all running => app_status running, no per-component deep-dive at all
        self.assertEqual(result["app_status"], "running")
        deep.assert_not_called()
        blockers = {c["service_id"]: c["critical_blocker"] for c in result["components"]}
        self.assertEqual(blockers, {"a": None, "b": None})
        self.assertEqual(result["total"], 2)

    # capability_id: console.mcp.app-health-overview
    def test_abnormal_component_deepdived_for_blocker(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7"}
        services = [_Svc("a", "api", "api"), _Svc("b", "db", "db-postgres")]
        status_list = [{"service_id": "a", "status": "running"},
                       {"service_id": "b", "status": "abnormal"}]
        warnings = [{"reason": "ImagePullBackOff", "message": "Back-off pulling image"}]
        with patch.object(mcp_query_service, "_get_team_app_context",
                          return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.group_service.get_group_services",
                       return_value=services):
                with patch("console.services.mcp_query_service.base_service.status_multi_service",
                           return_value=status_list):
                    with patch.object(mcp_query_service, "_collect_pod_warnings",
                                      return_value=warnings) as deep:
                        result = mcp_query_service.get_app_health_overview(Obj(nick_name="t"), args)
        # only the abnormal component is deep-dived
        self.assertEqual(deep.call_count, 1)
        self.assertEqual(result["app_status"], "part_running")
        blockers = {c["service_id"]: c["critical_blocker"] for c in result["components"]}
        self.assertIsNone(blockers["a"])
        self.assertEqual(blockers["b"], "image_pull_failed")

    # capability_id: console.mcp.app-health-overview
    def test_deepdive_failure_degrades_to_unknown(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7"}
        services = [_Svc("b", "db", "db-postgres")]
        status_list = [{"service_id": "b", "status": "abnormal"}]
        with patch.object(mcp_query_service, "_get_team_app_context",
                          return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.group_service.get_group_services",
                       return_value=services):
                with patch("console.services.mcp_query_service.base_service.status_multi_service",
                           return_value=status_list):
                    with patch.object(mcp_query_service, "_collect_pod_warnings",
                                      side_effect=Exception("region down")):
                        result = mcp_query_service.get_app_health_overview(Obj(nick_name="t"), args)
        # deep-dive failure must not break aggregation
        self.assertEqual(result["components"][0]["critical_blocker"], "unknown")

    # capability_id: console.mcp.app-health-overview
    def test_empty_app(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7"}
        with patch.object(mcp_query_service, "_get_team_app_context",
                          return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.group_service.get_group_services",
                       return_value=[]):
                result = mcp_query_service.get_app_health_overview(Obj(nick_name="t"), args)
        self.assertEqual(result["components"], [])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["app_status"], "closed")


class HealthOverviewRegistrationTests(SimpleTestCase):

    # capability_id: console.mcp.app-health-overview
    def test_tool_is_listed_and_dispatchable(self):
        user = Obj(user_id=1, enterprise_id="eid-1", nick_name="u", is_enterprise_admin=False)
        names = [t["name"] for t in mcp_query_service.list_tools(user)]
        self.assertIn("rainbond_get_app_health_overview", names)
