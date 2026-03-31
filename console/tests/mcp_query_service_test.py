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

from console.exception.main import ServiceHandleException
from console.services.mcp_query_service import mcp_query_service


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MCPQueryServiceToolVisibilityTests(SimpleTestCase):

    # capability_id: console.tool-visibility.enterprise-admin
    def test_list_tools_for_enterprise_admin_includes_region_and_enterprise_tools(self):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )

        tool_names = [tool["name"] for tool in mcp_query_service.list_tools(user)]

        self.assertIn("rainbond_get_current_user", tool_names)
        self.assertIn("rainbond_get_app_detail", tool_names)
        self.assertIn("rainbond_create_app", tool_names)
        self.assertIn("rainbond_get_component_summary", tool_names)
        self.assertIn("rainbond_get_component_detail", tool_names)
        self.assertIn("rainbond_get_component_logs", tool_names)
        self.assertNotIn("rainbond_get_component_events", tool_names)
        self.assertIn("rainbond_create_component", tool_names)
        self.assertIn("rainbond_delete_component", tool_names)
        self.assertIn("rainbond_operate_app", tool_names)
        self.assertIn("rainbond_manage_component_envs", tool_names)
        self.assertIn("rainbond_manage_component_connection_envs", tool_names)
        self.assertNotIn("rainbond_update_component_envs", tool_names)
        self.assertIn("rainbond_change_component_image", tool_names)
        self.assertIn("rainbond_manage_component_ports", tool_names)
        self.assertNotIn("rainbond_handle_component_ports", tool_names)
        self.assertNotIn("rainbond_bind_component_volume", tool_names)
        self.assertIn("rainbond_manage_component_storage", tool_names)
        self.assertIn("rainbond_manage_component_autoscaler", tool_names)
        self.assertIn("rainbond_manage_component_probe", tool_names)
        self.assertIn("rainbond_manage_component_dependency", tool_names)
        self.assertIn("rainbond_horizontal_scale_component", tool_names)
        self.assertIn("rainbond_vertical_scale_component", tool_names)
        self.assertIn("rainbond_close_apps", tool_names)
        self.assertIn("rainbond_get_team_apps", tool_names)
        self.assertIn("rainbond_build_component", tool_names)
        self.assertIn("rainbond_get_app_upgrade_info", tool_names)
        self.assertIn("rainbond_upgrade_app", tool_names)
        self.assertIn("rainbond_get_copy_app_info", tool_names)
        self.assertIn("rainbond_copy_app", tool_names)
        self.assertIn("rainbond_install_app_by_market", tool_names)
        self.assertIn("rainbond_create_component_from_source", tool_names)
        self.assertIn("rainbond_create_component_from_package", tool_names)
        self.assertNotIn("rainbond_check_component", tool_names)
        self.assertNotIn("rainbond_get_component_check_result", tool_names)
        self.assertIn("rainbond_create_component_from_image", tool_names)
        self.assertIn("rainbond_create_app_from_yaml", tool_names)
        self.assertIn("rainbond_check_yaml_app", tool_names)
        self.assertIn("rainbond_get_yaml_app_check_result", tool_names)
        self.assertIn("rainbond_query_app_monitor", tool_names)
        self.assertIn("rainbond_query_app_monitor_range", tool_names)
        self.assertIn("rainbond_create_gateway_rules", tool_names)
        self.assertIn("rainbond_check_helm_app", tool_names)
        self.assertIn("rainbond_build_helm_app", tool_names)
        self.assertIn("rainbond_query_regions", tool_names)
        self.assertIn("rainbond_get_region_detail", tool_names)
        self.assertIn("rainbond_create_region", tool_names)
        self.assertIn("rainbond_update_region", tool_names)
        self.assertIn("rainbond_delete_region", tool_names)
        self.assertIn("rainbond_query_region_nodes", tool_names)
        self.assertIn("rainbond_get_region_node_detail", tool_names)
        self.assertIn("rainbond_query_region_rbd_components", tool_names)
        self.assertIn("rainbond_query_enterprises", tool_names)
        self.assertIn("rainbond_query_teams", tool_names)
        self.assertIn("rainbond_query_apps", tool_names)
        self.assertIn("rainbond_query_components", tool_names)

    # capability_id: console.tool-visibility.standard-user
    def test_list_tools_for_non_enterprise_admin_hides_region_and_enterprise_tools(self):
        user = Obj(
            user_id=2,
            enterprise_id="eid-2",
            nick_name="developer",
            real_name="Dev User",
            email="dev@example.com",
            is_active=True,
            is_enterprise_admin=False,
        )

        tool_names = [tool["name"] for tool in mcp_query_service.list_tools(user)]

        self.assertIn("rainbond_get_current_user", tool_names)
        self.assertIn("rainbond_get_app_detail", tool_names)
        self.assertIn("rainbond_create_app", tool_names)
        self.assertIn("rainbond_get_component_summary", tool_names)
        self.assertIn("rainbond_get_component_detail", tool_names)
        self.assertIn("rainbond_get_component_logs", tool_names)
        self.assertNotIn("rainbond_get_component_events", tool_names)
        self.assertIn("rainbond_create_component", tool_names)
        self.assertIn("rainbond_delete_component", tool_names)
        self.assertIn("rainbond_operate_app", tool_names)
        self.assertIn("rainbond_manage_component_envs", tool_names)
        self.assertIn("rainbond_manage_component_connection_envs", tool_names)
        self.assertNotIn("rainbond_update_component_envs", tool_names)
        self.assertIn("rainbond_change_component_image", tool_names)
        self.assertIn("rainbond_manage_component_ports", tool_names)
        self.assertNotIn("rainbond_handle_component_ports", tool_names)
        self.assertNotIn("rainbond_bind_component_volume", tool_names)
        self.assertIn("rainbond_manage_component_storage", tool_names)
        self.assertIn("rainbond_manage_component_autoscaler", tool_names)
        self.assertIn("rainbond_manage_component_probe", tool_names)
        self.assertIn("rainbond_manage_component_dependency", tool_names)
        self.assertIn("rainbond_horizontal_scale_component", tool_names)
        self.assertIn("rainbond_vertical_scale_component", tool_names)
        self.assertIn("rainbond_close_apps", tool_names)
        self.assertIn("rainbond_get_team_apps", tool_names)
        self.assertIn("rainbond_build_component", tool_names)
        self.assertIn("rainbond_get_app_upgrade_info", tool_names)
        self.assertIn("rainbond_upgrade_app", tool_names)
        self.assertIn("rainbond_get_copy_app_info", tool_names)
        self.assertIn("rainbond_copy_app", tool_names)
        self.assertIn("rainbond_install_app_by_market", tool_names)
        self.assertIn("rainbond_create_component_from_source", tool_names)
        self.assertIn("rainbond_create_component_from_package", tool_names)
        self.assertNotIn("rainbond_check_component", tool_names)
        self.assertNotIn("rainbond_get_component_check_result", tool_names)
        self.assertIn("rainbond_create_component_from_image", tool_names)
        self.assertIn("rainbond_create_app_from_yaml", tool_names)
        self.assertIn("rainbond_check_yaml_app", tool_names)
        self.assertIn("rainbond_get_yaml_app_check_result", tool_names)
        self.assertIn("rainbond_query_app_monitor", tool_names)
        self.assertIn("rainbond_query_app_monitor_range", tool_names)
        self.assertIn("rainbond_create_gateway_rules", tool_names)
        self.assertIn("rainbond_check_helm_app", tool_names)
        self.assertIn("rainbond_build_helm_app", tool_names)
        self.assertNotIn("rainbond_query_regions", tool_names)
        self.assertNotIn("rainbond_get_region_detail", tool_names)
        self.assertNotIn("rainbond_create_region", tool_names)
        self.assertNotIn("rainbond_update_region", tool_names)
        self.assertNotIn("rainbond_delete_region", tool_names)
        self.assertNotIn("rainbond_query_region_nodes", tool_names)
        self.assertNotIn("rainbond_get_region_node_detail", tool_names)
        self.assertNotIn("rainbond_query_region_rbd_components", tool_names)
        self.assertNotIn("rainbond_query_enterprises", tool_names)
        self.assertIn("rainbond_query_teams", tool_names)
        self.assertIn("rainbond_query_apps", tool_names)
        self.assertIn("rainbond_query_components", tool_names)

    # capability_id: console.user.current-profile
    def test_get_current_user_returns_identity_and_enterprise_admin_flag(self):
        admin_user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        normal_user = Obj(
            user_id=2,
            enterprise_id="eid-2",
            nick_name="developer",
            real_name="Dev User",
            email="dev@example.com",
            is_active=True,
            is_enterprise_admin=False,
        )

        admin_result = mcp_query_service.call_tool(admin_user, "rainbond_get_current_user", {})
        normal_result = mcp_query_service.call_tool(normal_user, "rainbond_get_current_user", {})

        self.assertEqual(admin_result["user_id"], 1)
        self.assertEqual(admin_result["nick_name"], "admin")
        self.assertTrue(admin_result["is_enterprise_admin"])
        self.assertNotIn("is_platform_admin", admin_result)

        self.assertEqual(normal_result["user_id"], 2)
        self.assertEqual(normal_result["nick_name"], "developer")
        self.assertFalse(normal_result["is_enterprise_admin"])
        self.assertNotIn("is_platform_admin", normal_result)

    # capability_id: console.gateway.port-action-schema
    def test_handle_component_ports_tool_schema_exposes_action_enum(self):
        tool = mcp_query_service._tool_handle_component_ports()

        self.assertEqual(tool["name"], "rainbond_handle_component_ports")
        self.assertEqual(
            tool["inputSchema"]["properties"]["action"]["enum"],
            [
                "open_outer", "only_open_outer", "close_outer", "open_inner",
                "close_inner", "change_protocol", "change_port_alias"
            ],
        )

    # capability_id: console.gateway.operation-schema
    def test_manage_component_ports_tool_schema_exposes_operation_enum(self):
        tool = mcp_query_service._tool_manage_component_ports()

        self.assertEqual(tool["name"], "rainbond_manage_component_ports")
        self.assertIn("enable_inner", tool["inputSchema"]["properties"]["operation"]["enum"])
        self.assertIn("enable_outer", tool["inputSchema"]["properties"]["operation"]["enum"])
        self.assertIn("disable_inner", tool["inputSchema"]["properties"]["operation"]["enum"])
        self.assertIn("disable_outer", tool["inputSchema"]["properties"]["operation"]["enum"])
        self.assertIn("enable_outer_only", tool["inputSchema"]["properties"]["operation"]["enum"])
        self.assertIn("update_protocol", tool["inputSchema"]["properties"]["operation"]["enum"])
        self.assertIn("update_alias", tool["inputSchema"]["properties"]["operation"]["enum"])

    # capability_id: console.component.operation-aliases
    def test_normalize_component_operation_aliases(self):
        self.assertEqual(
            mcp_query_service._normalize_component_operation("list", {"list": "summary"}, ("summary",), "测试"),
            "summary",
        )
        with self.assertRaises(ServiceHandleException):
            mcp_query_service._normalize_component_operation("unknown", {"list": "summary"}, ("summary",), "测试")

    # capability_id: console.component.env-scope-default
    def test_normalize_env_scope_defaults_to_inner(self):
        self.assertEqual(mcp_query_service._normalize_env_scope(None), "inner")
        self.assertEqual(mcp_query_service._normalize_env_scope("local"), "inner")
        with self.assertRaises(ServiceHandleException):
            mcp_query_service._normalize_env_scope("connection")

    @patch("console.services.mcp_query_service.region_services.get_enterprise_regions")
    # capability_id: console.enterprise.region-list-authz
    # capability_id: console.enterprise.region-list
    def test_query_regions_requires_enterprise_admin(self, mock_get_regions):
        user = Obj(
            user_id=2,
            enterprise_id="eid-2",
            nick_name="developer",
            real_name="Dev User",
            email="dev@example.com",
            is_active=True,
            is_enterprise_admin=False,
        )

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(user, "rainbond_query_regions", {})

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.msg, "permission denied")
        self.assertIn("没有权限执行该操作", context.exception.msg_show)
        mock_get_regions.assert_not_called()

    @patch("console.services.mcp_query_service.region_services.get_enterprise_regions")
    # capability_id: console.enterprise.region-list
    def test_query_regions_returns_paginated_regions_for_enterprise_admin(self, mock_get_regions):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        region = Obj(
            region_id="r1",
            region_name="rainbond",
            region_alias="Rainbond Region",
            status="healthy",
            provider="local",
            create_time=None,
        )
        mock_get_regions.return_value = [region]

        result = mcp_query_service.call_tool(user, "rainbond_query_regions", {})

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["region_name"], "rainbond")
        self.assertEqual(result["items"][0]["region_alias"], "Rainbond Region")

    @patch("console.services.mcp_query_service.region_services.get_enterprise_regions")
    # capability_id: console.enterprise.region-list-authz
    # capability_id: console.enterprise.region-list
    def test_query_regions_rejects_cross_enterprise_access_for_enterprise_admin(self, mock_get_regions):
        user = Obj(
            user_id=3,
            enterprise_id="eid-3",
            nick_name="enterprise-admin",
            real_name="Enterprise Admin",
            email="ea@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(user, "rainbond_query_regions", {"enterprise_id": "eid-other"})

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.msg, "permission denied")
        self.assertIn("没有权限执行该操作", context.exception.msg_show)
        mock_get_regions.assert_not_called()

    @patch("console.services.mcp_query_service.region_services.get_region_by_region_id")
    # capability_id: console.enterprise.region-detail
    def test_get_region_detail_returns_region_data(self, mock_get_region):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        mock_get_region.return_value = Obj(
            region_id="r1",
            enterprise_id="eid-1",
            region_name="rainbond",
            region_alias="Rainbond Region",
            region_type='[]',
            url="https://region.example.com",
            token="token-1",
            wsurl="wss://region.example.com/ws",
            httpdomain="apps.example.com",
            tcpdomain="1.1.1.1",
            scope="private",
            ssl_ca_cert="ca",
            cert_file="cert",
            key_file="key",
            status="1",
            desc="region-desc",
            provider="",
            provider_cluster_id="",
            create_time=None,
        )

        result = mcp_query_service.call_tool(user, "rainbond_get_region_detail", {"region_id": "r1"})

        self.assertEqual(result["region_id"], "r1")
        self.assertEqual(result["region_name"], "rainbond")
        self.assertEqual(result["region_alias"], "Rainbond Region")
        self.assertEqual(result["url"], "https://region.example.com")

    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.enterprise_services.get_nodes")
    # capability_id: console.enterprise.region-node-list
    def test_query_region_nodes_returns_nodes_for_enterprise_admin(self, mock_get_nodes, mock_get_region):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_nodes.return_value = (
            [{"name": "node-1", "status": "Ready", "role": ["worker"], "arch": "amd64"}],
            {"worker": 1},
        )

        result = mcp_query_service.call_tool(user, "rainbond_query_region_nodes", {"region_name": "rainbond"})

        self.assertEqual(result["region_name"], "rainbond")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["nodes"][0]["name"], "node-1")
        self.assertEqual(result["cluster_role_count"]["worker"], 1)

    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.enterprise_services.get_node_detail")
    # capability_id: console.enterprise.region-node-detail
    def test_get_region_node_detail_returns_node_detail_for_enterprise_admin(self, mock_get_node_detail, mock_get_region):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_node_detail.return_value = {
            "name": "node-1",
            "status": "Ready",
            "ip": "10.0.0.1",
            "roles": ["worker"],
        }

        result = mcp_query_service.call_tool(
            user, "rainbond_get_region_node_detail", {"region_name": "rainbond", "node_name": "node-1"}
        )

        self.assertEqual(result["name"], "node-1")
        self.assertEqual(result["status"], "Ready")
        self.assertEqual(result["ip"], "10.0.0.1")

    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.enterprise_services.get_rbdcomponents")
    # capability_id: console.enterprise.region-component-list
    def test_query_region_rbd_components_returns_components_for_enterprise_admin(
            self, mock_get_components, mock_get_region):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_components.return_value = [{"name": "rbd-api", "status": "Running"}]

        result = mcp_query_service.call_tool(
            user, "rainbond_query_region_rbd_components", {"region_name": "rainbond"}
        )

        self.assertEqual(result["region_name"], "rainbond")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["name"], "rbd-api")


