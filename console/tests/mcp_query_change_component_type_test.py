# -*- coding: utf-8 -*-
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

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.mcp_query_service import mcp_query_service  # noqa: E402


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MCPQueryChangeComponentTypeTests(SimpleTestCase):
    """agent 全程通过 MCP 操作集群, 而 ElasticSearch / ZooKeeper / Kafka / Nacos 这类
    集群模板必须是有状态组件(才能拿到 headless Service 和每个 pod 自己的稳定地址)。
    REST 层的 ChangeServiceTypeView 一直都在, 缺的只是 MCP 工具层的封装。
    """
    def setUp(self):
        self.user = Obj(
            user_id=1,
            pk=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        self.user.get_username = lambda: self.user.nick_name

        self.team = Obj(
            ID=11,
            tenant_id="team-1",
            tenant_name="demo-team",
            tenant_alias="Demo Team",
            enterprise_id="eid-1",
            namespace="default",
            creater=1,
        )
        self.app = Obj(ID=12, tenant_id="team-1", group_name="demo-app", region_name="rainbond")
        self.service = Obj(
            service_id="svc-1",
            tenant_id="team-1",
            service_region="rainbond",
            service_alias="alias-1",
            service_cname="nacos",
            create_status="complete",
            extend_method="stateless_multiple",
            min_node=3,
        )
        self.service.save = lambda: None
        self.region = Obj(region_name="rainbond", enterprise_id="eid-1")

        patchers = [
            patch(
                "console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name",
                return_value=self.team),
            patch(
                "console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name",
                return_value=self.region),
            patch("console.services.mcp_query_service.group_service.get_app_by_id", return_value=self.app),
            patch("console.services.mcp_query_service.service_repo.get_service_by_service_id", return_value=self.service),
            patch(
                "console.services.mcp_query_service.group_service_relation_repo.get_services_by_group",
                return_value=[Obj(service_id="svc-1")]),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_tool_is_registered(self):
        tool = next(tool for tool in mcp_query_service.list_tools(self.user) if tool["name"] == "rainbond_change_component_type")
        self.assertIn("state_multiple", tool["inputSchema"]["properties"]["extend_method"]["enum"])
        self.assertEqual(["team_name", "region_name", "app_id", "service_id", "extend_method"],
                         tool["inputSchema"]["required"])

    # capability_id: console.component.change-type
    @patch("console.services.mcp_query_service.app_manage_service.change_service_type")
    def test_change_component_type_to_state_multiple(self, mock_change):
        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_change_component_type",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "extend_method": "state_multiple",
            },
        )

        self.assertTrue(result["changed"])
        self.assertEqual("svc-1", result["service_id"])
        self.assertEqual("stateless_multiple", result["old_extend_method"])
        self.assertEqual("state_multiple", result["extend_method"])
        mock_change.assert_called_once_with(self.team, self.service, "state_multiple", "admin")

    @patch("console.services.mcp_query_service.app_manage_service.change_service_type")
    def test_unsupported_component_type_is_rejected(self, mock_change):
        with self.assertRaises(ServiceHandleException):
            mcp_query_service.call_tool(
                self.user,
                "rainbond_change_component_type",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "service_id": "svc-1",
                    "extend_method": "not_a_type",
                },
            )

        mock_change.assert_not_called()

    @patch("console.services.mcp_query_service.app_manage_service.change_service_type")
    def test_extend_method_is_required(self, mock_change):
        with self.assertRaises(ServiceHandleException):
            mcp_query_service.call_tool(
                self.user,
                "rainbond_change_component_type",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "service_id": "svc-1",
                },
            )

        mock_change.assert_not_called()
