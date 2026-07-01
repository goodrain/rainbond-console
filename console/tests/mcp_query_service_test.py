# -*- coding: utf-8 -*-
import json
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
from console.utils.source_build_state import build_compile_env_payload, read_compile_env_state


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
        self.assertIn("rainbond_get_component_pods", tool_names)
        self.assertIn("rainbond_get_pod_detail", tool_names)
        self.assertIn("rainbond_get_component_logs", tool_names)
        self.assertIn("rainbond_get_component_events", tool_names)
        self.assertIn("rainbond_get_component_build_logs", tool_names)
        self.assertIn("rainbond_get_component_build_source", tool_names)
        self.assertIn("rainbond_update_component_build_source", tool_names)
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
        self.assertIn("rainbond_get_app_version_overview", tool_names)
        self.assertIn("rainbond_list_app_version_snapshots", tool_names)
        self.assertIn("rainbond_get_app_version_snapshot_detail", tool_names)
        self.assertIn("rainbond_create_app_version_snapshot", tool_names)
        self.assertIn("rainbond_delete_app_version_snapshot", tool_names)
        self.assertIn("rainbond_rollback_app_version_snapshot", tool_names)
        self.assertIn("rainbond_list_app_version_rollback_records", tool_names)
        self.assertIn("rainbond_get_app_version_rollback_record_detail", tool_names)
        self.assertIn("rainbond_delete_app_version_rollback_record", tool_names)
        self.assertIn("rainbond_create_app_from_snapshot_version", tool_names)
        self.assertIn("rainbond_get_app_publish_candidates", tool_names)
        self.assertIn("rainbond_create_app_share_record", tool_names)
        self.assertIn("rainbond_list_app_share_records", tool_names)
        self.assertIn("rainbond_get_app_share_record", tool_names)
        self.assertIn("rainbond_delete_app_share_record", tool_names)
        self.assertIn("rainbond_get_app_share_info", tool_names)
        self.assertIn("rainbond_submit_app_share_info", tool_names)
        self.assertIn("rainbond_list_app_share_events", tool_names)
        self.assertIn("rainbond_start_app_share_event", tool_names)
        self.assertIn("rainbond_get_app_share_event", tool_names)
        self.assertIn("rainbond_complete_app_share", tool_names)
        self.assertIn("rainbond_giveup_app_share", tool_names)
        self.assertIn("rainbond_build_component", tool_names)
        self.assertIn("rainbond_get_app_last_upgrade_record", tool_names)
        self.assertIn("rainbond_query_app_upgrade_records", tool_names)
        self.assertIn("rainbond_create_app_upgrade_record", tool_names)
        self.assertIn("rainbond_get_app_upgrade_record", tool_names)
        self.assertIn("rainbond_get_app_upgrade_detail", tool_names)
        self.assertIn("rainbond_get_app_upgrade_changes", tool_names)
        self.assertIn("rainbond_execute_app_upgrade_record", tool_names)
        self.assertIn("rainbond_deploy_app_upgrade_record", tool_names)
        self.assertIn("rainbond_get_app_rollback_records", tool_names)
        self.assertIn("rainbond_rollback_app_upgrade_record", tool_names)
        self.assertIn("rainbond_get_app_upgrade_info", tool_names)
        self.assertIn("rainbond_upgrade_app", tool_names)
        self.assertIn("rainbond_get_copy_app_info", tool_names)
        self.assertIn("rainbond_copy_app", tool_names)
        self.assertIn("rainbond_query_cloud_markets", tool_names)
        self.assertIn("rainbond_query_local_app_models", tool_names)
        self.assertIn("rainbond_query_cloud_app_models", tool_names)
        self.assertIn("rainbond_query_app_model_versions", tool_names)
        self.assertIn("rainbond_install_app_model", tool_names)
        self.assertIn("rainbond_install_app_by_market", tool_names)
        self.assertIn("rainbond_create_component_from_source", tool_names)
        self.assertIn("rainbond_create_component_from_package", tool_names)
        self.assertIn("rainbond_init_package_upload", tool_names)
        self.assertIn("rainbond_upload_package_file", tool_names)
        self.assertIn("rainbond_get_package_upload_status", tool_names)
        self.assertIn("rainbond_delete_package_upload", tool_names)
        self.assertIn("rainbond_create_component_from_local_package", tool_names)
        self.assertIn("rainbond_check_component", tool_names)
        self.assertIn("rainbond_get_component_check_result", tool_names)
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
        self.assertIn("rainbond_get_component_pods", tool_names)
        self.assertIn("rainbond_get_pod_detail", tool_names)
        self.assertIn("rainbond_get_component_logs", tool_names)
        self.assertIn("rainbond_get_component_events", tool_names)
        self.assertIn("rainbond_get_component_build_logs", tool_names)
        self.assertIn("rainbond_get_component_build_source", tool_names)
        self.assertIn("rainbond_update_component_build_source", tool_names)
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
        self.assertIn("rainbond_get_app_version_overview", tool_names)
        self.assertIn("rainbond_list_app_version_snapshots", tool_names)
        self.assertIn("rainbond_get_app_version_snapshot_detail", tool_names)
        self.assertIn("rainbond_create_app_version_snapshot", tool_names)
        self.assertIn("rainbond_delete_app_version_snapshot", tool_names)
        self.assertIn("rainbond_rollback_app_version_snapshot", tool_names)
        self.assertIn("rainbond_list_app_version_rollback_records", tool_names)
        self.assertIn("rainbond_get_app_version_rollback_record_detail", tool_names)
        self.assertIn("rainbond_delete_app_version_rollback_record", tool_names)
        self.assertIn("rainbond_create_app_from_snapshot_version", tool_names)
        self.assertIn("rainbond_get_app_publish_candidates", tool_names)
        self.assertIn("rainbond_create_app_share_record", tool_names)
        self.assertIn("rainbond_list_app_share_records", tool_names)
        self.assertIn("rainbond_get_app_share_record", tool_names)
        self.assertIn("rainbond_delete_app_share_record", tool_names)
        self.assertIn("rainbond_get_app_share_info", tool_names)
        self.assertIn("rainbond_submit_app_share_info", tool_names)
        self.assertIn("rainbond_list_app_share_events", tool_names)
        self.assertIn("rainbond_start_app_share_event", tool_names)
        self.assertIn("rainbond_get_app_share_event", tool_names)
        self.assertIn("rainbond_complete_app_share", tool_names)
        self.assertIn("rainbond_giveup_app_share", tool_names)
        self.assertIn("rainbond_build_component", tool_names)
        self.assertIn("rainbond_get_app_last_upgrade_record", tool_names)
        self.assertIn("rainbond_query_app_upgrade_records", tool_names)
        self.assertIn("rainbond_create_app_upgrade_record", tool_names)
        self.assertIn("rainbond_get_app_upgrade_record", tool_names)
        self.assertIn("rainbond_get_app_upgrade_detail", tool_names)
        self.assertIn("rainbond_get_app_upgrade_changes", tool_names)
        self.assertIn("rainbond_execute_app_upgrade_record", tool_names)
        self.assertIn("rainbond_deploy_app_upgrade_record", tool_names)
        self.assertIn("rainbond_get_app_rollback_records", tool_names)
        self.assertIn("rainbond_rollback_app_upgrade_record", tool_names)
        self.assertIn("rainbond_get_app_upgrade_info", tool_names)
        self.assertIn("rainbond_upgrade_app", tool_names)
        self.assertIn("rainbond_get_copy_app_info", tool_names)
        self.assertIn("rainbond_copy_app", tool_names)
        self.assertIn("rainbond_query_cloud_markets", tool_names)
        self.assertIn("rainbond_query_local_app_models", tool_names)
        self.assertIn("rainbond_query_cloud_app_models", tool_names)
        self.assertIn("rainbond_query_app_model_versions", tool_names)
        self.assertIn("rainbond_install_app_model", tool_names)
        self.assertIn("rainbond_install_app_by_market", tool_names)
        self.assertIn("rainbond_create_component_from_source", tool_names)
        self.assertIn("rainbond_create_component_from_package", tool_names)
        self.assertIn("rainbond_init_package_upload", tool_names)
        self.assertIn("rainbond_upload_package_file", tool_names)
        self.assertIn("rainbond_get_package_upload_status", tool_names)
        self.assertIn("rainbond_delete_package_upload", tool_names)
        self.assertIn("rainbond_create_component_from_local_package", tool_names)
        self.assertIn("rainbond_check_component", tool_names)
        self.assertIn("rainbond_get_component_check_result", tool_names)
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

    # capability_id: console.gateway.port-protocol-schema
    def test_manage_component_ports_tool_schema_exposes_protocol_enum(self):
        tool = mcp_query_service._tool_manage_component_ports()

        protocol_schema = tool["inputSchema"]["properties"]["protocol"]
        port_item_schema = tool["inputSchema"]["properties"]["ports"]["items"]["oneOf"][1]["properties"]["protocol"]

        self.assertEqual(protocol_schema["enum"], ["http", "https", "stream", "grpc"])
        self.assertEqual(port_item_schema["enum"], ["http", "https", "stream", "grpc"])
        self.assertIn("小写", protocol_schema["description"])

    # capability_id: console.gateway.port-constraints-schema
    def test_manage_component_ports_tool_schema_exposes_port_constraints(self):
        tool = mcp_query_service._tool_manage_component_ports()

        port_alias_schema = tool["inputSchema"]["properties"]["port_alias"]
        k8s_service_name_schema = tool["inputSchema"]["properties"]["k8s_service_name"]

        self.assertEqual(port_alias_schema["pattern"], r"^[A-Z][A-Z0-9_]*$")
        self.assertIn("留空", port_alias_schema["description"])
        self.assertEqual(k8s_service_name_schema["pattern"], r"^[a-z]([-a-z0-9]*[a-z0-9])?$")
        self.assertEqual(k8s_service_name_schema["maxLength"], 63)

    # capability_id: console.gateway.create-app-k8s-name-schema
    def test_create_app_tool_schema_exposes_k8s_app_constraints(self):
        tool = mcp_query_service._tool_create_app()

        app_name_schema = tool["inputSchema"]["properties"]["app_name"]
        k8s_app_schema = tool["inputSchema"]["properties"]["k8s_app"]

        self.assertIn("展示名称", app_name_schema["description"])
        self.assertEqual(app_name_schema["maxLength"], 128)
        self.assertEqual(app_name_schema["pattern"], r"^[a-zA-Z0-9_\.\-\u4e00-\u9fa5]+$")
        self.assertIn("不支持空格", app_name_schema["description"])
        self.assertEqual(k8s_app_schema["pattern"], r"^[a-z]([-a-z0-9]*[a-z0-9])?$")
        self.assertIn("默认建议不传", k8s_app_schema["description"])

    # capability_id: console.app-version.target-app-name-schema
    def test_create_app_from_snapshot_version_tool_exposes_target_app_name_constraints(self):
        tool = mcp_query_service._tool_create_app_from_snapshot_version()

        target_app_name_schema = tool["inputSchema"]["properties"]["target_app_name"]

        self.assertEqual(target_app_name_schema["maxLength"], 128)
        self.assertEqual(target_app_name_schema["pattern"], r"^[a-zA-Z0-9_\.\-\u4e00-\u9fa5]+$")
        self.assertIn("不支持空格", target_app_name_schema["description"])

    # capability_id: console.gateway.source-code-from-schema
    def test_create_component_from_source_schema_exposes_code_from_guidance(self):
        tool = mcp_query_service._tool_create_component_from_source()

        code_from_schema = tool["inputSchema"]["properties"]["code_from"]
        prefer_dockerfile_schema = tool["inputSchema"]["properties"]["prefer_dockerfile_when_detected"]
        subdirectories_schema = tool["inputSchema"]["properties"]["subdirectories"]

        self.assertIn("git/github/oauth_xxx", code_from_schema["description"])
        self.assertIn("gitlab_manual", code_from_schema["description"])
        self.assertIn("不支持指定具体 dockerfile_path", prefer_dockerfile_schema["description"])
        self.assertIn("?dir=", subdirectories_schema["description"])

    # capability_id: console.package-upload.local-path-schema
    def test_upload_package_file_tool_schema_exposes_local_path_guidance(self):
        tool = mcp_query_service._tool_upload_package_file()

        local_path_schema = tool["inputSchema"]["properties"]["local_path"]
        archive_name_schema = tool["inputSchema"]["properties"]["archive_name"]

        self.assertEqual(tool["name"], "rainbond_upload_package_file")
        self.assertIn("本地文件或目录路径", local_path_schema["description"])
        self.assertIn("rainbond-console", local_path_schema["description"])
        self.assertIn("不是 MCP 客户端本机路径", local_path_schema["description"])
        self.assertIn("zip", archive_name_schema["description"])

    # capability_id: console.package-upload.local-path-create-schema
    def test_create_component_from_local_package_tool_schema_exposes_server_side_local_path_guidance(self):
        tool = mcp_query_service._tool_create_component_from_local_package()

        local_path_schema = tool["inputSchema"]["properties"]["local_path"]

        self.assertIn("本地文件或目录路径", local_path_schema["description"])
        self.assertIn("rainbond-console", local_path_schema["description"])
        self.assertIn("不是 MCP 客户端本机路径", local_path_schema["description"])

    # capability_id: console.gateway.dependency-container-port-schema
    def test_manage_component_dependency_schema_exposes_container_port_guidance(self):
        tool = mcp_query_service._tool_manage_component_dependency()

        open_inner_schema = tool["inputSchema"]["properties"]["open_inner"]
        container_port_schema = tool["inputSchema"]["properties"]["container_port"]

        self.assertIn("被依赖组件", container_port_schema["description"])
        self.assertIn("open_inner=true", container_port_schema["description"])
        self.assertIn("自动开启", open_inner_schema["description"])

    # capability_id: console.gateway.component-env-upsert-schema
    def test_manage_component_envs_schema_exposes_single_item_upsert_guidance(self):
        tool = mcp_query_service._tool_manage_component_envs()

        envs_schema = tool["inputSchema"]["properties"]["envs"]
        attr_name_schema = tool["inputSchema"]["properties"]["attr_name"]
        build_env_dict_schema = tool["inputSchema"]["properties"]["build_env_dict"]

        self.assertIn("upsert", envs_schema["description"])
        self.assertIn("单条", attr_name_schema["description"])
        self.assertIn("BUILD_NO_CACHE", build_env_dict_schema["description"])
        self.assertIn("CNB_FRAMEWORK", build_env_dict_schema["description"])
        self.assertIn("BP_JVM_VERSION", build_env_dict_schema["description"])
        self.assertIn("BP_GO_VERSION", build_env_dict_schema["description"])
        self.assertIn("BP_DOTNET_FRAMEWORK_VERSION", build_env_dict_schema["description"])

    # capability_id: console.component.build-component-schema
    def test_build_component_tool_schema_exposes_build_info_guidance(self):
        tool = mcp_query_service._tool_build_component()

        build_info_schema = tool["inputSchema"]["properties"]["build_info"]

        self.assertIn("repo_url", build_info_schema["description"])
        self.assertIn("branch", build_info_schema["description"])
        self.assertIn("username", build_info_schema["description"])
        self.assertIn("replace_build_envs", build_info_schema["description"])
        self.assertEqual(build_info_schema["properties"]["repo_url"]["type"], "string")
        self.assertEqual(build_info_schema["properties"]["password"]["type"], "string")

    # capability_id: console.component.default-resource-spec
    def test_component_creation_tools_expose_default_resource_guidance(self):
        image_tool = mcp_query_service._tool_create_component_from_image()
        source_tool = mcp_query_service._tool_create_component_from_source()
        package_tool = mcp_query_service._tool_create_component_from_package()
        build_tool = mcp_query_service._tool_build_component()

        self.assertIn("512MB", image_tool["description"])
        self.assertIn("0m CPU", image_tool["description"])
        self.assertIn("128MB", source_tool["description"])
        self.assertIn("500m CPU", source_tool["description"])
        self.assertIn("32MB", source_tool["description"])
        self.assertIn("128MB", package_tool["description"])
        self.assertIn("500m CPU", package_tool["description"])
        self.assertIn("默认资源", build_tool["description"])
        self.assertIn("沿用组件当前", build_tool["description"])

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
    # capability_id: console.enterprise.region-detail-by-name
    def test_get_region_detail_accepts_region_name(self, mock_get_region):
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

        result = mcp_query_service.call_tool(user, "rainbond_get_region_detail", {"region_name": "rainbond"})

        self.assertEqual(result["region_id"], "r1")
        self.assertEqual(result["region_name"], "rainbond")
        mock_get_region.assert_called_once_with("eid-1", "rainbond")

    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.region_services.get_region_by_region_id")
    # capability_id: console.enterprise.region-detail-region-name-fallback
    def test_get_region_detail_treats_missing_region_id_as_region_name(self, mock_get_region_by_id,
                                                                        mock_get_region_by_name):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        mock_get_region_by_id.return_value = None
        mock_get_region_by_name.return_value = Obj(
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

        result = mcp_query_service.call_tool(
            user, "rainbond_get_region_detail", {"region_id": "rainbond", "region_name": "rainbond"})

        self.assertEqual(result["region_id"], "r1")
        mock_get_region_by_name.assert_called_once_with("eid-1", "rainbond")

    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.region_services.get_region_by_region_id")
    # capability_id: console.enterprise.region-detail-no-cross-fallback
    def test_get_region_detail_does_not_override_distinct_bad_region_id(self, mock_get_region_by_id,
                                                                        mock_get_region_by_name):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )
        mock_get_region_by_id.return_value = None

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                user, "rainbond_get_region_detail", {"region_id": "missing-id", "region_name": "rainbond"})

        self.assertEqual(context.exception.status_code, 404)
        mock_get_region_by_name.assert_not_called()

    # capability_id: console.enterprise.region-detail-schema
    def test_get_region_detail_schema_accepts_region_name(self):
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="admin",
            real_name="Admin User",
            email="admin@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )

        tool = next(tool for tool in mcp_query_service.list_tools(user) if tool["name"] == "rainbond_get_region_detail")

        self.assertIn("region_id", tool["inputSchema"]["properties"])
        self.assertIn("region_name", tool["inputSchema"]["properties"])

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
    @patch("console.services.mcp_query_service.group_service.create_app")
    # capability_id: console.app.create-k8s-name-duplicate
    def test_create_app_exposes_structured_k8s_app_duplicate_error(self, mock_create_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_create_app.side_effect = ServiceHandleException(
            msg="k8s app name exists", msg_show="k8s app name exists", status_code=400, error_code=11011
        )

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_app",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_name": "demo-app",
                    "k8s_app": "demo-app",
                },
            )

        self.assertEqual(context.exception.error_code, 11011)
        self.assertEqual(context.exception.details["field"], "k8s_app")
        self.assertEqual(context.exception.details["reason"], "duplicate")
        self.assertFalse(context.exception.details["retryable"])

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
    @patch("console.services.mcp_query_service.volume_service.get_all_service_volumes_with_status")
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
    # capability_id: console.component.pods
    def test_get_component_pods_returns_normalized_runtime_instances(
            self,
            mock_get_service_pods,
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
        mock_get_service_pods.return_value = {
            "bean": {
                "new_pods": [
                    {
                        "pod_name": "pod-new-1",
                        "pod_status": "RUNNING",
                        "manage_name": "manager",
                        "container": {"POD": {}, "main": {}, "sidecar": {}}
                    }
                ],
                "old_pods": [
                    {
                        "pod_name": "pod-old-1",
                        "pod_status": "TERMINATING",
                        "container": [{"container_name": "legacy"}]
                    }
                ]
            }
        }

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_pods",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"},
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["items"][0]["pod_name"], "pod-new-1")
        self.assertEqual(result["items"][0]["group"], "new_pods")
        self.assertEqual(result["items"][0]["container_names"], ["main", "sidecar"])
        self.assertEqual(result["items"][1]["group"], "old_pods")
        self.assertEqual(result["items"][1]["container_names"], ["legacy"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.region_api.pod_detail")
    # capability_id: console.pod.detail
    def test_get_pod_detail_returns_runtime_diagnostics(
            self,
            mock_pod_detail,
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
        mock_pod_detail.return_value = {
            "bean": {
                "name": "pod-new-1",
                "namespace": "demo-team",
                "status": {
                    "type": 7,
                    "reason": "ContainersNotInitialized",
                    "message": "containers with incomplete status: [init]"
                },
                "init_containers": [{"image": "probe:v1", "state": "Waiting", "reason": "ImagePullBackOff"}],
                "containers": [{"image": "demo:v1", "state": "Waiting", "reason": "PodInitializing"}],
                "events": [{"type": "Warning", "reason": "Failed", "message": "ImagePullBackOff"}]
            }
        }

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_pod_detail",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "pod_name": "pod-new-1",
            },
        )

        self.assertEqual(result["name"], "pod-new-1")
        self.assertEqual(result["status"]["reason"], "ContainersNotInitialized")
        self.assertEqual(result["init_containers"][0]["reason"], "ImagePullBackOff")
        self.assertEqual(result["events"][0]["reason"], "Failed")
        mock_pod_detail.assert_called_once_with("rainbond", "demo-team", "alias-1", "pod-new-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.region_api.kubeblocks_cluster_pod_detail")
    @patch("console.services.mcp_query_service.region_api.pod_detail")
    # capability_id: console.pod.detail-kubeblocks
    def test_get_pod_detail_uses_kubeblocks_endpoint_for_kubeblocks_component(
            self,
            mock_pod_detail,
            mock_kubeblocks_pod_detail,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        self.service.extend_method = "kubeblocks_component"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_kubeblocks_pod_detail.return_value = {"bean": {"name": "pod-new-1", "status": {"reason": "Running"}}}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_pod_detail",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "pod_name": "pod-new-1",
            },
        )

        self.assertEqual(result["name"], "pod-new-1")
        mock_kubeblocks_pod_detail.assert_called_once_with("rainbond", "svc-1", "pod-new-1")
        mock_pod_detail.assert_not_called()

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
    @patch("console.services.mcp_query_service.volume_service.get_all_service_volumes_with_status")
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
    @patch("console.services.mcp_query_service.autoscaler_service.create_autoscaler_rule")
    # capability_id: console.component.autoscaler-invalid-metrics
    def test_manage_component_autoscaler_create_rejects_incomplete_metric_before_service_call(
            self,
            mock_create_rule,
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

        with self.assertRaises(ServiceHandleException) as ctx:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_manage_component_autoscaler",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "service_id": "svc-1",
                    "operation": "create_rule",
                    "xpa_type": "hpa",
                    "enable": True,
                    "min_replicas": 1,
                    "max_replicas": 2,
                    "metrics": [{"metric_type": "resource_metrics"}],
                },
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.msg, "invalid metrics")
        mock_create_rule.assert_not_called()

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
    @patch("console.services.mcp_query_service.env_var_service.get_service_inner_env")
    @patch("console.services.mcp_query_service.env_var_service.add_service_env_var")
    # capability_id: console.component.env-upsert-single-item
    def test_manage_component_envs_upsert_accepts_single_item_shape(
            self,
            mock_add_env,
            mock_get_inner_envs,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        env = Obj(attr_name="DB_PASSWORD", attr_value="postgres", name="DB_PASSWORD", is_change=True, scope="inner")
        env.to_dict = lambda: {"attr_name": "DB_PASSWORD", "attr_value": "postgres", "scope": "inner"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_inner_envs.side_effect = [[], [env]]
        mock_add_env.return_value = (200, "success", env)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_envs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "upsert",
                "name": "DB_PASSWORD",
                "attr_name": "DB_PASSWORD",
                "attr_value": "postgres",
                "scope": "inner",
                "is_change": True,
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["envs"][0]["name"], "DB_PASSWORD")
        self.assertEqual(mock_add_env.call_args[0][3], "DB_PASSWORD")
        self.assertEqual(mock_add_env.call_args[0][4], "DB_PASSWORD")
        self.assertEqual(mock_add_env.call_args[0][5], "postgres")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.env_var_service.get_service_build_envs")
    @patch("console.services.mcp_query_service.env_var_service.add_service_build_env_var")
    @patch("console.services.mcp_query_service.compile_env_repo.get_service_compile_env")
    # capability_id: console.component.build-env-preserve-source-build-state
    def test_manage_component_envs_replace_build_envs_preserves_source_build_state(
            self,
            mock_get_compile_env,
            mock_add_build_env,
            mock_get_build_envs,
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
        mock_get_build_envs.return_value = [Obj(delete=lambda: None)]
        mock_add_build_env.return_value = (200, "success", Obj())

        compile_env = Obj(
            user_dependency=json.dumps(build_compile_env_payload(
                {
                    "language": "Java-maven",
                    "runtimes": "17",
                    "procfile": "",
                    "dependencies": {}
                },
                {
                    "user_saved": {
                        "Java-maven": {
                            "compile_env": {
                                "language": "Java-maven",
                                "runtimes": "21",
                                "procfile": "",
                                "dependencies": {}
                            },
                            "build_env_dict": {
                                "BUILD_RUNTIMES": "21"
                            },
                            "build_strategy": "cnb",
                            "cmd": "start web"
                        }
                    }
                }
            )),
            save=lambda: None,
        )
        mock_get_compile_env.return_value = compile_env

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_envs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "replace_build_envs",
                "build_env_dict": {
                    "BUILD_RUNTIMES": "17"
                },
            },
        )

        compile_env_payload, state = read_compile_env_state(compile_env.user_dependency)

        self.assertTrue(result["updated"])
        self.assertEqual(compile_env_payload["language"], "Java-maven")
        self.assertEqual(compile_env_payload["runtimes"], "17")
        self.assertEqual(state["user_saved"]["Java-maven"]["build_env_dict"]["BUILD_RUNTIMES"], "21")

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
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.component.port-open-public
    def test_manage_component_ports_enable_outer_passes_app_context_to_port_service(
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
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "enable_outer",
                "port": 80,
            },
        )

        self.assertEqual(result["container_port"], 80)
        self.assertEqual(mock_manage_port.call_args[0][4], "open_outer")
        self.assertIs(mock_manage_port.call_args[1]["app"], self.app)

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

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.batch_add_service_ports")
    # capability_id: console.component.port-batch-add
    def test_manage_component_ports_batch_add_delegates_to_batch_service(
            self,
            mock_batch_add,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        port80 = Obj(tenant_id="team-1", service_id="svc-1", container_port=80, protocol="http",
                     is_inner_service=True, is_outer_service=False, port_alias="ALIAS180",
                     k8s_service_name="alias-1", mapping_port=80)
        port80.to_dict = lambda: {"container_port": 80, "protocol": "http",
                                  "is_inner_service": True, "is_outer_service": False}
        port8080 = Obj(tenant_id="team-1", service_id="svc-1", container_port=8080, protocol="stream",
                       is_inner_service=False, is_outer_service=False, port_alias="ALIAS18080",
                       k8s_service_name="alias-1", mapping_port=8080)
        port8080.to_dict = lambda: {"container_port": 8080, "protocol": "stream",
                                    "is_inner_service": False, "is_outer_service": False}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_batch_add.return_value = [port80, port8080]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "add",
                "ports": [
                    {"port": 80, "protocol": " HTTP ", "enable_inner": True},
                    {"port": 8080, "protocol": "Stream"},
                ],
            },
        )

        self.assertEqual(len(result["ports"]), 2)
        call_args = mock_batch_add.call_args
        self.assertEqual(call_args[0][0], self.team)
        self.assertEqual(call_args[0][1], self.service)
        passed_ports = call_args[0][2]
        self.assertEqual(len(passed_ports), 2)
        self.assertEqual(passed_ports[0]["port"], 80)
        self.assertEqual(passed_ports[0]["protocol"], "http")
        self.assertEqual(passed_ports[1]["port"], 8080)
        self.assertEqual(passed_ports[1]["protocol"], "stream")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.component.port-batch-enable-inner
    def test_manage_component_ports_batch_enable_inner_loads_context_once(
            self,
            mock_manage_port,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        def make_port(n):
            p = Obj(container_port=n, protocol="http", is_inner_service=True, is_outer_service=False)
            p.to_dict = lambda: {"container_port": n}
            return p

        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_manage_port.side_effect = [(200, "success", make_port(80)), (200, "success", make_port(8080))]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "enable_inner",
                "ports": [{"port": 80}, {"port": 8080}],
            },
        )

        self.assertEqual(len(result["ports"]), 2)
        # context loaded exactly once (get_team called once)
        self.assertEqual(mock_get_team.call_count, 1)
        # manage_port called for each port with open_inner action
        self.assertEqual(mock_manage_port.call_count, 2)
        self.assertEqual(mock_manage_port.call_args_list[0][0][4], "open_inner")
        self.assertEqual(mock_manage_port.call_args_list[1][0][4], "open_inner")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.component.port-batch-enable-outer
    def test_manage_component_ports_batch_enable_outer_accepts_integer_items(
            self,
            mock_manage_port,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        def make_port(n):
            p = Obj(container_port=n, protocol="http", is_inner_service=True, is_outer_service=True)
            p.to_dict = lambda: {"container_port": n}
            return p

        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_manage_port.side_effect = [(200, "success", make_port(80)), (200, "success", make_port(443))]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "enable_outer",
                "ports": [80, 443],
            },
        )

        self.assertEqual(len(result["ports"]), 2)
        self.assertEqual(mock_manage_port.call_args_list[0][0][3], 80)
        self.assertEqual(mock_manage_port.call_args_list[1][0][3], 443)
        self.assertEqual(mock_manage_port.call_args_list[0][0][4], "open_outer")
        self.assertEqual(mock_manage_port.call_args_list[1][0][4], "open_outer")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.component.port-protocol-normalize
    def test_manage_component_ports_update_protocol_normalizes_protocol(
            self,
            mock_manage_port,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        port = Obj(container_port=80, protocol="https", is_inner_service=True, is_outer_service=False)
        port.to_dict = lambda: {"container_port": 80, "protocol": "https"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_manage_port.return_value = (200, "success", port)

        mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "update_protocol",
                "port": 80,
                "protocol": " HTTPS ",
            },
        )

        self.assertEqual(mock_manage_port.call_args[0][5], "https")

    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.component.port-protocol-validation
    def test_manage_component_ports_update_protocol_rejects_invalid_protocol_before_service_call(
            self,
            mock_manage_port,
    ):
        with self.assertRaises(ServiceHandleException) as cm:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_manage_component_ports",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "service_id": "svc-1",
                    "operation": "update_protocol",
                    "port": 80,
                    "protocol": "tcp",
                },
            )

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("protocol", cm.exception.msg_show)
        self.assertIn("http", cm.exception.msg_show)
        self.assertFalse(mock_manage_port.called)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.manage_port")
    # capability_id: console.component.port-batch-protocol
    def test_manage_component_ports_batch_update_protocol_passes_each_normalized_protocol(
            self,
            mock_manage_port,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        def make_port(n, protocol):
            p = Obj(container_port=n, protocol=protocol, is_inner_service=True, is_outer_service=False)
            p.to_dict = lambda: {"container_port": n, "protocol": protocol}
            return p

        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_manage_port.side_effect = [
            (200, "success", make_port(80, "http")),
            (200, "success", make_port(443, "grpc")),
        ]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_manage_component_ports",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "operation": "update_protocol",
                "ports": [
                    {"port": 80, "protocol": " HTTP "},
                    {"port": 443, "protocol": "Grpc"},
                ],
            },
        )

        self.assertEqual(len(result["ports"]), 2)
        self.assertEqual(mock_manage_port.call_args_list[0][0][5], "http")
        self.assertEqual(mock_manage_port.call_args_list[1][0][5], "grpc")

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

    @patch("console.services.mcp_query_service.service_repo.get_services_by_service_ids")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.team_repo.get_user_tenant_by_name")
    @patch("console.services.mcp_query_service.enterprise_user_perm_repo.is_admin")
    @patch("console.services.mcp_query_service.enterprise_repo.get_enterprises_by_user_id")
    @patch("console.services.mcp_query_service.team_repo.get_team_by_team_id")
    @patch("console.services.mcp_query_service.group_repo.get_group_by_id")
    # capability_id: console.component.list
    def test_query_components_query_matches_service_id_exactly(
            self,
            mock_get_app,
            mock_get_team_by_team_id,
            mock_get_enterprises,
            mock_is_admin,
            mock_get_user_tenant,
            mock_get_relations,
            mock_get_services,
    ):
        """When the LLM passes a 32-char hex service_id as `query`, the filter
        should still match that component instead of falling back to fuzzy
        cname/alias matching (which never matches a hex id)."""
        app = Obj(ID=12, tenant_id="team-1", group_name="demo-app")
        tenant = self.team
        nginx = Obj(
            service_id="eab572213bd297e5597fa3e231119aed",
            service_alias="alias-1",
            service_cname="Nginx",
        )
        nginx.to_dict = lambda: {
            "service_id": nginx.service_id,
            "service_alias": nginx.service_alias,
            "service_cname": nginx.service_cname,
        }
        mysql = Obj(
            service_id="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            service_alias="alias-2",
            service_cname="MySQL",
        )
        mysql.to_dict = lambda: {
            "service_id": mysql.service_id,
            "service_alias": mysql.service_alias,
            "service_cname": mysql.service_cname,
        }

        mock_get_app.return_value = app
        mock_get_team_by_team_id.return_value = tenant
        mock_get_enterprises.return_value = [Obj(enterprise_id="eid-1")]
        mock_is_admin.return_value = True
        mock_get_user_tenant.return_value = tenant
        mock_get_relations.return_value = [
            Obj(service_id=nginx.service_id),
            Obj(service_id=mysql.service_id),
        ]
        mock_get_services.return_value = [nginx, mysql]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_components",
            {
                "enterprise_id": "eid-1",
                "app_id": 12,
                "query": nginx.service_id,
                "page": 1,
                "page_size": 20,
            },
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["service_id"], nginx.service_id)

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

    @patch("console.services.mcp_query_service.event_service.get_event_log")
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    # capability_id: console.component.build-logs
    def test_get_component_build_logs_returns_event_log_items(
            self,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
            mock_get_event_log,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_event_log.return_value = ["step-1", "step-2"]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_build_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "event_id": "evt-build-1",
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["event_id"], "evt-build-1")
        self.assertEqual(result["items"], ["step-1", "step-2"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["total_unfiltered"], 2)
        self.assertFalse(result["truncated"])
        mock_get_event_log.assert_called_once_with(self.team, "rainbond", "evt-build-1")

    @patch("console.services.mcp_query_service.event_service.get_event_log")
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    # capability_id: console.component.build-logs
    def test_get_component_build_logs_tail_returns_last_n_items(
            self,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
            mock_get_event_log,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        full_log = [{"message": "step-%d" % i, "time": "t-%d" % i} for i in range(10)]
        mock_get_event_log.return_value = full_log

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_build_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "event_id": "evt-build-1",
                "tail": 3,
            },
        )

        self.assertEqual([item["message"] for item in result["items"]], ["step-7", "step-8", "step-9"])
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["total_unfiltered"], 10)
        self.assertTrue(result["truncated"])

    @patch("console.services.mcp_query_service.event_service.get_event_log")
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    # capability_id: console.component.build-logs
    def test_get_component_build_logs_grep_filters_message_field(
            self,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
            mock_get_event_log,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_event_log.return_value = [
            {"message": "Downloading dependency...", "time": "t1"},
            {"message": "[ERROR] Compilation failed", "time": "t2"},
            {"message": "BUILD FAILURE", "time": "t3"},
            {"message": "tail spam", "time": "t4"},
        ]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_build_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "event_id": "evt-build-1",
                "grep": "ERROR",
            },
        )

        self.assertEqual([item["message"] for item in result["items"]], ["[ERROR] Compilation failed"])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["total_unfiltered"], 4)
        self.assertTrue(result["truncated"])

    @patch("console.services.mcp_query_service.event_service.get_event_log")
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    # capability_id: console.component.build-logs
    def test_get_component_build_logs_offset_limit_paginates(
            self,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
            mock_get_event_log,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_event_log.return_value = [
            {"message": "step-%d" % i} for i in range(10)
        ]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_build_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "event_id": "evt-build-1",
                "offset": 5,
                "limit": 3,
            },
        )

        self.assertEqual([item["message"] for item in result["items"]], ["step-5", "step-6", "step-7"])
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["total_unfiltered"], 10)
        self.assertTrue(result["truncated"])

    @patch("console.services.mcp_query_service.event_service.get_event_log")
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    # capability_id: console.component.build-logs
    def test_get_component_build_logs_grep_then_tail_applies_in_order(
            self,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
            mock_get_event_log,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_event_log.return_value = [
            {"message": "[ERROR] first"},
            {"message": "ok"},
            {"message": "[ERROR] second"},
            {"message": "[ERROR] third"},
            {"message": "ok again"},
        ]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_build_logs",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "event_id": "evt-build-1",
                "grep": "ERROR",
                "tail": 2,
            },
        )

        # grep first (3 matches), then tail of those 3 = last 2
        self.assertEqual(
            [item["message"] for item in result["items"]],
            ["[ERROR] second", "[ERROR] third"],
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["total_unfiltered"], 5)
        self.assertTrue(result["truncated"])

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
    @patch("console.services.mcp_query_service.console_app_service.create_docker_run_app")
    @patch("console.services.mcp_query_service.group_service.add_service_to_group")
    @patch("console.services.mcp_query_service.console_app_service.create_region_service")
    @patch("console.services.mcp_query_service.app_manage_service.deploy")
    # capability_id: console.component.create-from-image
    def test_create_component_copies_docker_cmd_into_cmd(
            self,
            mock_deploy,
            mock_create_region_service,
            mock_add_service_to_group,
            mock_create_docker_run_app,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        # create_docker_run_app only persists docker_cmd; the MCP path skips
        # the docker-run check stage that would parse it into service.cmd,
        # while deploy only sends service.cmd to the builder. The handler
        # must copy it over or the start command never reaches the container.
        self.service.cmd = ""
        self.service.docker_cmd = "bundle exec rails server -p 3000"
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
                "image": "chatwoot/chatwoot:latest",
                "docker_cmd": "bundle exec rails server -p 3000",
                "is_deploy": True,
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(self.service.cmd, "bundle exec rails server -p 3000")

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
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.app_manage_service.batch_action")
    @patch("console.services.mcp_query_service.app_manage_service.batch_operations")
    # capability_id: console.app.restart-component-operation
    def test_operate_app_restart_calls_batch_action(
            self,
            mock_batch_operations,
            mock_batch_action,
            mock_relations,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_batch_action.return_value = (200, "success", [self.service])

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_operate_app",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "action": "restart",
            },
        )

        self.assertEqual(result["action"], "restart")
        self.assertEqual(result["service_ids"], ["svc-1"])
        self.assertEqual(result["result"][0]["service_id"], "svc-1")
        mock_batch_action.assert_called_once_with(
            "rainbond", self.team, self.user, "restart", ["svc-1"], None, None)
        mock_batch_operations.assert_not_called()

    def test_operate_app_schema_limits_supported_actions(self):
        tools = mcp_query_service.list_tools(self.user)
        operate_app_tool = [tool for tool in tools if tool["name"] == "rainbond_operate_app"][0]

        self.assertEqual(
            operate_app_tool["inputSchema"]["properties"]["action"]["enum"],
            ["start", "stop", "restart", "upgrade", "deploy"],
        )

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
    @patch("console.services.mcp_query_service.base_service.get_build_infos")
    @patch("console.services.mcp_query_service.region_api.get_cluster_nodes_arch")
    # capability_id: console.component.build-source-get
    def test_get_component_build_source_returns_sanitized_summary(
            self,
            mock_get_arch,
            mock_get_build_infos,
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
        mock_get_build_infos.return_value = {
            "svc-1": {
                "service_source": "source_code",
                "git_url": "https://git.example.com/demo.git",
                "code_version": "master",
                "server_type": "git",
                "build_env_dict": {"BUILD_TYPE": "cnb"},
                "build_strategy": "cnb",
                "user": "git-user",
                "password": "secret-token",
                "docker_cmd": "",
            }
        }
        mock_get_arch.return_value = (None, {"list": ["amd64", "arm64", "amd64"]})

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_build_source",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
            },
        )

        self.assertEqual(result["service_id"], "svc-1")
        self.assertEqual(result["build_source"]["git_url"], "https://git.example.com/demo.git")
        self.assertEqual(result["build_source"]["username"], "git-user")
        self.assertTrue(result["build_source"]["has_password"])
        self.assertNotIn("password", result["build_source"])
        self.assertNotIn("docker_cmd", result["build_source"])
        self.assertEqual(sorted(result["build_source"]["arch_options"]), ["amd64", "arm64"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch.object(mcp_query_service, "_get_component_build_source_snapshot")
    @patch("console.services.mcp_query_service.service_source_repo.get_service_source")
    @patch("console.services.mcp_query_service.arch_service.update_affinity_by_arch")
    # capability_id: console.component.build-source-update
    def test_update_component_build_source_updates_source_code_fields(
            self,
            mock_update_affinity,
            mock_get_service_source,
            mock_snapshot,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        source_record = Obj(user_name="old-user", password="old-pass", save=lambda: None)
        self.service.service_source = "source_code"
        self.service.git_url = "https://git.example.com/old.git"
        self.service.code_version = "master"
        self.service.server_type = "git"
        self.service.arch = "amd64"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_service_source.return_value = source_record
        mock_snapshot.return_value = {"service_source": "source_code", "git_url": "https://git.example.com/demo.git?dir=services/api"}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_update_component_build_source",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "service_source": "source_code",
                "git_url": "https://git.example.com/demo.git",
                "subdirectories": "services/api",
                "code_version": "v1.0.0",
                "version_type": "tag",
                "server_type": "git",
                "username": "git-user",
                "password": "git-pass",
                "arch": "arm64",
            },
        )

        self.assertTrue(result["updated"])
        self.assertEqual(self.service.git_url, "https://git.example.com/demo.git?dir=services/api")
        self.assertEqual(self.service.code_version, "tag:v1.0.0")
        self.assertEqual(self.service.server_type, "git")
        self.assertEqual(self.service.service_source, "source_code")
        self.assertEqual(self.service.arch, "arm64")
        self.assertEqual(source_record.user_name, "git-user")
        self.assertEqual(source_record.password, "git-pass")
        mock_update_affinity.assert_called_once_with("arm64", self.team, "rainbond", self.service)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch.object(mcp_query_service, "_get_component_build_source_snapshot")
    @patch("console.services.mcp_query_service.service_source_repo.get_service_source")
    @patch("console.services.mcp_query_service.arch_service.update_affinity_by_arch")
    # capability_id: console.component.build-source-update-image-cmd
    def test_update_component_build_source_keeps_cmd_when_omitted_on_image_update(
            self,
            mock_update_affinity,
            mock_get_service_source,
            mock_snapshot,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        # An image component already carrying a start command: an image-only
        # update (no `cmd` argument) must not silently wipe it. The stored
        # service_source is "docker_image" while callers pass "docker_run",
        # so the old inequality check erased cmd on every such call.
        self.service.service_source = "docker_image"
        self.service.cmd = "bundle exec rails server -p 3000"
        self.service.arch = "amd64"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_service_source.return_value = None
        mock_snapshot.return_value = {"service_source": "docker_image"}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_update_component_build_source",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "service_source": "docker_run",
                "image": "chatwoot/chatwoot:v3.0",
            },
        )

        self.assertTrue(result["updated"])
        self.assertEqual(self.service.image, "chatwoot/chatwoot:v3.0")
        self.assertEqual(self.service.cmd, "bundle exec rails server -p 3000")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch.object(mcp_query_service, "_get_component_build_source_snapshot")
    @patch("console.services.mcp_query_service.service_source_repo.get_service_source")
    @patch("console.services.mcp_query_service.arch_service.update_affinity_by_arch")
    # capability_id: console.component.build-source-update-image-cmd
    def test_update_component_build_source_sets_cmd_and_syncs_docker_cmd(
            self,
            mock_update_affinity,
            mock_get_service_source,
            mock_snapshot,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        self.service.service_source = "docker_image"
        self.service.cmd = ""
        self.service.docker_cmd = ""
        self.service.arch = "amd64"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_service_source.return_value = None
        mock_snapshot.return_value = {"service_source": "docker_image"}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_update_component_build_source",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "service_id": "svc-1",
                "service_source": "docker_run",
                "cmd": "bundle exec sidekiq -C config/sidekiq.yml",
            },
        )

        self.assertTrue(result["updated"])
        self.assertEqual(self.service.cmd, "bundle exec sidekiq -C config/sidekiq.yml")
        self.assertEqual(self.service.docker_cmd, "bundle exec sidekiq -C config/sidekiq.yml")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.port_service.add_service_port")
    # capability_id: console.component.port-add-invalid-alias
    def test_handle_component_ports_add_exposes_structured_alias_validation(
            self,
            mock_add_service_port,
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
        mock_add_service_port.return_value = (400, "端口别名不合法", None)

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_handle_component_ports",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_id": 12,
                    "service_id": "svc-1",
                    "operation": "add",
                    "port": 80,
                    "protocol": "TCP",
                    "port_alias": "p80",
                },
            )

        self.assertEqual(context.exception.msg_show, "端口别名不合法")
        self.assertEqual(context.exception.details["field"], "port_alias")
        self.assertEqual(context.exception.details["reason"], "pattern_mismatch")
        self.assertFalse(context.exception.details["retryable"])

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
    @patch("console.services.mcp_query_service.app_version_service.get_overview")
    # capability_id: console.app-version.overview
    def test_get_app_version_overview_returns_version_center_overview(
            self, mock_get_overview, mock_get_app, mock_get_region, mock_get_team):
        region = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = region
        mock_get_app.return_value = self.app
        mock_get_overview.return_value = {"has_template": True, "current_version": "1.0.0", "snapshot_count": 2}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_version_overview",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12},
        )

        self.assertEqual(result["overview"]["current_version"], "1.0.0")
        mock_get_overview.assert_called_once_with(self.team, region, self.user, self.app)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.app_version_service.get_hidden_template")
    @patch("console.services.mcp_query_service.app_version_service.list_snapshot_versions")
    # capability_id: console.app-version.snapshots
    def test_list_app_version_snapshots_returns_versions(
            self, mock_list_snapshots, mock_get_hidden_template, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_hidden_template.return_value = (Obj(app_model_id="hidden-1"), Obj(app_id="hidden-1"))
        mock_list_snapshots.return_value = [{"version_id": 1, "version": "1.0.0"}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_list_app_version_snapshots",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12},
        )

        self.assertTrue(result["has_template"])
        self.assertEqual(result["items"][0]["version"], "1.0.0")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.app_version_service.create_snapshot")
    # capability_id: console.app-version.create-snapshot
    def test_create_app_version_snapshot_calls_app_version_service(
            self, mock_create_snapshot, mock_get_app, mock_get_region, mock_get_team):
        region = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = region
        mock_get_app.return_value = self.app
        mock_create_snapshot.return_value = {"version_id": 1, "version": "1.0.1", "created": True}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_app_version_snapshot",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "version": "1.0.1",
                "version_alias": "stable",
                "app_version_info": "snapshot note",
            },
        )

        self.assertTrue(result["created"])
        mock_create_snapshot.assert_called_once_with(
            self.team, region, self.user, self.app,
            version="1.0.1",
            version_alias="stable",
            app_version_info="snapshot note",
            share_info={},
        )

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.app_version_service.rollback_snapshot")
    @patch("console.services.mcp_query_service.app_version_service.get_rollback_record")
    # capability_id: console.app-version.rollback-snapshot
    def test_rollback_app_version_snapshot_returns_rollback_record(
            self, mock_get_rollback_detail, mock_rollback_snapshot, mock_get_app, mock_get_region, mock_get_team):
        region = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = region
        mock_get_app.return_value = self.app
        mock_rollback_snapshot.return_value = {"ID": 91, "version": "1.0.0"}
        mock_get_rollback_detail.return_value = {"ID": 91, "status": 4, "service_record": []}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_rollback_app_version_snapshot",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "version_id": 3},
        )

        self.assertEqual(result["rollback_record"]["ID"], 91)
        mock_rollback_snapshot.assert_called_once_with(self.team, region, self.user, self.app, 3)
        mock_get_rollback_detail.assert_called_once_with("demo-team", "rainbond", 12, 91)

    @patch.object(mcp_query_service, "install_app_model")
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.app_version_service.get_overview")
    @patch("console.services.mcp_query_service.app_version_service.get_snapshot_detail")
    @patch("console.services.mcp_query_service.group_service.create_app")
    # capability_id: console.app-version.create-app-from-snapshot
    def test_create_app_from_snapshot_version_installs_hidden_template_into_new_app(
            self, mock_create_app, mock_get_snapshot_detail, mock_get_overview, mock_get_app, mock_get_region, mock_get_team, mock_install_app_model):
        region = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = region
        mock_get_app.return_value = self.app
        mock_get_overview.return_value = {"template_id": "hidden-template-id"}
        mock_get_snapshot_detail.return_value = {"version_id": 5, "version": "1.2.3"}
        mock_create_app.return_value = {"app_id": 88, "app_name": "snapshot-copy"}
        mock_install_app_model.return_value = {"installed": True, "app_id": 88}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_app_from_snapshot_version",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "source_app_id": 12,
                "version_id": 5,
                "target_app_name": "snapshot-copy",
                "target_app_note": "from snapshot",
                "is_deploy": True,
            },
        )

        self.assertTrue(result["installed"])
        self.assertEqual(result["snapshot"]["template_id"], "hidden-template-id")
        self.assertEqual(result["snapshot"]["version"], "1.2.3")
        self.assertEqual(result["target_app"]["app_id"], 88)
        mock_create_app.assert_called_once_with(
            self.team,
            "rainbond",
            "snapshot-copy",
            "from snapshot",
            self.user.nick_name,
            k8s_app="",
        )
        mock_install_app_model.assert_called_once_with(
            self.user,
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 88,
                "source": "local",
                "app_model_id": "hidden-template-id",
                "app_model_version": "1.2.3",
                "is_deploy": True,
            },
        )

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.create_app")
    # capability_id: console.gateway.create-app-invalid-display-name
    def test_create_app_returns_structured_details_for_illegal_app_name(
            self, mock_create_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_create_app.side_effect = ServiceHandleException(
            msg="app_name illegal",
            msg_show="应用名称只支持中英文, 数字, 下划线, 中划线和点",
        )

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_app",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "app_name": "demo app",
                },
            )

        self.assertEqual(context.exception.details["field"], "app_name")
        self.assertEqual(context.exception.details["reason"], "pattern_mismatch")
        self.assertEqual(context.exception.details["provided_value"], "demo app")
        self.assertIn("expected_pattern", context.exception.details)
        self.assertEqual(context.exception.details["max_length"], 128)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.app_version_service.get_overview")
    @patch("console.services.mcp_query_service.app_version_service.get_snapshot_detail")
    @patch("console.services.mcp_query_service.group_service.create_app")
    # capability_id: console.app-version.create-app-from-snapshot-invalid-name
    def test_create_app_from_snapshot_version_returns_structured_details_for_illegal_target_app_name(
            self, mock_create_app, mock_get_snapshot_detail, mock_get_overview, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_overview.return_value = {"template_id": "hidden-template-id"}
        mock_get_snapshot_detail.return_value = {"version_id": 5, "version": "1.2.3"}
        mock_create_app.side_effect = ServiceHandleException(
            msg="app_name illegal",
            msg_show="应用名称最多支持128个字符",
        )

        with self.assertRaises(ServiceHandleException) as context:
            mcp_query_service.call_tool(
                self.user,
                "rainbond_create_app_from_snapshot_version",
                {
                    "team_name": "demo-team",
                    "region_name": "rainbond",
                    "source_app_id": 12,
                    "version_id": 5,
                    "target_app_name": "x" * 129,
                },
            )

        self.assertEqual(context.exception.details["field"], "app_name")
        self.assertEqual(context.exception.details["reason"], "too_long")
        self.assertEqual(context.exception.details["provided_value"], "x" * 129)
        self.assertEqual(context.exception.details["max_length"], 128)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.share_service.get_last_shared_app_and_app_list")
    # capability_id: console.app-publish.candidates
    def test_get_app_publish_candidates_returns_models(
            self, mock_get_candidates, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_candidates.return_value = {
            "last_shared_app": {"app_id": "model-1", "version": "1.0.0"},
            "app_model_list": [{"app_id": "model-1", "app_name": "demo-model"}],
        }

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_publish_candidates",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "scope": "local"},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["app_name"], "demo-model")
        mock_get_candidates.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.share_service.check_service_source")
    @patch("console.services.mcp_query_service.app_version_service.get_or_create_hidden_template")
    @patch("console.services.mcp_query_service.share_service.create_service_share_record")
    @patch("console.services.mcp_query_service.rainbond_app_repo.get_rainbond_app_by_app_id")
    @patch("console.services.mcp_query_service.rainbond_app_repo.get_rainbond_app_version_by_record_id")
    # capability_id: console.app-share.create-record
    def test_create_app_share_record_supports_snapshot_mode(
            self, mock_get_record_version, mock_get_hidden_app, mock_create_share_record, mock_hidden_template, mock_check_share, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_check_share.return_value = {"code": 200}
        mock_get_hidden_app.return_value = None
        mock_get_record_version.return_value = None
        hidden_template = Obj(app_id="hidden-model-id")
        mock_hidden_template.return_value = (Obj(app_model_id="hidden-model-id"), hidden_template)
        record = Obj(ID=51, app_id="hidden-model-id", share_version="", share_version_alias="", scope="", share_store_name="", share_app_market_name="", share_app_model_name="", share_app_version_info="", step=1, is_success=False, status=0, create_time=None)
        mock_create_share_record.return_value = record

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_app_share_record",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "snapshot_mode": True},
        )

        self.assertEqual(result["share_record"]["app_model_id"], "hidden-model-id")
        mock_hidden_template.assert_called_once_with(self.team, self.user, self.app)
        mock_create_share_record.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.share_service.get_service_share_record_by_ID")
    @patch("console.services.mcp_query_service.rainbond_app_repo.get_app_version")
    @patch("console.services.mcp_query_service.share_service.is_snapshot_publish_version")
    # capability_id: console.app-share.info
    def test_get_app_share_info_returns_snapshot_payload(
            self, mock_is_snapshot_publish, mock_get_app_version, mock_get_share_record, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        share_record = Obj(ID=61, is_success=False, step=1, scope="", app_id="hidden-model-id", share_version="1.0.1", group_id=12)
        mock_get_share_record.return_value = share_record
        mock_get_app_version.return_value = Obj(app_template=json.dumps({"apps": [{"service_cname": "api"}], "plugins": [{"plugin_alias": "p1"}], "k8s_resources": [{"name": "cfg"}]}))
        mock_is_snapshot_publish.return_value = True

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_share_info",
            {"team_name": "demo-team", "region_name": "rainbond", "share_id": 61},
        )

        self.assertEqual(result["publish_mode"], "snapshot")
        self.assertEqual(result["share_info"]["share_service_list"][0]["service_cname"], "api")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.share_service.get_service_share_record_by_ID")
    @patch("console.services.mcp_query_service.share_service.create_share_info")
    # capability_id: console.app-share.submit-info
    def test_submit_app_share_info_calls_share_service(
            self, mock_create_share_info, mock_get_share_record, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        share_record = Obj(ID=71, is_success=False, step=1, group_id=12)
        mock_get_share_record.return_value = share_record
        mock_create_share_info.return_value = (200, "分享信息处理成功", {"ID": 71, "step": 2})

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_submit_app_share_info",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "share_id": 71,
                "use_force": True,
                "app_version_info": {"app_model_id": "model-1", "version": "1.0.1"},
            },
        )

        self.assertTrue(result["submitted"])
        mock_create_share_info.assert_called_once()

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.share_service.get_service_share_record_by_ID")
    @patch("console.services.mcp_query_service.ServiceShareRecordEvent.objects.filter")
    @patch("console.services.mcp_query_service.PluginShareRecordEvent.objects.filter")
    # capability_id: console.app-share.events
    def test_list_app_share_events_returns_service_and_plugin_events(
            self, mock_plugin_events, mock_service_events, mock_get_share_record, mock_get_team):
        mock_get_team.return_value = self.team
        share_record = Obj(ID=81, is_success=False, step=1)
        mock_get_share_record.return_value = share_record
        service_event = Obj(event_status="success")
        service_event.to_dict = lambda: {"ID": 1, "event_status": "success"}
        plugin_event = Obj(event_status="not_start")
        plugin_event.to_dict = lambda: {"ID": 2, "event_status": "not_start"}
        mock_service_events.return_value = [service_event]
        mock_plugin_events.return_value = [plugin_event]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_list_app_share_events",
            {"team_name": "demo-team", "share_id": 81},
        )

        self.assertEqual(result["total"], 2)
        self.assertFalse(result["is_complete"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.share_service.get_service_share_record_by_ID")
    @patch("console.services.mcp_query_service.ServiceShareRecordEvent.objects.filter")
    @patch("console.services.mcp_query_service.share_service.sync_event")
    # capability_id: console.app-share.start-event
    def test_start_app_share_event_calls_sync_event(
            self, mock_sync_event, mock_filter_events, mock_get_share_record, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        share_record = Obj(ID=91, is_success=False, step=1)
        mock_get_share_record.return_value = share_record
        event = Obj(ID=3, event_status="start")
        event.to_dict = lambda: {"ID": 3, "event_status": "start"}
        mock_filter_events.return_value.first.return_value = event
        mock_sync_event.return_value = event

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_start_app_share_event",
            {"team_name": "demo-team", "region_name": "rainbond", "share_id": 91, "event_id": 3},
        )

        self.assertEqual(result["event"]["ID"], 3)
        mock_sync_event.assert_called_once_with(self.user, "rainbond", "demo-team", event)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.share_service.get_service_share_record_by_ID")
    @patch("console.services.mcp_query_service.ServiceShareRecordEvent.objects.filter")
    @patch("console.services.mcp_query_service.share_service.get_sync_event_result")
    # capability_id: console.app-share.get-event
    def test_get_app_share_event_returns_event_status(
            self, mock_get_event_result, mock_filter_events, mock_get_share_record, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        share_record = Obj(ID=92, is_success=False, step=1)
        mock_get_share_record.return_value = share_record
        event = Obj(ID=4, event_status="start")
        event.to_dict = lambda: {"ID": 4, "event_status": "success"}
        mock_filter_events.return_value.first.return_value = event
        mock_get_event_result.return_value = event

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_share_event",
            {"team_name": "demo-team", "region_name": "rainbond", "share_id": 92, "event_id": 4},
        )

        self.assertEqual(result["event"]["event_status"], "success")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.share_service.get_service_share_record_by_ID")
    @patch("console.services.mcp_query_service.ServiceShareRecordEvent.objects.filter")
    @patch("console.services.mcp_query_service.PluginShareRecordEvent.objects.filter")
    @patch("console.services.mcp_query_service.share_service.complete")
    # capability_id: console.app-share.complete
    def test_complete_app_share_calls_share_service_complete(
            self, mock_complete, mock_plugin_events, mock_service_events, mock_get_share_record, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        share_record = Obj(ID=93, is_success=False, step=2)
        share_record.to_dict = lambda: {"ID": 93, "status": 1}
        mock_get_share_record.return_value = share_record
        mock_service_events.return_value.exclude.return_value.count.return_value = 0
        mock_plugin_events.return_value.exclude.return_value.count.return_value = 0
        mock_complete.return_value = "https://market.example"

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_complete_app_share",
            {"team_name": "demo-team", "region_name": "rainbond", "share_id": 93},
        )

        self.assertTrue(result["completed"])
        self.assertEqual(result["app_market_url"], "https://market.example")
        mock_complete.assert_called_once_with(self.team, self.user, share_record, False, None, "rainbond")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.share_service.get_service_share_record_by_ID")
    @patch("console.services.mcp_query_service.share_service.get_app_version_by_app_id")
    @patch("console.services.mcp_query_service.share_service.get_app_by_key")
    @patch("console.services.mcp_query_service.share_service.delete_record")
    # capability_id: console.app-share.giveup
    def test_giveup_app_share_deletes_draft_record(
            self, mock_delete_record, mock_get_app_by_key, mock_get_versions, mock_get_share_record, mock_get_team):
        mock_get_team.return_value = self.team
        share_record = Obj(ID=94, is_success=False, step=1, app_id="hidden-model-id")
        mock_get_share_record.return_value = share_record
        mock_get_app_by_key.return_value = None
        mock_get_versions.return_value.delete = lambda: None

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_giveup_app_share",
            {"team_name": "demo-team", "share_id": 94},
        )

        self.assertTrue(result["given_up"])
        mock_delete_record.assert_called_once_with(share_record)

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
    @patch("console.services.mcp_query_service.upgrade_service.get_latest_upgrade_record")
    @patch("console.services.mcp_query_service.app_snapshot_repo.get_by_snapshot_id")
    # capability_id: console.app-upgrade.last-record
    def test_get_app_last_upgrade_record_returns_snapshot_metadata(
            self, mock_get_snapshot, mock_get_latest_record, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_latest_record.return_value = {
            "ID": 101,
            "group_id": 12,
            "tenant_id": "team-1",
            "record_type": "upgrade",
            "snapshot_id": "snap-1",
            "status": 2,
        }
        mock_get_snapshot.return_value = Obj(snapshot_id="snap-1")

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_last_upgrade_record",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12},
        )

        self.assertTrue(result["exists"])
        self.assertEqual(result["record"]["ID"], 101)
        self.assertEqual(result["record"]["snapshot"]["snapshot_id"], "snap-1")
        self.assertTrue(result["record"]["snapshot"]["exists"])
        mock_get_latest_record.assert_called_once_with(self.team, self.app, None, None)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_service.list_records")
    # capability_id: console.app-upgrade.records
    def test_query_app_upgrade_records_returns_paginated_items(
            self, mock_list_records, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_list_records.return_value = (
            [{"ID": 201, "group_id": 12, "tenant_id": "team-1", "record_type": "upgrade", "snapshot_id": None}],
            1,
        )

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_app_upgrade_records",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "page": 1, "page_size": 10},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["ID"], 201)
        self.assertEqual(result["record_type"], "upgrade")
        mock_list_records.assert_called_once_with("demo-team", "rainbond", 12, "upgrade", 1, 10)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_service.create_upgrade_record")
    # capability_id: console.app-upgrade.create-record
    def test_create_app_upgrade_record_calls_upgrade_service(
            self, mock_create_record, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_create_record.return_value = {
            "ID": 301,
            "group_id": 12,
            "tenant_id": "team-1",
            "record_type": "upgrade",
            "snapshot_id": None,
        }

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_app_upgrade_record",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "upgrade_group_id": 88,
            },
        )

        self.assertTrue(result["created"])
        self.assertEqual(result["record"]["ID"], 301)
        mock_create_record.assert_called_once_with("eid-1", self.team, self.app, 88)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_repo.get_by_record_id")
    @patch("console.services.mcp_query_service.upgrade_service.get_app_upgrade_record")
    @patch("console.services.mcp_query_service.app_snapshot_repo.get_by_snapshot_id")
    # capability_id: console.app-upgrade.record
    def test_get_app_upgrade_record_returns_record_detail(
            self, mock_get_snapshot, mock_get_record_detail, mock_get_record, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_record.return_value = Obj(ID=401, group_id=12, tenant_id="team-1")
        mock_get_record_detail.return_value = {
            "ID": 401,
            "group_id": 12,
            "tenant_id": "team-1",
            "record_type": "upgrade",
            "snapshot_id": "snap-401",
            "service_record": [{"service_id": "svc-1", "status": 2}],
        }
        mock_get_snapshot.return_value = Obj(snapshot_id="snap-401")

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_upgrade_record",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "record_id": 401},
        )

        self.assertEqual(result["record"]["ID"], 401)
        self.assertEqual(result["record"]["service_record"][0]["service_id"], "svc-1")
        self.assertTrue(result["record"]["snapshot"]["exists"])
        mock_get_record_detail.assert_called_once_with("demo-team", "rainbond", 401)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_repo.get_by_record_id")
    @patch("console.services.mcp_query_service.market_app_service.list_app_upgradeable_versions")
    # capability_id: console.app-upgrade.detail
    def test_get_app_upgrade_detail_returns_record_and_versions(
            self, mock_list_versions, mock_get_record, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_record.return_value = Obj(
            ID=501,
            group_id=12,
            tenant_id="team-1",
            snapshot_id=None,
            record_type="upgrade",
        )
        mock_list_versions.return_value = [{"version": "2.0.0"}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_upgrade_detail",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "record_id": 501},
        )

        self.assertEqual(result["detail"]["record"]["ID"], 501)
        self.assertEqual(result["detail"]["versions"][0]["version"], "2.0.0")
        mock_list_versions.assert_called_once_with("eid-1", mock_get_record.return_value)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_service.get_property_changes")
    # capability_id: console.app-upgrade.changes
    def test_get_app_upgrade_changes_returns_diff_payload(
            self, mock_get_changes, mock_get_app, mock_get_region, mock_get_team):
        region = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = region
        mock_get_app.return_value = self.app
        mock_get_changes.return_value = (
            {"upgrade_info": {"k8s_resources": []}},
            [{"service": {"service_id": "svc-1"}}],
        )

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_upgrade_changes",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "version": "2.0.0",
                "upgrade_group_id": 88,
            },
        )

        self.assertEqual(result["version"], "2.0.0")
        self.assertEqual(result["total"], 1)
        mock_get_changes.assert_called_once_with(self.team, region, self.user, self.app, 88, "2.0.0")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_repo.get_by_record_id")
    @patch("console.services.mcp_query_service.upgrade_service.upgrade")
    @patch("console.services.mcp_query_service.app_snapshot_repo.get_by_snapshot_id")
    # capability_id: console.app-upgrade.execute-record
    def test_execute_app_upgrade_record_calls_upgrade_service(
            self, mock_get_snapshot, mock_upgrade, mock_get_record, mock_get_app, mock_get_region, mock_get_team):
        region = Obj(region_name="rainbond", enterprise_id="eid-1")
        record = Obj(ID=601, group_id=12, tenant_id="team-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = region
        mock_get_app.return_value = self.app
        mock_get_record.return_value = record
        mock_upgrade.return_value = (
            {"ID": 601, "group_id": 12, "tenant_id": "team-1", "snapshot_id": "snap-601", "service_record": []},
            "demo-model",
        )
        mock_get_snapshot.return_value = Obj(snapshot_id="snap-601")

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_execute_app_upgrade_record",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "record_id": 601,
                "version": "2.0.0",
                "services": [{"service": {"service_key": "api"}}],
            },
        )

        self.assertTrue(result["upgraded"])
        self.assertEqual(result["app_template_name"], "demo-model")
        self.assertTrue(result["record"]["snapshot"]["exists"])
        mock_upgrade.assert_called_once_with(self.team, region, self.user, self.app, "2.0.0", record, ["api"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_repo.get_by_record_id")
    @patch("console.services.mcp_query_service.upgrade_service.deploy")
    @patch("console.services.mcp_query_service.upgrade_service.get_app_upgrade_record")
    # capability_id: console.app-upgrade.deploy-record
    def test_deploy_app_upgrade_record_calls_deploy(
            self, mock_get_record_detail, mock_deploy, mock_get_record, mock_get_app, mock_get_region, mock_get_team):
        record = Obj(ID=701, group_id=12, tenant_id="team-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_record.return_value = record
        mock_get_record_detail.return_value = {
            "ID": 701,
            "group_id": 12,
            "tenant_id": "team-1",
            "snapshot_id": None,
            "service_record": [],
        }

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_deploy_app_upgrade_record",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "record_id": 701},
        )

        self.assertTrue(result["deployed"])
        mock_deploy.assert_called_once_with(self.team, "rainbond", self.user, record)
        mock_get_record_detail.assert_called_once_with("demo-team", "rainbond", 701)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_repo.get_by_record_id")
    @patch("console.services.mcp_query_service.upgrade_service.list_rollback_record")
    # capability_id: console.app-upgrade.rollback-records
    def test_get_app_rollback_records_returns_items(
            self, mock_list_rollback, mock_get_record, mock_get_app, mock_get_region, mock_get_team):
        record = Obj(ID=801, group_id=12, tenant_id="team-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_record.return_value = record
        mock_list_rollback.return_value = [{"ID": 802, "group_id": 12, "tenant_id": "team-1", "snapshot_id": None}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_app_rollback_records",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "record_id": 801},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["ID"], 802)
        mock_list_rollback.assert_called_once_with(record)

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.upgrade_repo.get_by_record_id")
    @patch("console.services.mcp_query_service.upgrade_service.restore")
    @patch("console.services.mcp_query_service.app_snapshot_repo.get_by_snapshot_id")
    # capability_id: console.app-upgrade.rollback
    def test_rollback_app_upgrade_record_calls_restore(
            self, mock_get_snapshot, mock_restore, mock_get_record, mock_get_app, mock_get_region, mock_get_team):
        region = Obj(region_name="rainbond", enterprise_id="eid-1")
        record = Obj(ID=901, group_id=12, tenant_id="team-1")
        mock_get_team.return_value = self.team
        mock_get_region.return_value = region
        mock_get_app.return_value = self.app
        mock_get_record.return_value = record
        mock_restore.return_value = (
            {"ID": 902, "group_id": 12, "tenant_id": "team-1", "snapshot_id": "snap-902", "service_record": []},
            "demo-component-group",
        )
        mock_get_snapshot.return_value = Obj(snapshot_id="snap-902")

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_rollback_app_upgrade_record",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "record_id": 901},
        )

        self.assertTrue(result["rolled_back"])
        self.assertEqual(result["component_group_alias"], "demo-component-group")
        self.assertTrue(result["record"]["snapshot"]["exists"])
        mock_restore.assert_called_once_with(self.team, region, self.user, self.app, record)

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

    @patch("console.services.mcp_query_service.app_market_service.get_app_markets")
    # capability_id: console.market.cloud-markets
    def test_query_cloud_markets_returns_market_list(self, mock_get_app_markets):
        mock_get_app_markets.return_value = [{"name": "RainbondMarket", "domain": "rainbond", "url": "https://hub.grapps.cn"}]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_cloud_markets",
            {"enterprise_id": "eid-1", "extend": True},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["name"], "RainbondMarket")
        mock_get_app_markets.assert_called_once_with("eid-1", "true")

    @patch("console.services.mcp_query_service.market_app_service.get_visiable_apps")
    # capability_id: console.market.local-app-models
    def test_query_local_app_models_returns_paginated_templates(self, mock_get_visiable_apps):
        app_model = Obj(
            app_id="model-1",
            app_name="WordPress",
            versions_info=[{"version": "1.0.0"}],
            min_memory=256,
            arch=["amd64"],
        )
        app_model.to_dict = lambda: {"app_id": "model-1", "app_name": "WordPress", "arch": ["amd64"]}
        mock_get_visiable_apps.return_value = ([app_model], 1, ["model-1"])

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_local_app_models",
            {"enterprise_id": "eid-1", "scope": "enterprise", "page": 1, "page_size": 10},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["app_id"], "model-1")
        self.assertEqual(result["items"][0]["versions_info"][0]["version"], "1.0.0")
        self.assertEqual(result["items"][0]["min_memory"], 256)
        mock_get_visiable_apps.assert_called_once_with("enterprise", None, True, 1, 10, "", "", "", None)

    @patch("console.services.mcp_query_service.app_market_service.get_market_app_list")
    @patch("console.services.mcp_query_service.app_market_service.get_app_market")
    # capability_id: console.market.cloud-app-models
    def test_query_cloud_app_models_returns_market_templates(self, mock_get_app_market, mock_get_market_app_list):
        market = Obj(name="RainbondMarket")
        mock_get_app_market.return_value = ({"name": "RainbondMarket"}, market)
        mock_get_market_app_list.return_value = ([{"app_id": "model-1", "app_name": "Redis"}], 1, 10, 1)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_cloud_app_models",
            {"enterprise_id": "eid-1", "market_name": "RainbondMarket", "page": 1, "page_size": 10},
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["app_name"], "Redis")
        mock_get_market_app_list.assert_called_once_with(market, 1, 10, query=None, query_all=False, extend=True, arch="")

    @patch("console.services.mcp_query_service.market_app_service.get_rainbond_app_and_versions")
    # capability_id: console.market.app-model-versions-local
    def test_query_app_model_versions_for_local_returns_versions(self, mock_get_versions):
        app_model = {"app_id": "model-1", "app_name": "WordPress"}
        versions = [{"version": "1.0.0"}, {"version": "1.1.0"}]
        mock_get_versions.return_value = (app_model, versions, 2)

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_query_app_model_versions",
            {"enterprise_id": "eid-1", "source": "local", "app_model_id": "model-1", "page": 1, "page_size": 10},
        )

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["app_model"]["app_name"], "WordPress")
        self.assertEqual(result["items"][1]["version"], "1.1.0")
        mock_get_versions.assert_called_once_with("eid-1", "model-1", 1, 10)

    @patch("console.services.mcp_query_service.group_service.get_group_services")
    @patch("console.services.mcp_query_service.market_app_service.install_app")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    # capability_id: console.market.install-app-model-cloud
    def test_install_app_model_for_cloud_calls_market_app_service(
            self,
            mock_get_team,
            mock_get_region,
            mock_get_app,
            mock_install_app,
            mock_get_group_services,
    ):
        installed_service = Obj(service_id="svc-1")
        installed_service.to_dict = lambda: {"service_id": "svc-1"}
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_install_app.return_value = "Redis"
        mock_get_group_services.return_value = [installed_service]

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_install_app_model",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "source": "cloud",
                "market_name": "RainbondMarket",
                "app_model_id": "model-1",
                "app_model_name": "Redis",
                "app_model_version": "1.0.0",
                "is_deploy": True,
            },
        )

        self.assertTrue(result["installed"])
        self.assertEqual(result["installed_app_name"], "Redis")
        self.assertEqual(result["service_list"][0]["service_id"], "svc-1")
        mock_install_app.assert_called_once_with(
            self.team, mock_get_region.return_value, self.user, 12, "model-1", "1.0.0", "RainbondMarket", True, True
        )

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
    @patch("console.services.mcp_query_service.source_component_service.auto_create_component")
    # capability_id: console.component.create-from-source-prefer-dockerfile
    def test_create_component_from_source_passes_prefer_dockerfile_flag(
            self, mock_auto_create, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_auto_create.return_value = {"service_id": "svc-1", "built": True}

        mcp_query_service.call_tool(
            self.user,
            "rainbond_create_component_from_source",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "code_from": "git",
                "service_cname": "demo-2048",
                "git_url": "https://gitee.com/rainbond/demo-2048.git",
                "prefer_dockerfile_when_detected": True,
            },
        )

        self.assertTrue(mock_auto_create.call_args[1]["prefer_dockerfile_when_detected"])

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
    @patch("console.services.mcp_query_service.package_upload_tool_service.init_upload")
    # capability_id: console.package-upload.init
    def test_init_package_upload_delegates_to_upload_tool_service(self, mock_init_upload, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_init_upload.return_value = {"event_id": "evt-upload-1", "upload_url": "http://upload"}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_init_package_upload",
            {"team_name": "demo-team", "region_name": "rainbond"},
        )

        self.assertEqual(result["event_id"], "evt-upload-1")
        mock_init_upload.assert_called_once_with("demo-team", "rainbond", "")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.package_upload_tool_service.upload_package")
    # capability_id: console.package-upload.file
    def test_upload_package_file_delegates_to_upload_tool_service(self, mock_upload_package, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_upload_package.return_value = {"event_id": "evt-upload-1", "uploaded_packages": ["demo.zip"], "uploaded": True}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_upload_package_file",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "event_id": "evt-upload-1",
                "local_path": "/tmp/demo",
                "archive_name": "demo-package",
            },
        )

        self.assertTrue(result["uploaded"])
        mock_upload_package.assert_called_once_with("demo-team", "rainbond", "evt-upload-1", "/tmp/demo", "demo-package")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.package_upload_tool_service.get_upload_status")
    # capability_id: console.package-upload.status
    def test_get_package_upload_status_delegates_to_upload_tool_service(self, mock_get_upload_status, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_upload_status.return_value = {"event_id": "evt-upload-1", "uploaded_packages": ["demo.zip"], "uploaded": True}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_package_upload_status",
            {"team_name": "demo-team", "region_name": "rainbond", "event_id": "evt-upload-1"},
        )

        self.assertEqual(result["uploaded_packages"], ["demo.zip"])
        mock_get_upload_status.assert_called_once_with("demo-team", "rainbond", "evt-upload-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.package_upload_tool_service.delete_upload")
    # capability_id: console.package-upload.delete
    def test_delete_package_upload_delegates_to_upload_tool_service(self, mock_delete_upload, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_delete_upload.return_value = {"event_id": "evt-upload-1", "deleted": True}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_delete_package_upload",
            {"team_name": "demo-team", "region_name": "rainbond", "event_id": "evt-upload-1"},
        )

        self.assertTrue(result["deleted"])
        mock_delete_upload.assert_called_once_with("demo-team", "rainbond", "evt-upload-1")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.package_upload_tool_service.auto_create_component_from_local_path")
    # capability_id: console.package-upload.local-package
    def test_create_component_from_local_package_calls_upload_tool_service(
            self, mock_auto_create, mock_get_app, mock_get_region, mock_get_team):
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_auto_create.return_value = {"service_id": "svc-local-pkg-1", "built": True, "upload_event_id": "evt-upload-1"}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_create_component_from_local_package",
            {
                "team_name": "demo-team",
                "region_name": "rainbond",
                "app_id": 12,
                "local_path": "/tmp/demo-app",
                "service_cname": "demo-app",
                "is_deploy": True,
            },
        )

        self.assertTrue(result["built"])
        self.assertEqual(result["service_id"], "svc-local-pkg-1")
        mock_auto_create.assert_called_once_with(
            team=self.team,
            app=self.app,
            user=self.user,
            local_path="/tmp/demo-app",
            service_cname="demo-app",
            k8s_component_name="",
            arch="amd64",
            is_deploy=True,
            archive_name="",
        )

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
    @patch("console.services.mcp_query_service.app_check_service.get_service_check_info")
    @patch("console.services.mcp_query_service.app_check_service.save_service_check_info")
    @patch("console.services.mcp_query_service.app_check_service.wrap_service_check_info")
    # capability_id: console.component.check-result
    def test_get_component_check_result_prefer_dockerfile_forces_dockerfile(
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
        # Recovery path: a CNB-classified language (.NetCore) that ships a
        # Dockerfile must persist as a Dockerfile build when the caller passes
        # prefer_dockerfile_when_detected, so it does not dead-end on the CNB
        # version policy (e.g. .NET 7).
        self.service.service_source = "source_code"
        self.service.create_status = "checked"  # != complete -> else branch
        self.service.check_uuid = "chk-1"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_check_info.return_value = (
            200, "success",
            {"check_status": "success", "error_infos": [],
             "service_info": [{"language": ".NetCore", "dockerfiles": ["Dockerfile"]}]},
        )
        captured = {}

        def cap_save(team, app_id, service, data):
            captured["data"] = data
            service.create_status = "checked"

        mock_save_check_info.side_effect = cap_save
        mock_wrap_check_info.return_value = {"check_status": "success", "error_infos": [], "service_info": []}

        mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_check_result",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12,
             "service_id": "svc-1", "prefer_dockerfile_when_detected": True},
        )

        # _select_service_info rewrote the detected language to "dockerfile"
        # before persistence, so build_strategy will resolve to non-CNB.
        self.assertEqual(captured["data"]["service_info"][0]["language"], "dockerfile")

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.app_check_service.get_service_check_info")
    @patch("console.services.mcp_query_service.app_check_service.save_service_check_info")
    @patch("console.services.mcp_query_service.app_check_service.wrap_service_check_info")
    @patch("console.services.mcp_query_service.source_component_service.load_dockerfile_preference")
    # capability_id: console.component.check-result
    def test_get_component_check_result_applies_persisted_dockerfile_preference(
            self,
            mock_load_preference,
            mock_wrap_check_info,
            mock_save_check_info,
            mock_get_check_info,
            mock_relations,
            mock_get_service,
            mock_get_app,
            mock_get_region,
            mock_get_team,
    ):
        # The create call timed out on detection and persisted the Dockerfile
        # preference; the follow-up check-result call must auto-apply it even
        # when the caller does not re-pass prefer_dockerfile_when_detected.
        self.service.service_source = "source_code"
        self.service.create_status = "checked"
        self.service.check_uuid = "chk-1"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_load_preference.return_value = True
        mock_get_check_info.return_value = (
            200, "success",
            {"check_status": "success", "error_infos": [],
             "service_info": [{"language": "Go", "dockerfiles": ["Dockerfile"]}]},
        )
        captured = {}

        def cap_save(team, app_id, service, data):
            captured["data"] = data
            service.create_status = "checked"

        mock_save_check_info.side_effect = cap_save
        mock_wrap_check_info.return_value = {"check_status": "success", "error_infos": [], "service_info": []}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_check_result",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12, "service_id": "svc-1"},
        )

        self.assertEqual(captured["data"]["service_info"][0]["language"], "dockerfile")
        self.assertTrue(result["prefer_dockerfile_when_detected"])
        self.assertTrue(result["dockerfile_preference_applied"])

    @patch("console.services.mcp_query_service.team_services.get_enterprise_tenant_by_tenant_name")
    @patch("console.services.mcp_query_service.region_services.get_enterprise_region_by_region_name")
    @patch("console.services.mcp_query_service.group_service.get_app_by_id")
    @patch("console.services.mcp_query_service.service_repo.get_service_by_service_id")
    @patch("console.services.mcp_query_service.group_service_relation_repo.get_services_by_group")
    @patch("console.services.mcp_query_service.app_check_service.get_service_check_info")
    @patch("console.services.mcp_query_service.app_check_service.save_service_check_info")
    @patch("console.services.mcp_query_service.app_check_service.wrap_service_check_info")
    # capability_id: console.component.check-result
    def test_get_component_check_result_reports_unapplied_dockerfile_preference(
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
        # The caller asked for a Dockerfile build but detection found no
        # Dockerfile at the build root: the preference silently no-ops in
        # _select_service_info, so the response must surface that fallback.
        self.service.service_source = "source_code"
        self.service.create_status = "checked"
        self.service.check_uuid = "chk-1"
        mock_get_team.return_value = self.team
        mock_get_region.return_value = Obj(region_name="rainbond", enterprise_id="eid-1")
        mock_get_app.return_value = self.app
        mock_get_service.return_value = self.service
        mock_relations.return_value = [Obj(service_id="svc-1")]
        mock_get_check_info.return_value = (
            200, "success",
            {"check_status": "success", "error_infos": [], "service_info": [{"language": "Go"}]},
        )

        def mark_checked(team, app_id, service, data):
            service.create_status = "checked"

        mock_save_check_info.side_effect = mark_checked
        mock_wrap_check_info.return_value = {"check_status": "success", "error_infos": [], "service_info": []}

        result = mcp_query_service.call_tool(
            self.user,
            "rainbond_get_component_check_result",
            {"team_name": "demo-team", "region_name": "rainbond", "app_id": 12,
             "service_id": "svc-1", "prefer_dockerfile_when_detected": True},
        )

        self.assertTrue(result["prefer_dockerfile_when_detected"])
        self.assertFalse(result["dockerfile_preference_applied"])
        self.assertTrue(result["build_mode_note"])

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

    @patch("console.services.mcp_query_service.group_service.delete_app_with_resources")
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
        mock_delete_app.assert_called_once_with(self.user, self.tenant, self.app.region_name, self.app)

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


class MCPQueryServiceSerializeModelItemTests(SimpleTestCase):

    # capability_id: console.mcp.serialize-nested-sdk-models
    def test_serialize_model_item_recurses_into_dict_values(self):
        class FakeSDKModel(object):
            def __init__(self, value):
                self.value = value

            def to_dict(self):
                return {"value": self.value}

        nested = {
            "app_id": "abc",
            "versions": [FakeSDKModel("v1"), FakeSDKModel("v2")],
            "meta": {"latest": FakeSDKModel("v2")},
        }

        result = mcp_query_service._serialize_model_item(nested)

        self.assertEqual(result["app_id"], "abc")
        self.assertEqual(result["versions"], [{"value": "v1"}, {"value": "v2"}])
        self.assertEqual(result["meta"], {"latest": {"value": "v2"}})
        json.dumps(result)

    def test_serialize_model_item_handles_object_with_nested_sdk_attribute(self):
        class FakeSDKModel(object):
            def to_dict(self):
                return {"k": "v"}

        class Container(object):
            def __init__(self):
                self.name = "demo"
                self.payload = FakeSDKModel()

        result = mcp_query_service._serialize_model_item(Container())

        self.assertEqual(result, {"name": "demo", "payload": {"k": "v"}})


class MCPQueryServiceCreateAppFromSnapshotVersionTests(SimpleTestCase):

    @patch("console.services.mcp_query_service.group_service")
    def test_create_app_from_snapshot_version_raises_on_invalid_app_id(self, mock_group_service):
        """When created_app returns a non-integer ID, a ServiceHandleException
        should be raised with '应用ID格式无效' message."""
        user = Obj(
            user_id=1,
            enterprise_id="eid-1",
            nick_name="testuser",
            real_name="Test User",
            email="test@example.com",
            is_active=True,
            is_enterprise_admin=True,
        )

        # Resolve the team/app/region context and snapshot lookups in-memory so the
        # SimpleTestCase never touches the database. The created app carries a
        # non-integer ID to trigger the validation failure under test.
        team = Obj(tenant_name="team", tenant_id="tid-1")
        source_app = Obj(ID=123, group_name="source-app")
        region = Obj(region_name="region")
        mock_created_app = Obj(ID="not-a-number", app_id=None, group_id=None)

        with patch.object(mcp_query_service, "_get_team_app_context", return_value=(team, source_app)), \
                patch.object(mcp_query_service, "_get_region_by_name_context", return_value=region), \
                patch("console.services.mcp_query_service.app_version_service") as mock_app_version_service, \
                patch.object(mcp_query_service, "_create_app_with_mcp_error_details", return_value=mock_created_app):
            mock_app_version_service.get_overview.return_value = {"template_id": "tpl-1"}
            mock_app_version_service.get_snapshot_detail.return_value = {"version": "v1"}

            with self.assertRaises(ServiceHandleException) as ctx:
                mcp_query_service.create_app_from_snapshot_version(
                    user=user,
                    arguments={
                        "team_name": "team",
                        "region_name": "region",
                        "source_app_id": 123,
                        "version_id": 456,
                        "target_app_name": "target-app",
                    },
                )

        self.assertIn("应用ID格式无效", str(ctx.exception))