class MCPQueryServiceRegionMutationTests(SimpleTestCase):

    def setUp(self):
        self.user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )

    @patch("console.services.mcp_query_service.region_services.add_region")
    # capability_id: console.enterprise.region-create
    def test_create_region_executes_directly(self, mock_add_region):
        mock_add_region.return_value = Obj(
            region_id="r1",
            enterprise_id="eid-1",
            region_name="rainbond",
            region_alias="Rainbond Region",
            region_type='[]',
            url="https://region.example.com",
            token="",
            wsurl="wss://region.example.com/ws",
            httpdomain="apps.example.com",
            tcpdomain="1.1.1.1",
            scope="private",
            ssl_ca_cert="",
            cert_file="",
            key_file="",
            status="1",
            desc="",
            provider="",
            provider_cluster_id="",
            create_time=None,
        )

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_region",
            {
                "region_name": "rainbond",
                "region_alias": "Rainbond Region",
                "url": "https://region.example.com",
                "wsurl": "wss://region.example.com/ws",
                "httpdomain": "apps.example.com",
                "tcpdomain": "1.1.1.1",
            },
        )

        self.assertTrue(result["created"])
        self.assertEqual(result["region"]["region_name"], "rainbond")
        mock_add_region.assert_called_once()

    @patch("console.services.mcp_query_service.region_services.get_region_by_region_id")
    @patch("console.services.mcp_query_service.region_services.update_region")
    # capability_id: console.enterprise.region-update
    def test_update_region_executes_directly_with_merged_full_payload(self, mock_update_region, mock_get_region):
        mock_get_region.return_value = Obj(
            region_id="r1",
            enterprise_id="eid-1",
            region_name="rainbond",
            region_alias="Old Alias",
            region_type='[]',
            token="old-token",
            url="https://old-region.example.com",
            wsurl="wss://old-region.example.com/ws",
            httpdomain="old-apps.example.com",
            tcpdomain="2.2.2.2",
            scope="private",
            ssl_ca_cert="old-ca",
            cert_file="old-cert",
            key_file="old-key",
            status="1",
            desc="old-desc",
            provider="",
            provider_cluster_id="",
            create_time=None,
        )
        mock_update_region.return_value = Obj(
            region_id="r1",
            enterprise_id="eid-1",
            region_name="rainbond",
            region_alias="New Alias",
            region_type='[]',
            url="https://old-region.example.com",
            token="old-token",
            wsurl="wss://old-region.example.com/ws",
            httpdomain="old-apps.example.com",
            tcpdomain="2.2.2.2",
            scope="private",
            ssl_ca_cert="old-ca",
            cert_file="old-cert",
            key_file="old-key",
            status="1",
            desc="old-desc",
            provider="",
            provider_cluster_id="",
            create_time=None,
        )

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_update_region",
            {
                "region_id": "r1",
                "region_alias": "New Alias",
            },
        )

        self.assertTrue(result["updated"])
        self.assertEqual(result["region"]["region_alias"], "New Alias")
        mock_update_region.assert_called_once_with({
            "region_id": "r1",
            "region_name": "rainbond",
            "enterprise_id": "eid-1",
            "region_alias": "New Alias",
            "url": "https://old-region.example.com",
            "token": "old-token",
            "wsurl": "wss://old-region.example.com/ws",
            "httpdomain": "old-apps.example.com",
            "tcpdomain": "2.2.2.2",
            "scope": "private",
            "ssl_ca_cert": "old-ca",
            "cert_file": "old-cert",
            "key_file": "old-key",
            "status": "1",
            "desc": "old-desc",
        })

    @patch("console.services.mcp_query_service.region_services.get_region_by_region_id")
    @patch("console.services.mcp_query_service.region_services.del_by_region_id")
    # capability_id: console.enterprise.region-delete
    def test_delete_region_executes_directly(self, mock_delete_region, mock_get_region):
        mock_get_region.return_value = Obj(
            region_id="r1",
            enterprise_id="eid-1",
            region_name="rainbond",
            region_alias="Rainbond Region",
            region_type='[]',
            url="https://region.example.com",
            token="",
            wsurl="wss://region.example.com/ws",
            httpdomain="apps.example.com",
            tcpdomain="1.1.1.1",
            scope="private",
            ssl_ca_cert="",
            cert_file="",
            key_file="",
            status="1",
            desc="",
            provider="",
            provider_cluster_id="",
            create_time=None,
        )
        mock_delete_region.return_value = {
            "region_id": "r1",
            "enterprise_id": "eid-1",
            "region_name": "rainbond",
            "region_alias": "Rainbond Region",
            "status": "1",
        }

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_delete_region",
            {"region_id": "r1"},
        )

        self.assertTrue(result["deleted"])
        mock_delete_region.assert_called_once_with("r1")


class MCPQueryServiceApplicationToolTests(SimpleTestCase):

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

        def _get_username():
            return self.user.nick_name

        self.user.get_username = _get_username
        self.team = Obj(
            ID=11,
            tenant_id="team-1",
            tenant_name="demo-team",
            tenant_alias="Demo Team",
            enterprise_id="eid-1",
            namespace="default",
            creater=1,
        )
        self.app = Obj(
            ID=12,
            tenant_id="team-1",
            group_name="demo-app",
            region_name="rainbond",
            note="app-note",
            username="admin",
            governance_mode="KUBERNETES_NATIVE_SERVICE",
            create_time=None,
            update_time=None,
            app_type="rainbond",
            app_store_name="",
            app_store_url="",
            app_template_name="",
            version="",
            logo="",
            k8s_app="demo-k8s-app",
        )
        self.app.to_dict = lambda: {
            "ID": 12,
            "tenant_id": "team-1",
            "group_name": "demo-app",
            "region_name": "rainbond",
            "note": "app-note",
            "username": "admin",
            "governance_mode": "KUBERNETES_NATIVE_SERVICE",
            "app_type": "rainbond",
            "k8s_app": "demo-k8s-app",
        }
        self.service = Obj(
            service_id="svc-1",
            tenant_id="team-1",
            service_region="rainbond",
            service_alias="alias-1",
            service_cname="component-1",
            service_source="docker_image",
            create_status="complete",
            min_memory=128,
            min_node=1,
            image="nginx:1.25",
            version="1.25",
            arch="amd64",
        )
        self.service.to_dict = lambda: {
            "service_id": "svc-1",
            "tenant_id": "team-1",
            "service_region": "rainbond",
            "service_alias": "alias-1",
            "service_cname": "component-1",
            "service_source": "docker_image",
            "create_status": "complete",
            "min_memory": 128,
            "min_node": 1,
            "image": self.service.image,
            "version": self.service.version,
        }
        self.service.save = lambda: None
        self.plugin = Obj(category="analyst-plugin:perf")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.create_app")
    # capability_id: console.app.create
    def test_create_app_calls_group_service(self, mock_create_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_create_app.return_value = {"app_id": 12, "app_name": "demo-app", "group_id": 12}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_app",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_name": "demo-app",
                "app_note": "note",
            },
        )

        self.assertEqual(result["app_name"], "demo-app")
        mock_create_app.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.group_service.get_group_services")
    @patch("console.services.mcp_query_service.base_service.status_multi_service")
    # capability_id: console.app.detail
    def test_get_app_detail_returns_status_and_counts(
            self, mock_status_multi, mock_get_group_services, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_group_services.return_value = [self.service]
        mock_status_multi.return_value = [{"service_id": "svc-1", "status": "running"}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_detail",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12},
        )

        self.assertEqual(result["app_id"], 12)
        self.assertEqual(result["service_count"], 1)
        self.assertEqual(result["running_service_count"], 1)
        self.assertEqual(result["status"], "running")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.base_service.status_multi_service")
    @patch("console.services.mcp_query_service.domain_service.get_component_access_infos")
    @patch("console.services.mcp_query_service.port_service.get_service_ports")
    @patch("console.services.mcp_query_service.env_var_service.get_self_define_env")
    @patch("console.services.mcp_query_service.env_var_service.get_service_build_envs")
    @patch("console.services.mcp_query_service.volume_service.get_service_volumes")
    @patch("console.services.mcp_query_service.mnt_service.get_service_mnt_details")
    @patch("console.services.mcp_query_service.autoscaler_service.list_autoscaler_rules")
    @patch("console.services.mcp_query_service.probe_service.get_service_probe")
    @patch("console.services.mcp_query_service.event_service.get_target_events")
    @patch("console.services.mcp_query_service.region_api.get_service_resources")
    # capability_id: console.component.summary
    def test_get_component_summary_returns_aggregated_info(
            self,
            mock_get_resources,
            mock_get_events,
            mock_get_probe,
            mock_get_autoscaler_rules,
            mock_get_mnts,
            mock_get_volumes,
            mock_get_build_envs,
            mock_get_envs,
            mock_get_ports,
            mock_get_access_infos,
            mock_status_multi,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        self.service.language = "Python"
        self.service.min_cpu = 500
        self.service.extend_method = "stateless_multiple"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_status_multi.return_value = [{"service_id": "svc-1", "status": "running"}]
        mock_get_access_infos.return_value = [{"url": "http://demo.example.com"}]
        port = Obj(container_port=80, protocol="http")
        port.to_dict = lambda: {"container_port": 80, "protocol": "http"}
        mock_get_ports.return_value = [port]
        env = Obj(attr_name="APP_MODE", attr_value="prod")
        env.to_dict = lambda: {"attr_name": "APP_MODE", "attr_value": "prod"}
        build_env = Obj(attr_name="BUILD_TYPE", attr_value="cnb")
        build_env.to_dict = lambda: {"attr_name": "BUILD_TYPE", "attr_value": "cnb"}
        mock_get_envs.return_value = [env]
        mock_get_build_envs.return_value = [build_env]
        mock_get_volumes.return_value = [{"volume_name": "data", "status": "bound"}]
        mock_get_mnts.return_value = ([{"dep_vol_name": "shared-data"}], 1)
        mock_get_autoscaler_rules.return_value = [{"rule_id": "rule-1"}]
        probe = Obj()
        probe.to_dict = lambda: {"probe_id": "probe-1", "mode": "readiness"}
        mock_get_probe.return_value = (200, "success", probe)
        mock_get_events.return_value = ([{"event_id": "evt-1"}], 1, False)
        mock_get_resources.return_value = {"bean": {"svc-1": {"memory": 128, "cpu": 500, "disk": 1}}}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_summary",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"},
        )

        self.assertEqual(result["service"]["service_id"], "svc-1")
        self.assertEqual(result["status"]["status"], "running")
        self.assertEqual(result["ports"]["total"], 1)
        self.assertEqual(result["envs"]["total"], 1)
        self.assertEqual(result["build_envs"]["total"], 1)
        self.assertEqual(result["volumes"]["total"], 1)
        self.assertEqual(result["mnts"]["total"], 1)
        self.assertEqual(result["autoscaler_rules"]["total"], 1)
        self.assertEqual(result["recent_events"]["total"], 1)
        self.assertEqual(result["resource"]["memory"], 128)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.region_api.get_service_pods")
    @patch("console.services.mcp_query_service.region_api.get_component_pod_log")
    # capability_id: console.component.logs
    def test_get_component_logs_returns_component_logs(
            self,
            mock_get_logs,
            mock_get_service_pods,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        response = Obj()
        response.stream = lambda chunk_size: iter([b"data: line-1\n\n", b"data: line-2\n\n"])
        response.close = lambda: None
        response.release_conn = lambda: None
        self.service.k8s_component_name = "main"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_service_pods.return_value = {
            "bean": {
                "new_pods": [
                    {
                        "pod_name": "pod-1",
                        "pod_status": "RUNNING",
                        "container": {"POD": {}, "main": {}}
                    }
                ],
                "old_pods": None
            }
        }
        mock_get_logs.return_value = response

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "action": "service",
                "lines": 2,
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["items"][0], "line-1")
        self.assertEqual(result["fallback"]["pod_name"], "pod-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch.object(mcp_query_service, "_infer_component_log_target", return_value=("", ""))
    # capability_id: console.component.logs-no-instance
    def test_get_component_logs_rejects_when_no_runtime_instance_found(
            self,
            mock_infer_target,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_get_component_logs",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "service_id": "svc-1",
                    "action": "service",
                },
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.msg_show, "未找到可用的组件实例日志，请确认组件是否已运行")
        mock_infer_target.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.region_api.get_service_pods")
    @patch("console.services.mcp_query_service.region_api.get_component_pod_log")
    # capability_id: console.component.logs-fallback
    def test_get_component_logs_service_falls_back_to_first_pod_container(
            self,
            mock_get_component_log,
            mock_get_service_pods,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        response = Obj()
        response.stream = lambda chunk_size: iter([b"data: fallback-line-1\n\n", b"data: fallback-line-2\n\n"])
        response.close = lambda: None
        response.release_conn = lambda: None
        self.service.k8s_component_name = "go-demo-app"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_service_pods.return_value = {
            "bean": {
                "new_pods": [
                    {
                        "pod_name": "pod-1",
                        "pod_status": "RUNNING",
                        "container": {
                            "POD": {},
                            "go-demo-app": {}
                        }
                    }
                ],
                "old_pods": None
            }
        }
        mock_get_component_log.return_value = response

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "action": "service",
                "lines": 100,
            },
        )

        self.assertEqual(result["action"], "service")
        self.assertEqual(result["fallback"]["action"], "container")
        self.assertEqual(result["fallback"]["pod_name"], "pod-1")
        self.assertEqual(result["fallback"]["container_name"], "go-demo-app")
        self.assertEqual(result["items"][0], "fallback-line-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.region_api.get_service_pods")
    @patch("console.services.mcp_query_service.region_api.get_component_pod_log")
    # capability_id: console.component.logs-console-shape
    def test_get_component_logs_service_supports_console_style_pod_shape(
            self,
            mock_get_component_log,
            mock_get_service_pods,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        response = Obj()
        response.stream = lambda chunk_size: iter([b"data: console-shape-line\n\n"])
        response.close = lambda: None
        response.release_conn = lambda: None
        self.service.k8s_component_name = "gr5f202e"
        self.service.service_alias = "gr5f202e"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_service_pods.return_value = {
            "list": {
                "new_pods": [
                    {
                        "pod_name": "go-demo-app-gr5f202e-6996594955-8gpp6",
                        "pod_status": "RUNNING",
                        "manage_name": "manager",
                        "container": [
                            {
                                "container_name": "gr5f202e",
                                "memory_limit": 512,
                                "memory_usage": 2.52,
                                "usage_rate": 0.49
                            }
                        ]
                    }
                ],
                "old_pods": None
            }
        }
        mock_get_component_log.return_value = response

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "action": "service",
                "lines": 100,
            },
        )

        self.assertEqual(result["fallback"]["pod_name"], "go-demo-app-gr5f202e-6996594955-8gpp6")
        self.assertEqual(result["fallback"]["container_name"], "gr5f202e")
        self.assertEqual(result["items"][0], "console-shape-line")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.region_api.get_component_pod_log")
    # capability_id: console.component.logs-container
    def test_get_component_logs_returns_container_logs(
            self,
            mock_get_component_log,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        response = Obj()
        response.stream = lambda chunk_size: iter([b"data: log-line-1\n\n", b"data: log-line-2\n\n"])
        response.close = lambda: None
        response.release_conn = lambda: None
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_component_log.return_value = response

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "action": "container",
                "pod_name": "pod-1",
                "container_name": "main",
                "follow": False
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["action"], "container")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["items"][0], "log-line-1")

    # capability_id: console.component.logs-parse-sse
    def test_parse_component_log_line_handles_sse_prefix(self):
        self.assertEqual(mcp_query_service._parse_component_log_line("data: hello"), "hello")
        self.assertIsNone(mcp_query_service._parse_component_log_line("event: message"))
        self.assertIsNone(mcp_query_service._parse_component_log_line(""))

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.volume_service.get_service_support_volume_options")
    @patch("console.services.mcp_query_service.volume_service.get_service_volumes")
    @patch("console.services.mcp_query_service.mnt_service.get_service_mnt_details")
    # capability_id: console.component.storage-summary
    def test_manage_component_storage_summary_returns_storage_snapshot(
            self,
            mock_get_mnts,
            mock_get_volumes,
            mock_get_volume_options,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_volume_options.return_value = [{"volume_type": "local-path"}]
        mock_get_volumes.return_value = [{"volume_name": "data"}]
        mock_get_mnts.return_value = ([{"dep_vol_name": "shared-data"}], 1)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_storage",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "summary",
            },
        )

        self.assertEqual(result["volume_options"]["total"], 1)
        self.assertEqual(result["volumes"]["total"], 1)
        self.assertEqual(result["mnts"]["total"], 1)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.autoscaler_service.list_autoscaler_rules")
    @patch("console.services.mcp_query_service.scaling_records_service.list_scaling_records")
    # capability_id: console.component.autoscaler-summary
    def test_manage_component_autoscaler_summary_returns_rules_and_records(
            self,
            mock_list_records,
            mock_list_rules,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_list_rules.return_value = [{"rule_id": "rule-1"}]
        mock_list_records.return_value = {"list": [{"record_id": "record-1"}], "total": 1}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_autoscaler",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "summary",
            },
        )

        self.assertEqual(result["rules"]["total"], 1)
        self.assertEqual(result["records"]["total"], 1)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.probe_service.get_service_probe")
    @patch("console.services.mcp_query_service.probe_service.get_service_probe_by_mode")
    # capability_id: console.component.probe-summary
    def test_manage_component_probe_summary_returns_probe_snapshot(
            self,
            mock_get_probe_by_mode,
            mock_get_probe,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        probe = Obj(probe_id="probe-1", mode="readiness")
        probe.to_dict = lambda: {"probe_id": "probe-1", "mode": "readiness"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_probe.return_value = (200, "success", probe)
        mock_get_probe_by_mode.return_value = (200, "success", [{"readiness": True}, {"liveness": False}])

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_probe",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "summary",
            },
        )

        self.assertEqual(result["probe"]["probe_id"], "probe-1")
        self.assertEqual(len(result["mode_status"]), 2)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.dependency_service.get_service_dependencies")
    @patch("console.services.mcp_query_service.dependency_service.get_service_dependencies_reverse")
    @patch("console.services.mcp_query_service.dependency_service.get_undependencies")
    @patch("console.services.mcp_query_service.dependency_service.get_reverse_undependencies")
    @patch("console.services.mcp_query_service.group_service.get_services_group_name")
    @patch("console.services.mcp_query_service.port_service.get_service_ports")
    # capability_id: console.component.dependency-summary
    def test_manage_component_dependency_summary_returns_dependency_snapshot(
            self,
            mock_get_ports,
            mock_get_group_name,
            mock_get_reverse_undependencies,
            mock_get_undependencies,
            mock_get_reverse_dependencies,
            mock_get_dependencies,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        dep = Obj(service_id="svc-2", service_cname="dep-1", service_alias="dep-1")
        dep.to_dict = lambda: {"service_id": "svc-2", "service_cname": "dep-1", "service_alias": "dep-1"}
        port = Obj(container_port=6379)
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_dependencies.return_value = [dep]
        mock_get_reverse_dependencies.return_value = [dep]
        mock_get_undependencies.return_value = [dep]
        mock_get_reverse_undependencies.return_value = [dep]
        mock_get_group_name.return_value = {"svc-2": {"group_name": "demo-app", "group_id": 12}}
        mock_get_ports.return_value = [port]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_dependency",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "summary",
            },
        )

        self.assertEqual(result["dependencies"]["total"], 1)
        self.assertEqual(result["reverse_dependencies"]["total"], 1)
        self.assertEqual(result["available_dependencies"]["total"], 1)
        self.assertEqual(result["available_reverse_dependencies"]["total"], 1)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.env_var_service.get_service_inner_env")
    @patch("console.services.mcp_query_service.env_var_service.get_service_outer_env")
    @patch("console.services.mcp_query_service.env_var_service.get_service_build_envs")
    # capability_id: console.component.env-summary
    def test_manage_component_envs_summary_returns_env_snapshots(
            self,
            mock_get_build_envs,
            mock_get_outer_envs,
            mock_get_envs,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        env = Obj(attr_name="APP_MODE", attr_value="prod")
        env.to_dict = lambda: {"attr_name": "APP_MODE", "attr_value": "prod"}
        build_env = Obj(attr_name="BUILD_TYPE", attr_value="cnb")
        build_env.to_dict = lambda: {"attr_name": "BUILD_TYPE", "attr_value": "cnb"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_envs.return_value = [env]
        mock_get_outer_envs.return_value = []
        mock_get_build_envs.return_value = [build_env]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_envs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "summary",
            },
        )

        self.assertEqual(result["custom_envs"]["total"], 1)
        self.assertEqual(result["connection_envs"]["total"], 0)
        self.assertEqual(result["build_envs"]["total"], 1)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.env_var_service.add_service_env_var")
    # capability_id: console.component.env-create
    def test_manage_component_envs_create_defaults_scope_to_inner(
            self,
            mock_add_env,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        env = Obj(attr_name="user", attr_value="root")
        env.to_dict = lambda: {"attr_name": "user", "attr_value": "root", "scope": "inner"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_add_env.return_value = (200, "success", env)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_envs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "create",
                "attr_name": "user",
                "attr_value": "root",
            },
        )

        self.assertTrue(result["created"])
        self.assertEqual(mock_add_env.call_args[0][7], "inner")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.env_var_service.get_service_outer_env")
    # capability_id: console.component.connection-env-summary
    def test_manage_component_connection_envs_summary_returns_outer_envs(
            self,
            mock_get_outer_envs,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        env = Obj(attr_name="MYSQL_HOST", attr_value="db.default")
        env.to_dict = lambda: {"attr_name": "MYSQL_HOST", "attr_value": "db.default", "scope": "outer"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_outer_envs.return_value = [env]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_connection_envs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "summary",
            },
        )

        self.assertEqual(result["connection_envs"]["total"], 1)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.env_var_service.add_service_env_var")
    # capability_id: console.component.connection-env-create
    def test_manage_component_connection_envs_create_uses_outer_scope(
            self,
            mock_add_env,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        env = Obj(attr_name="MYSQL_HOST", attr_value="db.default")
        env.to_dict = lambda: {"attr_name": "MYSQL_HOST", "attr_value": "db.default", "scope": "outer"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_add_env.return_value = (200, "success", env)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_connection_envs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "create",
                "attr_name": "MYSQL_HOST",
                "attr_value": "db.default",
            },
        )

        self.assertTrue(result["created"])
        self.assertEqual(mock_add_env.call_args[0][7], "outer")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.env_var_service.get_service_inner_env")
    @patch("console.services.mcp_query_service.env_var_service.update_env_by_env_id")
    @patch("console.services.mcp_query_service.env_var_service.add_service_env_var")
    # capability_id: console.component.env-update
    def test_manage_component_envs_upsert_only_uses_inner_envs(
            self,
            mock_add_env,
            mock_update_env,
            mock_get_inner_envs,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        existing_env = Obj(ID=1, attr_name="EXISTING", name="existing", attr_value="old", is_change=True, scope="inner")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_inner_envs.side_effect = [[existing_env], [existing_env]]
        mock_update_env.return_value = (200, "success", existing_env)
        mock_add_env.return_value = (200, "success", Obj())

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_envs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "upsert",
                "envs": [
                    {"name": "EXISTING", "value": "new"},
                    {"name": "NEW_ENV", "value": "v2"}
                ],
            },
        )

        self.assertEqual(mock_update_env.call_args[0][2], "1")
        self.assertEqual(mock_add_env.call_args[0][7], "inner")
        self.assertEqual(result["service_id"], "svc-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch.object(mcp_query_service, "handle_component_ports")
    # capability_id: console.component.port-summary
    def test_manage_component_ports_summary_delegates_to_port_handler(
            self,
            mock_handle_ports,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_handle_ports.return_value = {"service_id": "svc-1", "items": [{"container_port": 80}], "total": 1}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "summary",
            },
        )

        self.assertEqual(result["ports"]["total"], 1)
        self.assertEqual(mock_handle_ports.call_args[0][1]["operation"], "list")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch.object(mcp_query_service, "handle_component_ports")
    # capability_id: console.component.port-open-inner
    def test_manage_component_ports_enable_inner_maps_to_open_inner(
            self,
            mock_handle_ports,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_handle_ports.return_value = {"container_port": 80}

        mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "enable_inner",
                "port": 80,
            },
        )

        self.assertEqual(mock_handle_ports.call_args[0][1]["operation"], "update")
        self.assertEqual(mock_handle_ports.call_args[0][1]["action"], "open_inner")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch.object(mcp_query_service, "handle_component_ports")
    # capability_id: console.component.port-open-outer-only
    def test_manage_component_ports_enable_outer_only_maps_to_only_open_outer(
            self,
            mock_handle_ports,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_handle_ports.return_value = {"container_port": 80}

        mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "enable_outer_only",
                "port": 80,
            },
        )

        self.assertEqual(mock_handle_ports.call_args[0][1]["action"], "only_open_outer")

    @patch("console.services.mcp_query_service.service_repo.get_services_by_service_ids")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.team_repo.get_user_tenant_by_name")
    @patch("console.services.mcp_query_service.enterprise_user_perm_repo.is_admin")
    @patch("console.services.mcp_query_service.enterprise_repo.get_enterprises_by_user_id")
    @patch("console.services.mcp_query_service.team_repo.get_team_by_team_id")
    @patch("console.services.mcp_query_service.group_repo.get_group_by_id")
    # capability_id: console.component.list
    def test_query_components_uses_existing_service_repo_method(
            self,
            mock_get_app,
            mock_get_team_by_team_id,
            mock_get_enterprises,
            mock_is_admin,
            mock_get_user_tenant,
            mock_get_relations,
            mock_get_services,
    ):
        app = Obj(ID=12, tenant_id="team-1", group_name="demo-app")
        tenant = self.team
        service = self.service
        mock_get_app.return_value = app
        mock_get_team_by_team_id.return_value = tenant
        mock_get_enterprises.return_value = [Obj(enterprise_id="eid-1")]
        mock_is_admin.return_value = True
        mock_get_user_tenant.return_value = tenant
        mock_get_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_services.return_value = [service]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_components",
            {
                "enterprise_id": "eid-1",
                "app_id": 12,
                "page": 1,
                "page_size": 20,
            },
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["service_id"], "svc-1")
        mock_get_services.assert_called_once_with(["svc-1"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.base_service.status_multi_service")
    @patch("console.services.mcp_query_service.domain_service.get_component_access_infos")
    # capability_id: console.component.detail
    def test_get_component_detail_returns_status_and_access_infos(
            self,
            mock_access_infos,
            mock_status_multi,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_status_multi.return_value = [{"service_id": "svc-1", "status": "running"}]
        mock_access_infos.return_value = ["https://demo.example.com"]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_detail",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"},
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["access_infos"], ["https://demo.example.com"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.event_service.get_target_events")
    # capability_id: console.component.events
    def test_get_component_events_returns_paginated_events(
            self, mock_events, mock_relations, mock_get_service, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_events.return_value = ([{"event_id": "evt-1"}], 1, False)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_events",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "page": 1,
                "page_size": 10,
            },
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["events"][0]["event_id"], "evt-1")
        self.assertFalse(result["has_next"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.console_app_service.create_docker_run_app")
    @patch("console.services.mcp_query_service.group_service.add_service_to_group")
    @patch("console.services.mcp_query_service.console_app_service.create_region_service")
    @patch("console.services.mcp_query_service.app_manage_service.deploy")
    # capability_id: console.component.create-from-image
    def test_create_component_calls_console_services(
            self,
            mock_deploy,
            mock_create_region_service,
            mock_add_service_to_group,
            mock_create_docker_run_app,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_create_docker_run_app.return_value = (200, "success", self.service)
        mock_add_service_to_group.return_value = (200, "success")
        mock_create_region_service.return_value = self.service
        mock_deploy.return_value = (200, "success", "evt-1")

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_component",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_cname": "component-1",
                "image": "nginx:latest",
                "is_deploy": True,
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["event_id"], "evt-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.app_manage_service.delete")
    # capability_id: console.component.delete
    def test_delete_component_calls_app_manage_delete(
            self,
            mock_delete,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_delete.return_value = (200, "success")

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_delete_component",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"},
        )

        self.assertTrue(result["deleted"])
        self.assertEqual(result["service_id"], "svc-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.app_manage_service.batch_operations")
    # capability_id: console.app.batch-component-operation
    def test_operate_app_calls_batch_operations(
            self, mock_batch_operations, mock_relations, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_batch_operations.return_value = [{"event_id": "evt-1"}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_operate_app",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "action": "stop"},
        )

        self.assertEqual(result["action"], "stop")
        self.assertEqual(result["service_ids"], ["svc-1"])
        self.assertEqual(result["result"][0]["event_id"], "evt-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    # capability_id: console.component.change-image
    def test_change_component_image_updates_service_fields(
            self, mock_relations, mock_get_service, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_change_component_image",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "image": "nginx:latest",
            },
        )

        self.assertEqual(result["image"], "nginx:latest")
        self.assertEqual(result["version"], "latest")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.get_service_ports")
    # capability_id: console.component.port-list
    def test_handle_component_ports_list_returns_ports(
            self,
            mock_get_ports,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        port = Obj(container_port=80, protocol="http", is_inner_service=True, is_outer_service=False)
        port.to_dict = lambda: {
            "container_port": 80,
            "protocol": "http",
            "is_inner_service": True,
            "is_outer_service": False,
        }
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_ports.return_value = [port]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_handle_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "list",
            },
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["container_port"], 80)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.component.port-open-public
    def test_handle_component_ports_alias_action_maps_to_standard_action(
            self,
            mock_manage_port,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        port = Obj(container_port=80, protocol="http", is_inner_service=True, is_outer_service=True)
        port.to_dict = lambda: {
            "container_port": 80,
            "protocol": "http",
            "is_inner_service": True,
            "is_outer_service": True,
        }
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_manage_port.return_value = (200, "success", port)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_handle_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "update",
                "port": 80,
                "action": "open_public",
            },
        )

        self.assertEqual(result["container_port"], 80)
        self.assertEqual(mock_manage_port.call_args[0][4], "open_outer")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.app_manage_service.horizontal_upgrade")
    # capability_id: console.component.horizontal-scale
    def test_horizontal_scale_component_calls_app_manage_service(
            self,
            mock_horizontal_upgrade,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_horizontal_scale_component",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "new_node": 3,
            },
        )

        self.assertTrue(result["scaled"])
        self.assertEqual(result["new_node"], 3)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.service_repo.get_tenant_region_services")
    @patch("console.services.mcp_query_service.app_manage_service.batch_action")
    # capability_id: console.app.close-all
    def test_close_apps_calls_batch_action(self, mock_batch_action, mock_get_services, mock_get_region, mock_get_team):
        services = [Obj(service_id="svc-1"), Obj(service_id="svc-2")]

        class FakeQuerySet(list):
            def values_list(self, key, flat=False):
                if key == "service_id" and flat:
                    return [item.service_id for item in self]
                return []

        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_services.return_value = FakeQuerySet(services)
        mock_batch_action.return_value = (200, "success", services)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_close_apps",
            {"team_name": "demo-team", "region_name": "rainbond"},
        )

        self.assertTrue(result["closed"])
        self.assertEqual(result["service_ids"], ["svc-1", "svc-2"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_apps_list")
    # capability_id: console.app.list-team-apps
    def test_get_team_apps_returns_app_list(self, mock_get_apps, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_apps.return_value = [self.app]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_team_apps",
            {"team_name": "demo-team", "region_name": "rainbond"},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["group_name"], "demo-app")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.market_app_service.get_market_apps_in_app")
    # capability_id: console.app-upgrade.info
    def test_get_app_upgrade_info_returns_upgrade_items(
            self, mock_get_upgrade_info, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_upgrade_info.return_value = [{"app_model_id": "m1", "can_upgrade": True}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_upgrade_info",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["app_model_id"], "m1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_service.openapi_upgrade_app_models")
    @patch("console.services.mcp_query_service.market_app_service.get_market_apps_in_app")
    # capability_id: console.app.upgrade
    def test_upgrade_app_calls_upgrade_service_and_returns_latest_items(
            self, mock_get_upgrade_info, mock_upgrade_app, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_upgrade_info.return_value = [{"app_model_id": "m1", "can_upgrade": False, "updated": True}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_upgrade_app",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "update_versions": [{"app_model_id": "m1", "version": "2.0.0"}],
            },
        )

        self.assertTrue(result["upgraded"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["app_model_id"], "m1")
        mock_upgrade_app.assert_called_once_with(
            self.user,
            self.team,
            "rainbond",
            None,
            12,
            {"update_versions": [{"app_model_id": "m1", "version": "2.0.0"}]},
        )

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.groupapp_copy_service.get_group_services_with_build_source")
    # capability_id: console.app.copy-info
    def test_get_copy_app_info_returns_services(
            self, mock_get_copy_info, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_copy_info.return_value = [{"service_id": "svc-1", "service_cname": "component-1"}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_copy_app_info",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["service_id"], "svc-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.groupapp_copy_service.check_and_get_team_group")
    @patch("console.services.mcp_query_service.groupapp_copy_service.copy_group_services")
    @patch("console.services.mcp_query_service.domain_service.get_components_that_contains_gateway_rules")
    # capability_id: console.app.copy
    def test_copy_app_returns_target_app_and_gateway_rules(
            self,
            mock_gateway_rules,
            mock_copy_services,
            mock_check_target,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        copied_service = Obj(
            service_id="svc-2",
            service_alias="alias-2",
            service_cname="component-2",
            gateway_rules={"http": [Obj(domain_name="demo.example.com")], "tcp": []},
        )
        copied_service.to_dict = lambda: {
            "service_id": "svc-2",
            "service_alias": "alias-2",
            "service_cname": "component-2",
        }
        target_team = Obj(tenant_name="target-team")
        target_group = Obj(ID=66, group_name="target-app")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_check_target.return_value = (target_team, target_group)
        mock_copy_services.return_value = [copied_service]
        mock_gateway_rules.return_value = [copied_service]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_copy_app",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "target_team_name": "target-team",
                "target_region_name": "target-region",
                "target_app_id": 66,
                "services": ["svc-1"],
            },
        )

        self.assertEqual(result["target_app_id"], 66)
        self.assertEqual(result["target_team_name"], "target-team")
        self.assertEqual(result["target_region_name"], "target-region")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["service_id"], "svc-2")
        self.assertEqual(result["items"][0]["gateway_rules"]["http"][0]["domain_name"], "demo.example.com")
        mock_check_target.assert_called_once_with(self.user, "target-team", "target-region", 66)
        mock_copy_services.assert_called_once_with(
            self.user, self.team, "rainbond", target_team, "target-region", target_group, 12, ["svc-1"]
        )

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    # capability_id: console.app.copy-services-guard
    def test_copy_app_rejects_non_list_services(
            self,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_copy_app",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "target_team_name": "target-team",
                    "target_region_name": "target-region",
                    "target_app_id": 66,
                    "services": "svc-1",
                },
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "参数services无效")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.app_market_service.get_app_market_by_domain_url")
    @patch("console.services.mcp_query_service.app_market_service.cloud_app_model_to_db_model")
    @patch("console.services.mcp_query_service.market_app_service.install_service")
    @patch("console.services.mcp_query_service.group_service.get_group_services")
    # capability_id: console.app.install-from-market
    def test_install_app_by_market_calls_market_service(
            self,
            mock_get_group_services,
            mock_install_service,
            mock_cloud_to_db,
            mock_get_market,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        market = Obj(name="market-1")
        market_app = Obj(app_id="model-1")
        market_version = Obj()
        installed_service = Obj(service_id="svc-1")
        installed_service.to_dict = lambda: {"service_id": "svc-1"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_market.return_value = market
        mock_cloud_to_db.return_value = (market_app, market_version)
        mock_get_group_services.return_value = [installed_service]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_install_app_by_market",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "market_url": "https://hub.grapps.cn",
                "market_domain": "rainbond",
                "market_type": "rainstore",
                "market_access_key": "ak",
                "app_model_id": "model-1",
                "app_model_version": "v1",
                "is_deploy": True,
            },
        )

        self.assertTrue(result["installed"])
        self.assertEqual(result["market_name"], "market-1")
        self.assertEqual(result["service_list"][0]["service_id"], "svc-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.service_repo.get_services_by_service_ids")
    @patch("console.services.mcp_query_service.app_plugin_service.get_service_abled_plugin")
    @patch("console.services.mcp_query_service.region_api.get_query_data")
    # capability_id: console.app.monitor-summary
    def test_query_app_monitor_returns_monitor_items(
            self,
            mock_query_data,
            mock_get_plugins,
            mock_get_services,
            mock_relations,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        class FakeQuerySet(list):
            def exclude(self, **kwargs):
                return self

        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_services.return_value = FakeQuerySet([self.service])
        mock_get_plugins.return_value = [self.plugin]
        mock_query_data.return_value = (None, {"data": {"result": [{"value": [1, 2]}]}})

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_app_monitor",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["service_id"], "svc-1")
        self.assertTrue(result["items"][0]["monitors"])

    # capability_id: console.app.monitor-summary-outer-only
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.service_repo.get_services_by_service_ids")
    @patch("console.services.mcp_query_service.app_plugin_service.get_service_abled_plugin")
    @patch("console.services.mcp_query_service.port_service.get_service_ports")
    def test_query_app_monitor_filters_to_outer_services_when_requested(
            self,
            mock_get_ports,
            mock_get_plugins,
            mock_get_services,
            mock_relations,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        class FakeQuerySet(list):
            def exclude(self, **kwargs):
                return self

        inner_only_port = Obj(container_port=80, protocol="http", is_outer_service=False)
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_services.return_value = FakeQuerySet([self.service])
        mock_get_plugins.return_value = [self.plugin]
        mock_get_ports.return_value = [inner_only_port]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_app_monitor",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "is_outer": True},
        )

        self.assertEqual(result["total"], 0)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.service_repo.get_services_by_service_ids")
    @patch("console.services.mcp_query_service.app_plugin_service.get_service_abled_plugin")
    @patch("console.services.mcp_query_service.region_api.get_query_range_data")
    # capability_id: console.app.monitor-range
    def test_query_app_monitor_range_returns_stringified_series(
            self,
            mock_query_range_data,
            mock_get_plugins,
            mock_get_services,
            mock_relations,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        class FakeQuerySet(list):
            def exclude(self, **kwargs):
                return self

        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_services.return_value = FakeQuerySet([self.service])
        mock_get_plugins.return_value = [self.plugin]
        mock_query_range_data.return_value = (
            None,
            {"data": {"result": [{"value": [[1710000000, "1"], [1710000060, "2"]]}]}},
        )

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_app_monitor_range",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "start": "1710000000",
                "end": "1710000600",
                "step": 120,
            },
        )

        self.assertEqual(result["app_id"], 12)
        self.assertEqual(result["start"], "1710000000")
        self.assertEqual(result["end"], "1710000600")
        self.assertEqual(result["step"], 120)
        self.assertEqual(result["total"], 1)
        self.assertTrue(result["items"][0]["monitors"])
        first_series = result["items"][0]["monitors"][0]["data"]["result"][0]["value"]
        self.assertEqual(first_series[0], "[1710000000, '1']")
        self.assertEqual(first_series[1], "[1710000060, '2']")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.service_repo.get_services_by_service_ids")
    @patch("console.services.mcp_query_service.app_plugin_service.get_service_abled_plugin")
    @patch("console.services.mcp_query_service.region_api.get_query_range_data")
    # capability_id: console.app.monitor-range-default-step
    def test_query_app_monitor_range_defaults_step_to_60(
            self,
            mock_query_range_data,
            mock_get_plugins,
            mock_get_services,
            mock_relations,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        class FakeQuerySet(list):
            def exclude(self, **kwargs):
                return self

        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_services.return_value = FakeQuerySet([self.service])
        mock_get_plugins.return_value = [self.plugin]
        mock_query_range_data.return_value = (None, {"data": {"result": []}})

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_app_monitor_range",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "start": "1710000000",
                "end": "1710000600",
            },
        )

        self.assertEqual(result["step"], 60)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.domain_service.check_domain_exist")
    @patch("console.services.mcp_query_service.port_service.get_service_port_by_port")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    @patch("console.services.mcp_query_service.domain_service.bind_httpdomain")
    @patch("console.services.mcp_query_service.region_api.api_gateway_bind_http_domain")
    # capability_id: console.gateway.create-http-rule
    def test_create_gateway_rules_http_returns_bound_rule(
            self,
            mock_bind_http_route,
            mock_bind_httpdomain,
            mock_manage_port,
            mock_get_port,
            mock_check_domain_exist,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        port = Obj(container_port=80, protocol="http", port_alias="ALIAS80", is_outer_service=True)
        rule = Obj(http_rule_id="rule-1")
        rule.to_dict = lambda: {"http_rule_id": "rule-1", "domain_name": "demo.example.com"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_check_domain_exist.return_value = False
        mock_get_port.return_value = port
        mock_manage_port.return_value = (200, "success", port)
        mock_bind_httpdomain.return_value = rule

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_gateway_rules",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "protocol": "http",
                "http": {
                    "service_id": "svc-1",
                    "container_port": 80,
                    "domain_name": "demo.example.com",
                    "domain_path": "/",
                },
            },
        )

        self.assertEqual(result["http_rule_id"], "rule-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.domain_service.check_domain_exist")
    @patch("console.services.mcp_query_service.port_service.get_service_port_by_port")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.gateway.http-port-not-open
    def test_create_gateway_rules_http_rejects_when_outer_port_is_unavailable(
            self,
            mock_manage_port,
            mock_get_port,
            mock_check_domain_exist,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        tenant_service_port = Obj(container_port=80, protocol="http", port_alias="ALIAS80", is_outer_service=False)
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_check_domain_exist.return_value = False
        mock_get_port.return_value = tenant_service_port
        mock_manage_port.return_value = (200, "success", tenant_service_port)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "http",
                    "http": {
                        "service_id": "svc-1",
                        "container_port": 80,
                        "domain_name": "demo.example.com",
                        "domain_path": "/",
                    },
                },
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "没有开启对外端口")

    @patch.object(mcp_query_service, "_get_team_app_context")
    # capability_id: console.gateway.http-required
    def test_create_gateway_rules_requires_http_payload(self, mock_context):
        mock_context.return_value = (self.team, self.app)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "http",
                },
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "缺少参数http")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.domain_service.check_domain_exist")
    # capability_id: console.gateway.http-rule-guard
    def test_create_gateway_rules_http_rejects_duplicate_rule(
            self,
            mock_check_domain_exist,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_check_domain_exist.return_value = True

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "http",
                    "http": {
                        "service_id": "svc-1",
                        "container_port": 80,
                        "domain_name": "demo.example.com",
                        "domain_path": "/",
                    },
                },
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "策略已存在")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.domain_service.check_domain_exist")
    @patch("console.services.mcp_query_service.port_service.get_service_port_by_port")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.gateway.http-port-open-failure
    def test_create_gateway_rules_http_rejects_port_open_failure(
            self,
            mock_manage_port,
            mock_get_port,
            mock_check_domain_exist,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        port = Obj(container_port=80, protocol="http", port_alias="ALIAS80", is_outer_service=True)
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_check_domain_exist.return_value = False
        mock_get_port.return_value = port
        mock_manage_port.return_value = (500, "open port fail", None)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "http",
                    "http": {
                        "service_id": "svc-1",
                        "container_port": 80,
                        "domain_name": "demo.example.com",
                        "domain_path": "/",
                    },
                },
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.msg_show, "open port fail")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.domain_service.check_domain_exist")
    @patch("console.services.mcp_query_service.port_service.check_domain_thirdpart")
    # capability_id: console.gateway.http-third-party-guard
    def test_create_gateway_rules_http_rejects_invalid_third_party_component(
            self,
            mock_check_thirdpart,
            mock_check_domain_exist,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        self.service.service_source = "third_party"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_check_domain_exist.return_value = False
        mock_check_thirdpart.return_value = ("invalid", "第三方组件不支持网关策略", 412)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "http",
                    "http": {
                        "service_id": "svc-1",
                        "container_port": 80,
                        "domain_name": "demo.example.com",
                        "domain_path": "/",
                    },
                },
            )

        self.assertEqual(context.exception.status_code, 412)
        self.assertEqual(context.exception.msg_show, "第三方组件不支持网关策略")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.get_service_port_by_port")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    @patch("console.services.mcp_query_service.domain_service.bind_tcpdomain")
    # capability_id: console.gateway.create-tcp-rule
    def test_create_gateway_rules_tcp_returns_bound_rule(
            self,
            mock_bind_tcpdomain,
            mock_manage_port,
            mock_get_port,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        port = Obj(container_port=6379, protocol="tcp", port_alias="REDIS", is_outer_service=True)
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_port.return_value = port
        mock_manage_port.return_value = (200, "success", port)
        mock_bind_tcpdomain.return_value = {"tcp_rule_id": "rule-2", "end_point": "1.1.1.1:30001"}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_gateway_rules",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "protocol": "tcp",
                "tcp": {
                    "service_id": "svc-1",
                    "container_port": 6379,
                    "end_point": "1.1.1.1:30001",
                    "default_port": False,
                },
            },
        )

        self.assertEqual(result["tcp_rule_id"], "rule-2")
        self.assertEqual(mock_manage_port.call_args[0][4], "only_open_outer")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.get_service_port_by_port")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.gateway.tcp-port-open-failure
    def test_create_gateway_rules_tcp_rejects_port_open_failure(
            self,
            mock_manage_port,
            mock_get_port,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        port = Obj(container_port=6379, protocol="tcp", port_alias="REDIS", is_outer_service=True)
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_port.return_value = port
        mock_manage_port.return_value = (500, "open tcp port fail", None)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "tcp",
                    "tcp": {
                        "service_id": "svc-1",
                        "container_port": 6379,
                        "end_point": "1.1.1.1:30001",
                        "default_port": False,
                    },
                },
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.msg_show, "open port failure")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.check_domain_thirdpart")
    # capability_id: console.gateway.tcp-third-party-guard
    def test_create_gateway_rules_tcp_rejects_invalid_third_party_component(
            self,
            mock_check_thirdpart,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        self.service.service_source = "third_party"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_check_thirdpart.return_value = ("invalid", "第三方组件不支持 TCP 策略", 412)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "tcp",
                    "tcp": {
                        "service_id": "svc-1",
                        "container_port": 6379,
                        "end_point": "1.1.1.1:30001",
                        "default_port": False,
                    },
                },
            )

        self.assertEqual(context.exception.status_code, 412)
        self.assertEqual(context.exception.msg_show, "第三方组件不支持 TCP 策略")

    @patch.object(mcp_query_service, "_get_team_app_context")
    # capability_id: console.gateway.tcp-required
    def test_create_gateway_rules_requires_tcp_payload(self, mock_context):
        mock_context.return_value = (self.team, self.app)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "tcp",
                },
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "缺少参数tcp")

    @patch.object(mcp_query_service, "_get_team_app_context")
    # capability_id: console.gateway.protocol-guard
    def test_create_gateway_rules_rejects_invalid_protocol(self, mock_context):
        mock_context.return_value = (self.team, self.app)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_gateway_rules",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "protocol": "udp",
                },
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "错误参数: protocol")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.helm_app_service.check_helm_app")
    # capability_id: console.helm.check
    def test_check_helm_app_returns_check_result(self, mock_check_helm_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", region_id="r1", enterprise_id="eid-1")
        mock_check_helm_app.return_value = (None, {"name": "demo-chart"})

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_check_helm_app",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "name": "demo-chart",
                "repo_name": "repo",
                "chart_name": "chart",
                "version": "1.0.0",
            },
        )

        self.assertEqual(result["name"], "demo-chart")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.helm_app_service.yaml_conversion")
    @patch("console.services.mcp_query_service.rainbond_app_repo.get_rainbond_app_by_app_id")
    @patch("console.services.mcp_query_service.helm_app_service.generate_template")
    # capability_id: console.helm.build
    def test_build_helm_app_generates_template(
            self,
            mock_generate_template,
            mock_get_app_model,
            mock_yaml_conversion,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", region_id="r1", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_yaml_conversion.return_value = {"convert_resource": []}
        mock_get_app_model.return_value = Obj(app_id="model-1")

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_build_helm_app",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "name": "demo-chart",
                "repo_name": "repo",
                "chart_name": "chart",
                "version": "1.0.0",
                "app_model_id": "model-1",
            },
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["app_model_id"], "model-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.source_component_service.auto_create_component")
    # capability_id: console.component.create-from-source-guided
    def test_create_component_from_source_calls_aggregated_source_service(
            self, mock_auto_create, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_auto_create.return_value = {"service_id": "svc-1", "built": True}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_component_from_source",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "code_from": "gitlab_manual",
                "service_cname": "component-1",
                "git_url": "https://git.example.com/demo.git",
                "subdirectories": "services/api",
                "version_type": "tag",
                "code_version": "v1.0.0",
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertTrue(result["built"])
        mock_auto_create.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.source_component_service.auto_create_component")
    # capability_id: console.component.create-from-source-generic-git
    def test_create_component_from_source_allows_generic_git_code_from(
            self, mock_auto_create, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_auto_create.return_value = {"service_id": "svc-1", "built": True}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_component_from_source",
            {
                "team_name": "default",
                "region_name": "rainbond",
                "app_id": 6,
                "code_from": "git",
                "service_cname": "demo-2048",
                "git_url": "https://gitee.com/rainbond/demo-2048.git",
                "code_version": "master",
                "server_type": "git",
                "version_type": "branch",
                "is_deploy": True,
            },
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(mock_auto_create.call_args[1]["code_from"], "git")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.package_component_service.auto_create_component")
    # capability_id: console.component.create-from-package-upload
    def test_create_component_from_package_calls_aggregated_package_service(
            self, mock_auto_create, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_auto_create.return_value = {"service_id": "svc-pkg-1", "built": True}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_component_from_package",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "event_id": "evt-upload-1",
                "service_cname": "demo-war",
                "is_deploy": True,
            },
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["service_id"], "svc-pkg-1")
        mock_auto_create.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.app_check_service.check_service")
    # capability_id: console.component.check-start
    def test_check_component_starts_check_flow(
            self, mock_check_service, mock_relations, mock_get_service, mock_get_app, mock_get_region, mock_get_team):
        self.service.service_source = "source_code"
        self.service.create_status = "creating"
        self.service.check_uuid = "chk-1"
        self.service.check_event_id = "evt-check-1"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_check_service.return_value = (200, "success", {"check_uuid": "chk-1"})

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_check_component",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"},
        )

        self.assertEqual(result["check_uuid"], "chk-1")
        self.assertEqual(result["next_action"], "rainbond_get_component_check_result")
        mock_check_service.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.app_check_service.get_service_check_info")
    @patch("console.services.mcp_query_service.app_check_service.save_service_check_info")
    @patch("console.services.mcp_query_service.app_check_service.wrap_service_check_info")
    # capability_id: console.component.check-result
    def test_get_component_check_result_saves_detection_result(
            self,
            mock_wrap_check_info,
            mock_save_check_info,
            mock_get_check_info,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        self.service.service_source = "source_code"
        self.service.create_status = "checked"
        self.service.check_uuid = "chk-1"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_check_info.return_value = (
            200, "success", {"check_status": "success", "error_infos": [], "service_info": [{"language": "Python"}]}
        )

        def mark_checked(team, app_id, service, data):
            service.create_status = "checked"

        mock_save_check_info.side_effect = mark_checked
        mock_wrap_check_info.return_value = {"check_status": "success", "error_infos": [], "service_info": []}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_check_result",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"},
        )

        self.assertTrue(result["can_build"])
        self.assertEqual(result["next_action"], "rainbond_build_component")
        mock_save_check_info.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.console_app_service.create_region_service")
    @patch("console.services.mcp_query_service.arch_service.update_affinity_by_arch")
    @patch("console.services.mcp_query_service.app_manage_service.deploy")
    @patch("console.services.mcp_query_service.deploy_repo.create_deploy_relation_by_service_id")
    # capability_id: console.component.build
    def test_build_component_builds_checked_component(
            self,
            mock_create_deploy_relation,
            mock_deploy,
            mock_update_affinity,
            mock_create_region_service,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        self.service.service_source = "source_code"
        self.service.create_status = "checked"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        built_service = Obj(service_id="svc-1", create_status="complete", arch="amd64")
        mock_create_region_service.return_value = built_service
        mock_deploy.return_value = (200, "success", "evt-1")

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_build_component",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"},
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["create_status"], "complete")
        mock_create_region_service.assert_called_once()
        mock_deploy.assert_called_once()
        mock_create_deploy_relation.assert_called_once_with(service_id="svc-1")

    @patch.object(mcp_query_service, "create_component")
    # capability_id: console.component.create-from-image-direct
    def test_create_component_from_image_uses_existing_image_flow(self, mock_create_component):
        mock_create_component.return_value = {"service_id": "svc-1"}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_component_from_image",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_cname": "component-1",
                "image": "nginx:latest",
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        mock_create_component.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.compose_service.create_group_compose")
    # capability_id: console.app.create-from-yaml
    def test_create_app_from_yaml_creates_compose_record(
            self, mock_create_compose, mock_get_app, mock_get_region, mock_get_team):
        compose = Obj(group_id=12, compose_id="compose-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_create_compose.return_value = (200, "success", compose)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_app_from_yaml",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "event_id": "evt-1",
            },
        )

        self.assertEqual(result["compose_id"], "compose-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.compose_service.check_compose")
    # capability_id: console.app.check-yaml
    def test_check_yaml_app_returns_compose_check_info(
            self, mock_check_compose, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_check_compose.return_value = (200, "success", {"compose_id": "compose-1", "check_uuid": "chk-1"})

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_check_yaml_app",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "compose_id": "compose-1",
            },
        )

        self.assertEqual(result["compose_id"], "compose-1")
        self.assertEqual(result["check_uuid"], "chk-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.compose_service.get_group_compose_by_compose_id")
    @patch("console.services.mcp_query_service.app_check_service.get_service_check_info")
    @patch("console.services.mcp_query_service.compose_service.save_compose_services")
    @patch("console.services.mcp_query_service.compose_service.wrap_compose_check_info")
    # capability_id: console.app.get-yaml-check-result
    def test_get_yaml_app_check_result_returns_services(
            self,
            mock_wrap_check_info,
            mock_save_compose_services,
            mock_get_service_check_info,
            mock_get_group_compose,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        compose = Obj(compose_id="compose-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_group_compose.return_value = compose
        mock_get_service_check_info.return_value = (200, "success", {"check_status": "success", "service_info": []})
        mock_save_compose_services.return_value = (200, "success", [self.service])
        mock_wrap_check_info.return_value = {"check_status": "success"}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_yaml_app_check_result",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "compose_id": "compose-1",
                "check_uuid": "chk-1",
            },
        )

        self.assertEqual(result["compose_id"], "compose-1")
        self.assertEqual(result["services"][0]["service_id"], "svc-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.env_var_service.update_or_create_envs")
    # capability_id: console.component.env-batch-save
    def test_update_component_envs_calls_env_service(
            self,
            mock_update_envs,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_update_envs.return_value = {"envs": [{"name": "A", "value": "B"}]}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_update_component_envs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "envs": [{"name": "A", "value": "B", "is_change": True, "scope": "inner"}],
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["envs"][0]["name"], "A")

    # capability_id: console.component.env-batch-guard
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    def test_update_component_envs_rejects_invalid_payload(
            self,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_update_component_envs",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "service_id": "svc-1",
                    "envs": "invalid",
                },
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.msg_show, "参数envs无效")


class MCPQueryServiceDeleteAppTests(SimpleTestCase):

    def setUp(self):
        self.user = Obj(user_id=1001, enterprise_id="eid-1")
        self.app = Obj(
            ID=12,
            group_name="demo-app",
            tenant_id="team-1",
            region_name="rbd-region",
        )
        self.tenant = Obj(
            tenant_id="team-1",
            tenant_name="demo-team",
            tenant_alias="Demo Team",
            enterprise_id="eid-1",
            creater=1002,
        )

    @patch("console.services.mcp_query_service.group_service.delete_app")
    @patch("console.services.mcp_query_service.group_service_relation_repo.count_service_by_app_id")
    @patch("console.services.mcp_query_service.team_repo.get_user_tenant_by_name")
    @patch("console.services.mcp_query_service.enterprise_user_perm_repo.is_admin")
    @patch("console.services.mcp_query_service.enterprise_repo.get_enterprises_by_user_id")
    @patch("console.services.mcp_query_service.team_repo.get_team_by_team_id")
    @patch("console.services.mcp_query_service.group_repo.get_group_by_id")
    # capability_id: console.app.delete-with-confirmation
    def test_delete_app_requires_confirmation_then_delete(
            self,
            mock_get_app,
            mock_get_team,
            mock_get_user_enterprises,
            mock_is_admin,
            mock_get_user_team,
            mock_count_components,
            mock_delete_app,
    ):
        mock_get_app.return_value = self.app
        mock_get_team.return_value = self.tenant
        mock_get_user_enterprises.return_value = []
        mock_is_admin.return_value = False
        mock_get_user_team.return_value = self.tenant
        mock_count_components.return_value = 3

        prepare_result = mcp_query_service.call_tool(
            self.user,
            "rainbond_delete_app",
            {"app_id": self.app.ID},
        )

        self.assertTrue(prepare_result.get("requires_confirmation"))
        self.assertTrue(prepare_result.get("confirmation_token"))

        confirm_result = mcp_query_service.call_tool(
            self.user,
            "rainbond_delete_app",
            {
                "app_id": self.app.ID,
                "confirm": True,
                "confirmation_token": prepare_result.get("confirmation_token"),
            },
        )

        self.assertFalse(confirm_result.get("requires_confirmation"))
        self.assertTrue(confirm_result.get("deleted"))
        mock_delete_app.assert_called_once_with(self.tenant, self.app.region_name, self.app)

    @patch("console.services.mcp_query_service.group_service_relation_repo.count_service_by_app_id")
    @patch("console.services.mcp_query_service.team_repo.get_user_tenant_by_name")
    @patch("console.services.mcp_query_service.enterprise_user_perm_repo.is_admin")
    @patch("console.services.mcp_query_service.enterprise_repo.get_enterprises_by_user_id")
    @patch("console.services.mcp_query_service.team_repo.get_team_by_team_id")
    @patch("console.services.mcp_query_service.group_repo.get_group_by_id")
    # capability_id: console.app.delete-confirmation-guard
    def test_delete_app_rejects_invalid_confirmation_token(
            self,
            mock_get_app,
            mock_get_team,
            mock_get_user_enterprises,
            mock_is_admin,
            mock_get_user_team,
            mock_count_components,
    ):
        mock_get_app.return_value = self.app
        mock_get_team.return_value = self.tenant
        mock_get_user_enterprises.return_value = []
        mock_is_admin.return_value = False
        mock_get_user_team.return_value = self.tenant
        mock_count_components.return_value = 3

        with self.assertRaises(ServiceHandleException):
            mcp_query_service.call_tool(
                self.user,
                "rainbond_delete_app",
                {
                    "app_id": self.app.ID,
                    "confirm": True,
                    "confirmation_token": "invalid-token",
                },
            )
