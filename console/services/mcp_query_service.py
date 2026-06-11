# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os

from django.core import signing
from django.core.exceptions import ObjectDoesNotExist

from console.constants import PluginCategoryConstants
from console.models.main import PluginShareRecordEvent, ServiceShareRecordEvent
from console.exception.exceptions import ExterpriseNotExistError, TenantNotExistError
from console.exception.main import ServiceHandleException
from console.repositories.app import service_repo, service_source_repo
from console.repositories.app_config import volume_repo, compile_env_repo, env_var_repo
from console.repositories.app_snapshot import app_snapshot_repo
from console.repositories.deploy_repo import deploy_repo
from console.repositories.enterprise_repo import enterprise_repo, enterprise_user_perm_repo
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.oauth_repo import oauth_repo, oauth_user_repo
from console.repositories.share_repo import share_repo
from console.repositories.team_repo import team_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.services.app import app_service as console_app_service, app_market_service
from console.services.app_actions import app_manage_service, event_service, log_service
from console.services.app_check_service import app_check_service
from console.services.app_version_service import app_version_service
from console.services.app_config import domain_service, env_var_service, port_service, volume_service, mnt_service, probe_service, dependency_service
from console.services.autoscaler_service import autoscaler_service, scaling_records_service
from console.services.app_config.arch_service import arch_service
from console.services.compose_service import compose_service
from console.services.enterprise_services import enterprise_services
from console.services.gateway_api import gateway_api
from console.services.group_service import group_service
from console.services.groupcopy_service import groupapp_copy_service
from console.services.helm_app_yaml import helm_app_service
from console.services.market_app_service import market_app_service
from console.services.package_component_service import package_component_service
from console.services.package_upload_tool_service import package_upload_tool_service
from console.services.plugin import app_plugin_service
from console.services.region_services import region_services
from console.services.service_services import base_service
from console.services.share_services import share_service
from console.services.source_component_service import source_component_service
from console.services.team_services import team_services
from console.services.upgrade_services import upgrade_service
from console.utils.source_build_state import build_compile_env_payload, read_compile_env_state
from console.utils.oauth.oauth_types import get_oauth_instance
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()

monitor_query_items = {
    "request_time": '?query=ceil(avg(app_requesttime{mode="avg",service_id="%s"}))',
    "request": '?query=sum(ceil(increase(app_request{service_id="%s",method="total"}[1m])/12))',
    "request_client": '?query=max(app_requestclient{service_id="%s"})',
}

monitor_query_range_items = {
    "request_time": '?query=ceil(avg(app_requesttime{mode="avg",service_id="%s"}))&start=%s&end=%s&step=%s',
    "request": '?query=sum(ceil(increase(app_request{service_id="%s",method="total"}[1m])/12))&start=%s&end=%s&step=%s',
    "request_client": '?query=max(app_requestclient{service_id="%s"})&start=%s&end=%s&step=%s',
}


class MCPQueryService(object):
    CONFIRM_SALT = "console.mcp.delete_app"
    CONFIRM_MAX_AGE_SECONDS = 300
    MAX_PAGE_SIZE = 200
    DISPLAY_APP_NAME_PATTERN = r"^[a-zA-Z0-9_\.\-\u4e00-\u9fa5]+$"
    DISPLAY_APP_NAME_MAX_LENGTH = 128
    DISPLAY_APP_NAME_DESCRIPTION = (
        "应用展示名称。支持中文、英文、数字、下划线、中划线和点；"
        "长度不超过128个字符；"
        "不支持空格、斜杠、括号、emoji 等其他特殊字符。"
    )
    SERVER_LOCAL_PATH_DESCRIPTION = (
        "本地文件或目录路径。该路径必须能被 rainbond-console 进程所在机器或容器直接访问；"
        "若传目录，会先压缩为 zip 后再上传；"
        "这里的 local_path 不是 MCP 客户端本机路径。"
    )
    PORT_ALIAS_PATTERN = r"^[A-Z][A-Z0-9_]*$"
    PORT_ALIAS_DESCRIPTION = (
        "端口别名。新增端口时通常不必传，留空由系统自动生成；"
        "若手动填写，必须以大写字母开头，"
        "只能包含大写字母、数字和下划线，例如 WEB、P80、METRICS_8080。"
    )
    K8S_SERVICE_NAME_PATTERN = r"^[a-z]([-a-z0-9]*[a-z0-9])?$"
    K8S_SERVICE_NAME_DESCRIPTION = (
        "内部域名。若手动填写，必须以小写字母开头，只能包含小写字母、数字和连字符，"
        "且长度不超过63，"
        "例如 web、api-80。"
    )
    K8S_APP_NAME_PATTERN = r"^[a-z]([-a-z0-9]*[a-z0-9])?$"
    K8S_APP_NAME_DESCRIPTION = (
        "应用英文名 / K8s app name。默认建议不传，由系统生成或在后端回填；"
        "若手动填写，必须以小写字母开头，只能包含小写字母、数字和连字符，"
        "并且在同团队同集群下唯一，例如 demo-app。"
    )
    IMAGE_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION = (
        "默认资源规范：镜像创建组件在生成时默认使用 512MB 内存和 0m CPU；"
        "若后续未做手动调整，构建和部署阶段继续沿用该默认资源。"
    )
    SOURCE_PACKAGE_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION = (
        "默认资源规范：源码/软件包组件在生成时默认使用 128MB 内存，"
        "CPU 按 memory/128*20 计算；检测成功后，默认资源会规范化为"
        "“检测内存值向下对齐到 32MB 整数倍 + 500m CPU”。"
    )
    BUILD_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION = (
        "默认资源说明：本步骤不会重新计算默认资源，"
        "而是沿用组件当前的 min_memory/min_cpu。"
    )
    PORT_ACTION_ENUM = (
        "open_outer", "only_open_outer", "close_outer", "open_inner",
        "close_inner", "change_protocol", "change_port_alias"
    )
    PORT_ACTION_ALIASES = {
        "open_public": "open_outer",
        "open_outer": "open_outer",
        "open_only_public": "only_open_outer",
        "only_open_outer": "only_open_outer",
        "close_public": "close_outer",
        "close_outer": "close_outer",
        "open_private": "open_inner",
        "open_inner": "open_inner",
        "close_private": "close_inner",
        "close_inner": "close_inner",
        "update_protocol": "change_protocol",
        "change_protocol": "change_protocol",
        "update_port_alias": "change_port_alias",
        "rename_port": "change_port_alias",
        "change_port_alias": "change_port_alias",
    }
    ENV_SCOPE_ALIASES = {
        "inner": "inner",
        "local": "inner",
        "self": "inner",
        "runtime": "inner",
    }
    ENV_OPERATION_ALIASES = {
        "summary": "summary",
        "list": "summary",
        "view": "summary",
        "upsert": "upsert",
        "set": "upsert",
        "batch_upsert": "upsert",
        "create": "create",
        "add": "create",
        "update": "update",
        "edit": "update",
        "delete": "delete",
        "remove": "delete",
        "patch_scope": "patch_scope",
        "change_scope": "patch_scope",
        "replace_build_envs": "replace_build_envs",
        "set_build_envs": "replace_build_envs",
        "update_build_envs": "replace_build_envs",
    }
    HIGH_LEVEL_PORT_OPERATION_ALIASES = {
        "summary": "summary",
        "list": "summary",
        "view": "summary",
        "add": "add",
        "create": "add",
        "update": "update",
        "edit": "update",
        "delete": "delete",
        "remove": "delete",
        "enable_inner": "enable_inner",
        "open_inner": "enable_inner",
        "inner_on": "enable_inner",
        "disable_inner": "disable_inner",
        "close_inner": "disable_inner",
        "inner_off": "disable_inner",
        "enable_outer": "enable_outer",
        "open_outer": "enable_outer",
        "outer_on": "enable_outer",
        "disable_outer": "disable_outer",
        "close_outer": "disable_outer",
        "outer_off": "disable_outer",
        "enable_outer_only": "enable_outer_only",
        "only_open_outer": "enable_outer_only",
        "outer_only": "enable_outer_only",
        "update_protocol": "update_protocol",
        "change_protocol": "update_protocol",
        "update_alias": "update_alias",
        "change_port_alias": "update_alias",
        "rename_port": "update_alias",
    }
    STORAGE_OPERATION_ALIASES = {
        "summary": "summary",
        "list": "summary",
        "view": "summary",
        "list_unmounted": "list_unmounted",
        "list_available_mounts": "list_unmounted",
        "create_volume": "create_volume",
        "add_volume": "create_volume",
        "update_volume": "update_volume",
        "edit_volume": "update_volume",
        "delete_volume": "delete_volume",
        "remove_volume": "delete_volume",
        "create_mnt": "create_mnt",
        "add_mount": "create_mnt",
        "delete_mnt": "delete_mnt",
        "remove_mount": "delete_mnt",
    }
    AUTOSCALER_OPERATION_ALIASES = {
        "summary": "summary",
        "list": "summary",
        "view": "summary",
        "get_rule": "get_rule",
        "detail": "get_rule",
        "create_rule": "create_rule",
        "create": "create_rule",
        "update_rule": "update_rule",
        "update": "update_rule",
        "edit": "update_rule",
        "records": "records",
        "history": "records",
        "logs": "records",
    }
    PROBE_OPERATION_ALIASES = {
        "summary": "summary",
        "list": "summary",
        "view": "summary",
        "get": "get",
        "detail": "get",
        "create": "create",
        "add": "create",
        "update": "update",
        "edit": "update",
        "delete": "delete",
        "remove": "delete",
    }
    APP_MODEL_SOURCE_ALIASES = {
        "local": "local",
        "template": "local",
        "enterprise": "local",
        "cloud": "cloud",
        "market": "cloud",
        "cloud_market": "cloud",
    }
    DEPENDENCY_OPERATION_ALIASES = {
        "summary": "summary",
        "list": "summary",
        "view": "summary",
        "add": "add",
        "create": "add",
        "add_reverse": "add_reverse",
        "create_reverse": "add_reverse",
        "delete": "delete",
        "remove": "delete",
    }

    def list_tools(self, user=None):
        tools = [
            self._tool_get_current_user(), self._tool_get_app_detail(), self._tool_create_app(),
            self._tool_get_component_summary(), self._tool_get_component_detail(),
            self._tool_get_component_pods(), self._tool_get_pod_detail(),
            self._tool_get_component_logs(), self._tool_exec_component(), self._tool_get_config_file(),
            self._tool_get_component_events(), self._tool_get_component_build_logs(),
            self._tool_get_component_build_source(), self._tool_update_component_build_source(),
            self._tool_create_component(),
            self._tool_delete_component(), self._tool_operate_app(), self._tool_manage_component_envs(),
            self._tool_manage_component_connection_envs(),
            self._tool_change_component_image(), self._tool_manage_component_ports(),
            self._tool_manage_component_storage(),
            self._tool_manage_component_autoscaler(), self._tool_manage_component_probe(),
            self._tool_manage_component_dependency(), self._tool_horizontal_scale_component(),
            self._tool_vertical_scale_component(), self._tool_close_apps(), self._tool_get_team_apps(),
            self._tool_get_app_version_overview(), self._tool_list_app_version_snapshots(),
            self._tool_get_app_version_snapshot_detail(), self._tool_create_app_version_snapshot(),
            self._tool_delete_app_version_snapshot(), self._tool_rollback_app_version_snapshot(),
            self._tool_list_app_version_rollback_records(), self._tool_get_app_version_rollback_record_detail(),
            self._tool_delete_app_version_rollback_record(), self._tool_create_app_from_snapshot_version(),
            self._tool_get_app_publish_candidates(),
            self._tool_create_app_share_record(), self._tool_list_app_share_records(),
            self._tool_get_app_share_record(), self._tool_delete_app_share_record(),
            self._tool_get_app_share_info(), self._tool_submit_app_share_info(),
            self._tool_list_app_share_events(), self._tool_start_app_share_event(),
            self._tool_get_app_share_event(), self._tool_complete_app_share(),
            self._tool_giveup_app_share(),
            self._tool_build_component(), self._tool_get_app_last_upgrade_record(),
            self._tool_query_app_upgrade_records(), self._tool_create_app_upgrade_record(),
            self._tool_get_app_upgrade_record(), self._tool_get_app_upgrade_detail(),
            self._tool_get_app_upgrade_changes(), self._tool_execute_app_upgrade_record(),
            self._tool_deploy_app_upgrade_record(), self._tool_get_app_rollback_records(),
            self._tool_rollback_app_upgrade_record(), self._tool_get_app_upgrade_info(), self._tool_upgrade_app(),
            self._tool_get_copy_app_info(), self._tool_copy_app(), self._tool_install_app_by_market(),
            self._tool_query_cloud_markets(), self._tool_query_local_app_models(), self._tool_query_cloud_app_models(),
            self._tool_query_app_model_versions(), self._tool_install_app_model(),
            self._tool_create_component_from_source(), self._tool_create_component_from_package(),
            self._tool_init_package_upload(), self._tool_upload_package_file(),
            self._tool_get_package_upload_status(), self._tool_delete_package_upload(),
            self._tool_create_component_from_local_package(),
            self._tool_check_component(), self._tool_get_component_check_result(),
            self._tool_create_component_from_image(),
            self._tool_create_app_from_yaml(), self._tool_check_yaml_app(), self._tool_get_yaml_app_check_result(),
            self._tool_query_app_monitor(), self._tool_query_app_monitor_range(),
            self._tool_create_gateway_rules(), self._tool_check_helm_app(), self._tool_build_helm_app(),
            self._tool_query_teams(), self._tool_query_apps(), self._tool_query_components(), self._tool_delete_app()
        ]
        if self._is_enterprise_admin(user):
            tools = [
                self._tool_query_enterprises(), self._tool_query_regions(), self._tool_get_region_detail(),
                self._tool_create_region(), self._tool_update_region(), self._tool_delete_region(),
                self._tool_query_region_nodes(), self._tool_get_region_node_detail(),
                self._tool_query_region_rbd_components()
            ] + tools
        return tools

    def call_tool(self, user, name, arguments=None):
        arguments = arguments or {}

        if name == "rainbond_get_current_user":
            return self.get_current_user(user)
        if name == "rainbond_get_app_detail":
            return self.get_app_detail(user, arguments)
        if name == "rainbond_create_app":
            return self.create_app(user, arguments)
        if name == "rainbond_get_component_summary":
            return self.get_component_summary(user, arguments)
        if name == "rainbond_get_component_pods":
            return self.get_component_pods(user, arguments)
        if name == "rainbond_get_pod_detail":
            return self.get_pod_detail(user, arguments)
        if name == "rainbond_get_component_logs":
            return self.get_component_logs(user, arguments)
        if name == "rainbond_exec":
            return self.exec_component(user, arguments)
        if name == "rainbond_get_config_file":
            return self.get_config_file(user, arguments)
        if name == "rainbond_get_component_build_logs":
            return self.get_component_build_logs(user, arguments)
        if name == "rainbond_get_component_build_source":
            return self.get_component_build_source(user, arguments)
        if name == "rainbond_update_component_build_source":
            return self.update_component_build_source(user, arguments)
        if name == "rainbond_get_component_detail":
            return self.get_component_detail(user, arguments)
        if name == "rainbond_get_component_events":
            return self.get_component_events(user, arguments)
        if name == "rainbond_create_component":
            return self.create_component(user, arguments)
        if name == "rainbond_delete_component":
            return self.delete_component(user, arguments)
        if name == "rainbond_operate_app":
            return self.operate_app(user, arguments)
        if name == "rainbond_manage_component_envs":
            return self.manage_component_envs(user, arguments)
        if name == "rainbond_manage_component_connection_envs":
            return self.manage_component_connection_envs(user, arguments)
        if name == "rainbond_update_component_envs":
            return self.update_component_envs(user, arguments)
        if name == "rainbond_change_component_image":
            return self.change_component_image(user, arguments)
        if name == "rainbond_manage_component_ports":
            return self.manage_component_ports(user, arguments)
        if name == "rainbond_handle_component_ports":
            return self.handle_component_ports(user, arguments)
        if name == "rainbond_bind_component_volume":
            return self.bind_component_volume(user, arguments)
        if name == "rainbond_manage_component_storage":
            return self.manage_component_storage(user, arguments)
        if name == "rainbond_manage_component_autoscaler":
            return self.manage_component_autoscaler(user, arguments)
        if name == "rainbond_manage_component_probe":
            return self.manage_component_probe(user, arguments)
        if name == "rainbond_manage_component_dependency":
            return self.manage_component_dependency(user, arguments)
        if name == "rainbond_horizontal_scale_component":
            return self.horizontal_scale_component(user, arguments)
        if name == "rainbond_vertical_scale_component":
            return self.vertical_scale_component(user, arguments)
        if name == "rainbond_close_apps":
            return self.close_apps(user, arguments)
        if name == "rainbond_get_team_apps":
            return self.get_team_apps(user, arguments)
        if name == "rainbond_get_app_version_overview":
            return self.get_app_version_overview(user, arguments)
        if name == "rainbond_list_app_version_snapshots":
            return self.list_app_version_snapshots(user, arguments)
        if name == "rainbond_get_app_version_snapshot_detail":
            return self.get_app_version_snapshot_detail(user, arguments)
        if name == "rainbond_create_app_version_snapshot":
            return self.create_app_version_snapshot(user, arguments)
        if name == "rainbond_delete_app_version_snapshot":
            return self.delete_app_version_snapshot(user, arguments)
        if name == "rainbond_rollback_app_version_snapshot":
            return self.rollback_app_version_snapshot(user, arguments)
        if name == "rainbond_list_app_version_rollback_records":
            return self.list_app_version_rollback_records(user, arguments)
        if name == "rainbond_get_app_version_rollback_record_detail":
            return self.get_app_version_rollback_record_detail(user, arguments)
        if name == "rainbond_delete_app_version_rollback_record":
            return self.delete_app_version_rollback_record(user, arguments)
        if name == "rainbond_create_app_from_snapshot_version":
            return self.create_app_from_snapshot_version(user, arguments)
        if name == "rainbond_get_app_publish_candidates":
            return self.get_app_publish_candidates(user, arguments)
        if name == "rainbond_create_app_share_record":
            return self.create_app_share_record(user, arguments)
        if name == "rainbond_list_app_share_records":
            return self.list_app_share_records(user, arguments)
        if name == "rainbond_get_app_share_record":
            return self.get_app_share_record(user, arguments)
        if name == "rainbond_delete_app_share_record":
            return self.delete_app_share_record(user, arguments)
        if name == "rainbond_get_app_share_info":
            return self.get_app_share_info(user, arguments)
        if name == "rainbond_submit_app_share_info":
            return self.submit_app_share_info(user, arguments)
        if name == "rainbond_list_app_share_events":
            return self.list_app_share_events(user, arguments)
        if name == "rainbond_start_app_share_event":
            return self.start_app_share_event(user, arguments)
        if name == "rainbond_get_app_share_event":
            return self.get_app_share_event(user, arguments)
        if name == "rainbond_complete_app_share":
            return self.complete_app_share(user, arguments)
        if name == "rainbond_giveup_app_share":
            return self.giveup_app_share(user, arguments)
        if name == "rainbond_build_component":
            return self.build_component(user, arguments)
        if name == "rainbond_get_app_last_upgrade_record":
            return self.get_app_last_upgrade_record(user, arguments)
        if name == "rainbond_query_app_upgrade_records":
            return self.query_app_upgrade_records(user, arguments)
        if name == "rainbond_create_app_upgrade_record":
            return self.create_app_upgrade_record(user, arguments)
        if name == "rainbond_get_app_upgrade_record":
            return self.get_app_upgrade_record(user, arguments)
        if name == "rainbond_get_app_upgrade_detail":
            return self.get_app_upgrade_detail(user, arguments)
        if name == "rainbond_get_app_upgrade_changes":
            return self.get_app_upgrade_changes(user, arguments)
        if name == "rainbond_execute_app_upgrade_record":
            return self.execute_app_upgrade_record(user, arguments)
        if name == "rainbond_deploy_app_upgrade_record":
            return self.deploy_app_upgrade_record(user, arguments)
        if name == "rainbond_get_app_rollback_records":
            return self.get_app_rollback_records(user, arguments)
        if name == "rainbond_rollback_app_upgrade_record":
            return self.rollback_app_upgrade_record(user, arguments)
        if name == "rainbond_get_app_upgrade_info":
            return self.get_app_upgrade_info(user, arguments)
        if name == "rainbond_upgrade_app":
            return self.upgrade_app(user, arguments)
        if name == "rainbond_get_copy_app_info":
            return self.get_copy_app_info(user, arguments)
        if name == "rainbond_copy_app":
            return self.copy_app(user, arguments)
        if name == "rainbond_install_app_by_market":
            return self.install_app_by_market(user, arguments)
        if name == "rainbond_query_cloud_markets":
            return self.query_cloud_markets(user, arguments)
        if name == "rainbond_query_local_app_models":
            return self.query_local_app_models(user, arguments)
        if name == "rainbond_query_cloud_app_models":
            return self.query_cloud_app_models(user, arguments)
        if name == "rainbond_query_app_model_versions":
            return self.query_app_model_versions(user, arguments)
        if name == "rainbond_install_app_model":
            return self.install_app_model(user, arguments)
        if name == "rainbond_create_component_from_source":
            return self.create_component_from_source(user, arguments)
        if name == "rainbond_create_component_from_package":
            return self.create_component_from_package(user, arguments)
        if name == "rainbond_init_package_upload":
            return self.init_package_upload(user, arguments)
        if name == "rainbond_upload_package_file":
            return self.upload_package_file(user, arguments)
        if name == "rainbond_get_package_upload_status":
            return self.get_package_upload_status(user, arguments)
        if name == "rainbond_delete_package_upload":
            return self.delete_package_upload(user, arguments)
        if name == "rainbond_create_component_from_local_package":
            return self.create_component_from_local_package(user, arguments)
        if name == "rainbond_check_component":
            return self.check_component(user, arguments)
        if name == "rainbond_get_component_check_result":
            return self.get_component_check_result(user, arguments)
        if name == "rainbond_create_component_from_image":
            return self.create_component_from_image(user, arguments)
        if name == "rainbond_create_app_from_yaml":
            return self.create_app_from_yaml(user, arguments)
        if name == "rainbond_check_yaml_app":
            return self.check_yaml_app(user, arguments)
        if name == "rainbond_get_yaml_app_check_result":
            return self.get_yaml_app_check_result(user, arguments)
        if name == "rainbond_query_app_monitor":
            return self.query_app_monitor(user, arguments)
        if name == "rainbond_query_app_monitor_range":
            return self.query_app_monitor_range(user, arguments)
        if name == "rainbond_create_gateway_rules":
            return self.create_gateway_rules(user, arguments)
        if name == "rainbond_check_helm_app":
            return self.check_helm_app(user, arguments)
        if name == "rainbond_build_helm_app":
            return self.build_helm_app(user, arguments)
        if name == "rainbond_query_enterprises":
            return self.query_enterprises(user, arguments)
        if name == "rainbond_query_regions":
            return self.query_regions(user, arguments)
        if name == "rainbond_get_region_detail":
            return self.get_region_detail(user, arguments)
        if name == "rainbond_create_region":
            return self.create_region(user, arguments)
        if name == "rainbond_update_region":
            return self.update_region(user, arguments)
        if name == "rainbond_delete_region":
            return self.delete_region(user, arguments)
        if name == "rainbond_query_region_nodes":
            return self.query_region_nodes(user, arguments)
        if name == "rainbond_get_region_node_detail":
            return self.get_region_node_detail(user, arguments)
        if name == "rainbond_query_region_rbd_components":
            return self.query_region_rbd_components(user, arguments)
        if name == "rainbond_query_teams":
            return self.query_teams(user, arguments)
        if name == "rainbond_query_apps":
            return self.query_apps(user, arguments)
        if name == "rainbond_query_components":
            return self.query_components(user, arguments)
        if name == "rainbond_delete_app":
            return self.delete_app(user, arguments)

        raise ServiceHandleException(msg="tool not found", msg_show="工具不存在", status_code=404)

    def get_current_user(self, user):
        return {
            "user_id": user.user_id,
            "nick_name": getattr(user, "nick_name", None),
            "real_name": getattr(user, "real_name", None),
            "email": getattr(user, "email", None),
            "enterprise_id": getattr(user, "enterprise_id", None),
            "is_enterprise_admin": self._is_enterprise_admin(user),
        }

    def get_app_detail(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        services = self._get_app_services_and_status(team, app)
        used_cpu, used_memory = self._get_services_cpu_memory(services)
        running_count = self._get_running_service_count(services)
        app_info = app.to_dict()
        app_info["service_count"] = len(services)
        app_info["enterprise_id"] = team.enterprise_id
        app_info["running_service_count"] = running_count
        app_info["status"] = self._get_app_status(running_count, len(services))
        app_info["team_name"] = team.tenant_name
        app_info["used_cpu"] = used_cpu
        app_info["used_memory"] = used_memory
        app_info["app_id"] = app.ID
        return app_info

    def create_app(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        app_name = self._require_string(arguments, "app_name")
        app_note = arguments.get("app_note", "") or ""
        k8s_app = arguments.get("k8s_app", "") or ""
        return self._create_app_with_mcp_error_details(
            team=team,
            region_name=region_name,
            app_name=app_name,
            app_note=app_note,
            username=self._get_username(user),
            k8s_app=k8s_app,
        )

    def get_component_detail(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        status_list = base_service.status_multi_service(
            region=app.region_name,
            tenant_name=team.tenant_name,
            service_ids=[service.service_id],
            enterprise_id=team.enterprise_id,
        )
        data = service.to_dict()
        data["status"] = status_list[0]["status"] if status_list else ""
        data["access_infos"] = domain_service.get_component_access_infos(app.region_name, service.service_id)
        return data

    def get_component_pods(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        data = region_api.get_service_pods(
            app.region_name, team.tenant_name, service.service_alias, team.enterprise_id
        )
        pods = self._extract_component_pods(data)
        items = []
        for pod in pods:
            item = {k: v for k, v in pod.items() if not k.startswith("_")}
            item["group"] = pod.get("_group")
            item["container_names"] = pod.get("_container_names") or []
            items.append(item)
        return {
            "team_name": team.tenant_name,
            "region_name": app.region_name,
            "app_id": app.ID,
            "service_id": service.service_id,
            "items": items,
            "total": len(items),
        }

    def get_pod_detail(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        pod_name = self._require_string(arguments, "pod_name")
        if getattr(service, "extend_method", "") == "kubeblocks_component":
            data = region_api.kubeblocks_cluster_pod_detail(
                app.region_name, service.service_id, pod_name
            )
        else:
            data = region_api.pod_detail(
                app.region_name, team.tenant_name, service.service_alias, pod_name
            )
        pod_detail = self._extract_region_pod_detail(data)
        if not pod_detail:
            raise ServiceHandleException(msg="pod not found", msg_show="Pod 不存在", status_code=404)
        return pod_detail

    def get_component_summary(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        event_limit = self._parse_int_with_default(arguments.get("event_limit"), 5)
        status_list = base_service.status_multi_service(
            region=app.region_name,
            tenant_name=team.tenant_name,
            service_ids=[service.service_id],
            enterprise_id=team.enterprise_id,
        )
        service_data = service.to_dict()
        service_data["status"] = status_list[0]["status"] if status_list else ""
        service_data["access_infos"] = domain_service.get_component_access_infos(app.region_name, service.service_id)

        ports = port_service.get_service_ports(service)
        envs = env_var_service.get_self_define_env(service)
        build_envs = env_var_service.get_service_build_envs(service)
        volumes = volume_service.get_all_service_volumes_with_status(team, service)
        mnts, mnt_total = mnt_service.get_service_mnt_details(team, service, None, page=1, page_size=1000)
        autoscaler_rules = autoscaler_service.list_autoscaler_rules(service.service_id)
        probe_code, _, probe = probe_service.get_service_probe(service)
        events, total, has_next = event_service.get_target_events(
            "service", service.service_id, team, service.service_region, 1, event_limit
        )
        resource = self._get_component_resource(team, service)

        return {
            "team_name": team.tenant_name,
            "region_name": app.region_name,
            "app_id": app.ID,
            "service_id": service.service_id,
            "service": service_data,
            "status": {"status": service_data["status"]},
            "resource": resource,
            "ports": {"items": [self._serialize_model_item(port) for port in ports], "total": len(ports)},
            "envs": {"items": [self._serialize_model_item(env) for env in envs], "total": len(envs)},
            "build_envs": {
                "items": [self._serialize_model_item(env) for env in build_envs],
                "total": len(build_envs),
            },
            "volumes": {"items": [self._serialize_model_item(volume) for volume in volumes], "total": len(volumes)},
            "mnts": {"items": mnts, "total": mnt_total},
            "probe": self._serialize_model_item(probe) if probe_code == 200 else None,
            "autoscaler_rules": {
                "items": [self._serialize_model_item(rule) for rule in autoscaler_rules],
                "total": len(autoscaler_rules),
            },
            "recent_events": {
                "items": events,
                "total": total,
                "page": 1,
                "page_size": event_limit,
                "has_next": has_next,
            },
        }

    def get_component_logs(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        action = arguments.get("action", "service") or "service"
        lines = self._parse_int_with_default(arguments.get("lines"), 100)
        follow = bool(arguments.get("follow", False))
        previous = self._parse_bool_with_default(arguments.get("previous"), False)
        fallback = None
        if action == "container":
            pod_name = self._require_string(arguments, "pod_name")
            container_name = arguments.get("container_name", "") or ""
        else:
            pod_name = arguments.get("pod_name", "") or ""
            container_name = arguments.get("container_name", "") or ""
            if not pod_name:
                pod_name, inferred_container = self._infer_component_log_target(team, app.region_name, service)
                if not pod_name:
                    raise ServiceHandleException(
                        msg="pod not found",
                        msg_show="未找到可用的组件实例日志，请确认组件是否已运行",
                        status_code=404,
                    )
                if not container_name:
                    container_name = inferred_container or ""
                fallback = {
                    "action": "container",
                    "pod_name": pod_name,
                    "container_name": container_name,
                }
        log_list = self._read_component_pod_logs(
            team, app.region_name, service.service_alias, pod_name, lines, container_name, previous=previous
        )
        return {
            "team_name": team.tenant_name,
            "region_name": app.region_name,
            "app_id": app.ID,
            "service_id": service.service_id,
            "action": action,
            "lines": self._parse_int_with_default(arguments.get("lines"), 100),
            "previous": previous,
            "items": log_list,
            "total": len(log_list),
            "fallback": fallback,
        }

    def exec_component(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        pod_name = self._require_string(arguments, "pod_name")
        container_name = arguments.get("container_name", "") or ""
        command = self._require_command(arguments)
        timeout_seconds = self._parse_optional_positive_int(
            arguments.get("timeout_seconds"), "timeout_seconds"
        ) or 30
        try:
            body = region_api.exec_component_pod(
                team.tenant_name,
                app.region_name,
                service.service_alias,
                pod_name,
                container_name,
                command,
                timeout_seconds=timeout_seconds,
            )
        except ServiceHandleException as e:
            # region 在容器未运行时返回可区分错误，被 region client 统一为该 msg。
            # 此处不直接抛出，而是返回一个对 AI/用户友好的结果，引导改用 previous 日志。
            if e.msg == "container not running":
                return {
                    "team_name": team.tenant_name,
                    "region_name": app.region_name,
                    "app_id": app.ID,
                    "service_id": service.service_id,
                    "pod_name": pod_name,
                    "container_name": container_name,
                    "container_running": False,
                    "message": (
                        "目标容器未处于运行状态，无法 exec。"
                        "请改用 rainbond_get_component_logs 并设置 previous=true 读取上一次退出前的日志进行排查；"
                        "若需确认配置文件内容，可使用 rainbond_get_config_file。"
                    ),
                }
            raise
        detail = self._extract_region_pod_detail(body) if isinstance(body, dict) else {}
        if not isinstance(detail, dict):
            detail = {}
        exit_code = detail.get("exit_code")
        try:
            exit_code = int(exit_code) if exit_code is not None else None
        except (TypeError, ValueError):
            pass
        return {
            "team_name": team.tenant_name,
            "region_name": app.region_name,
            "app_id": app.ID,
            "service_id": service.service_id,
            "pod_name": pod_name,
            "container_name": container_name,
            "container_running": True,
            "stdout": detail.get("stdout", "") or "",
            "stderr": detail.get("stderr", "") or "",
            "exit_code": exit_code,
            "truncated": bool(detail.get("truncated", False)),
        }

    def get_config_file(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        volume_name = arguments.get("volume_name", "") or ""
        volume_path = arguments.get("volume_path", "") or ""
        config_volumes = volume_repo.get_service_volumes_about_config_file(service.service_id) or []
        config_files = {}
        for config_file in volume_repo.get_service_config_files(service.service_id) or []:
            config_files[config_file.volume_id] = config_file
            if config_file.volume_name:
                config_files["name:" + config_file.volume_name] = config_file
        items = []
        for volume in config_volumes:
            if volume_name and volume.volume_name != volume_name:
                continue
            if volume_path and volume.volume_path != volume_path:
                continue
            config_file = config_files.get(volume.ID)
            if config_file is None and volume.volume_name:
                config_file = config_files.get("name:" + volume.volume_name)
            items.append({
                "volume_name": volume.volume_name,
                "volume_path": volume.volume_path,
                "mode": volume.mode,
                "file_content": config_file.file_content if config_file else "",
            })
        return {
            "team_name": team.tenant_name,
            "region_name": app.region_name,
            "app_id": app.ID,
            "service_id": service.service_id,
            "items": items,
            "total": len(items),
        }

    def get_component_events(self, user, arguments):
        page = self._parse_int_with_default(arguments.get("page"), 1)
        page_size = self._parse_int_with_default(arguments.get("page_size"), 10)
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        events, total, has_next = event_service.get_target_events(
            "service", service.service_id, team, service.service_region, page, page_size
        )
        return {
            "events": events,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": has_next,
        }

    def get_component_build_logs(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        event_id = self._require_string(arguments, "event_id")
        raw_items = event_service.get_event_log(team, app.region_name, event_id) or []
        total_unfiltered = len(raw_items)

        # Optional filters / slicing. Build logs from large projects (Maven monorepo,
        # multi-stage Node.js) can hit thousands of lines; without these, the upstream
        # LLM wrapper truncates the middle and the real error (always near the tail)
        # disappears.
        grep = arguments.get("grep")
        if isinstance(grep, str) and grep.strip():
            keyword = grep.strip()
            items = [it for it in raw_items if self._build_log_item_contains(it, keyword)]
        else:
            items = list(raw_items)

        offset = self._parse_optional_positive_int(arguments.get("offset"), "offset", allow_zero=True) or 0
        limit = self._parse_optional_positive_int(arguments.get("limit"), "limit")
        tail = self._parse_optional_positive_int(arguments.get("tail"), "tail")

        if tail is not None:
            # tail wins over offset/limit when both are provided; AI clients should pick one.
            items = items[-tail:]
        elif offset or limit is not None:
            end = offset + limit if limit is not None else None
            items = items[offset:end]

        truncated = len(items) != total_unfiltered
        return {
            "team_name": team.tenant_name,
            "region_name": app.region_name,
            "app_id": app.ID,
            "service_id": service.service_id,
            "event_id": event_id,
            "items": items,
            "total": len(items),
            "total_unfiltered": total_unfiltered,
            "truncated": truncated,
        }

    @staticmethod
    def _build_log_item_contains(item, keyword):
        if isinstance(item, dict):
            haystack = item.get("message")
            if not isinstance(haystack, str):
                haystack = str(item)
        elif isinstance(item, str):
            haystack = item
        else:
            haystack = str(item)
        return keyword in haystack

    def _get_component_build_source_snapshot(self, team, app, service):
        build_infos = base_service.get_build_infos(team, [service.service_id])
        bean = dict(build_infos.get(service.service_id) or {})
        username = bean.pop("user", bean.pop("user_name", "")) or ""
        has_password = bool(bean.pop("password", ""))
        bean["username"] = username
        bean["has_password"] = has_password
        bean.setdefault("service_source", getattr(service, "service_source", ""))
        bean.setdefault("arch", getattr(service, "arch", ""))
        try:
            _, body = region_api.get_cluster_nodes_arch(app.region_name)
            bean["arch_options"] = list(set((body or {}).get("list") or []))
        except Exception:
            bean["arch_options"] = []
        return bean

    def get_component_build_source(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        return {
            "app_id": app.ID,
            "service_id": service.service_id,
            "build_source": self._get_component_build_source_snapshot(team, app, service),
        }

    def update_component_build_source(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        target_source = self._require_string(arguments, "service_source").strip().lower()
        if target_source not in ("source_code", "docker_run", "docker_image"):
            raise ServiceHandleException(msg="invalid service_source", msg_show="参数service_source无效", status_code=400)

        source_record = service_source_repo.get_service_source(team.tenant_id, service.service_id)
        has_username = "username" in arguments or "user_name" in arguments
        has_password = "password" in arguments
        username = arguments.get("username", arguments.get("user_name", ""))
        password = arguments.get("password", "")
        if source_record:
            if has_username:
                source_record.user_name = username
            if has_password:
                source_record.password = password
            if has_username or has_password:
                source_record.save()
        elif has_username or has_password:
            console_app_service.create_service_source_info(team, service, username, password)

        old_arch = getattr(service, "arch", "")
        new_arch = (arguments.get("arch") or old_arch or "").strip()

        if target_source == "source_code":
            normalized_git_url = self._normalize_source_git_url(
                arguments.get("git_url") or getattr(service, "git_url", "") or "",
                arguments.get("subdirectories"),
            )
            server_type = (arguments.get("server_type") or getattr(service, "server_type", "") or "").strip()
            if not server_type and normalized_git_url:
                server_type = source_component_service.infer_server_type(normalized_git_url, None)
            is_oauth = self._parse_bool_with_default(arguments.get("is_oauth"), False)
            normalized_code_version = arguments.get("code_version")
            if normalized_code_version is not None:
                normalized_code_version = self._normalize_source_code_version(
                    normalized_code_version,
                    arguments.get("version_type"),
                )
            elif server_type == "oss":
                normalized_code_version = ""
            else:
                normalized_code_version = getattr(service, "code_version", "") or "master"

            if is_oauth:
                oauth_service_id = self._require_string(arguments, "oauth_service_id")
                try:
                    oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=oauth_service_id)
                    oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=oauth_service_id, user_id=user.user_id)
                except Exception:
                    raise ServiceHandleException(
                        msg="oauth service invalid",
                        msg_show="Oauth服务可能已被删除，请重新配置",
                        status_code=400,
                    )
                try:
                    instance = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
                except Exception:
                    raise ServiceHandleException(msg="oauth service invalid", msg_show="未找到OAuth服务", status_code=400)
                if not instance.is_git_oauth():
                    raise ServiceHandleException(
                        msg="oauth service invalid",
                        msg_show="该OAuth服务不是代码仓库类型",
                        status_code=400,
                    )
                service.code_from = "oauth_" + oauth_service.oauth_type
                service.oauth_service_id = oauth_service_id
                service.git_full_name = arguments.get("full_name", "") or getattr(service, "git_full_name", "")
            else:
                service.code_from = ""
            if normalized_git_url:
                service.git_url = normalized_git_url
            service.code_version = normalized_code_version
            service.service_source = "source_code"
            service.server_type = server_type
            service.cmd = ""
            service.image = ""
            service.service_key = "application"
        else:
            image = arguments.get("image") or getattr(service, "image", "")
            if image:
                version = image.split(":")[-1] if ":" in image else "latest"
                if ":" not in image:
                    image = image + ":" + version
                service.image = image
                service.version = version
            if "cmd" in arguments:
                service.cmd = arguments.get("cmd", "") or ""
            elif target_source != getattr(service, "service_source", ""):
                service.cmd = ""
            if "server_type" in arguments:
                service.server_type = arguments.get("server_type", "") or ""
            service.service_source = "docker_image"
            service.git_url = ""
            service.code_from = "image_manual"
            service.service_key = "application"
            service.language = ""

        service.arch = new_arch
        service.save()
        if old_arch != new_arch:
            arch_service.update_affinity_by_arch(new_arch, team, app.region_name, service)

        return {
            "updated": True,
            "app_id": app.ID,
            "service_id": service.service_id,
            "build_source": self._get_component_build_source_snapshot(team, app, service),
        }

    def create_component(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        service_cname = self._require_string(arguments, "service_cname")
        image = self._require_string(arguments, "image")
        docker_cmd = arguments.get("docker_cmd", "") or ""
        docker_user_name = arguments.get("user_name", "") or ""
        docker_password = arguments.get("password", "") or ""
        k8s_component_name = arguments.get("k8s_component_name", "") or ""
        is_deploy = bool(arguments.get("is_deploy", True))
        if k8s_component_name and console_app_service.is_k8s_component_name_duplicate(app.ID, k8s_component_name):
            raise ServiceHandleException(msg="component name exists", msg_show="组件英文名称已存在", status_code=400)

        code, msg_show, new_service = console_app_service.create_docker_run_app(
            app.region_name, team, user, service_cname, docker_cmd, "docker_image", k8s_component_name, image
        )
        if code != 200:
            raise ServiceHandleException(msg="service create fail", msg_show=msg_show, status_code=code)

        if docker_password or docker_user_name:
            console_app_service.create_service_source_info(team, new_service, docker_user_name, docker_password)

        code, msg_show = group_service.add_service_to_group(team, app.region_name, app.ID, new_service.service_id)
        if code != 200:
            raise ServiceHandleException(msg="add component to app failure", msg_show=msg_show, status_code=code)

        region_new_service = console_app_service.create_region_service(team, new_service, user.nick_name)
        event_id = ""
        if is_deploy:
            code, msg_show, event_id = app_manage_service.deploy(team, region_new_service, user)
            if code != 200:
                raise ServiceHandleException(msg="build failed", msg_show=msg_show, status_code=code)

        return {
            "service_id": region_new_service.service_id,
            "service_alias": region_new_service.service_alias,
            "service_cname": region_new_service.service_cname,
            "event_id": event_id,
            "is_deploy": is_deploy,
        }

    def delete_component(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        code, msg = app_manage_service.delete(user, team, service, True)
        if code != 200:
            raise self._build_component_delete_error(service, code, msg)
        return {
            "deleted": True,
            "service_id": service.service_id,
            "service_cname": service.service_cname,
            "app_id": app.ID,
        }

    @staticmethod
    def _build_component_delete_error(service, code, msg):
        """Turn a non-200 delete result into a structured, non-retryable reason.

        delete_component used to surface a generic "delete error", so the agent
        could not tell that a dependency/mount/running conflict is not worth
        retrying (the #1 source of delete retry storms). Map the known precondition
        failures to an explicit reason + remediation, keeping the dependent names
        that app_manage_service.delete already put in `msg`.
        """
        text = (msg or "").strip()
        reason = "delete_failed"
        retryable = None
        msg_show = text or "删除组件失败"
        if code == 412 and "依赖" in text:
            reason = "dependency_conflict"
            retryable = False
            msg_show = "{}。请先在依赖管理中解除依赖关系后再删除该组件。".format(text)
        elif code == 412 and "挂载" in text:
            reason = "storage_mount_conflict"
            retryable = False
            msg_show = "{}。请先解除存储挂载后再删除该组件。".format(text)
        elif code == 409:
            reason = "component_running"
            retryable = False
            msg_show = text or "组件可能处于运行状态，请先关闭组件后再删除。"
        details = {
            "reason": reason,
            "service_id": service.service_id,
            "service_cname": getattr(service, "service_cname", ""),
        }
        if retryable is not None:
            details["retryable"] = retryable
        return ServiceHandleException(msg=reason, msg_show=msg_show, status_code=code, details=details)

    def operate_app(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        action = self._require_string(arguments, "action")
        supported_actions = ("start", "stop", "restart", "upgrade", "deploy")
        if action not in supported_actions:
            raise ServiceHandleException(
                msg="unsupported action", msg_show="不支持的应用操作: {}".format(action), status_code=400)
        service_ids = arguments.get("service_ids") or self._get_app_service_ids(app)
        if action == "restart":
            code, msg, result = app_manage_service.batch_action(
                app.region_name, team, user, action, service_ids, None, None)
            if code != 200:
                raise ServiceHandleException(msg="batch restart error", msg_show=msg, status_code=code)
            result = [self._serialize_model_item(service) for service in result]
        else:
            result = app_manage_service.batch_operations(team, app.region_name, user, action, service_ids, None)
        return {
            "app_id": app.ID,
            "action": action,
            "service_ids": service_ids,
            "result": result,
        }

    def update_component_envs(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        envs = arguments.get("envs")
        if not isinstance(envs, list) or not envs:
            raise ServiceHandleException(msg="invalid envs", msg_show="参数envs无效", status_code=400)
        result = env_var_service.update_or_create_envs(team, service, envs)
        result["app_id"] = app.ID
        result["service_id"] = service.service_id
        return result

    def manage_component_envs(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        operation = self._normalize_component_operation(
            self._require_string(arguments, "operation"),
            self.ENV_OPERATION_ALIASES,
            ("summary", "upsert", "create", "update", "delete", "patch_scope", "replace_build_envs"),
            "环境变量",
        )
        if operation == "summary":
            envs = env_var_service.get_service_inner_env(service)
            connection_envs = env_var_service.get_service_outer_env(service)
            build_envs = env_var_service.get_service_build_envs(service)
            return {
                "service_id": service.service_id,
                "custom_envs": {"items": [self._serialize_model_item(env) for env in envs], "total": len(envs)},
                "connection_envs": {
                    "items": [self._serialize_model_item(env) for env in connection_envs],
                    "total": len(connection_envs),
                },
                "build_envs": {"items": [self._serialize_model_item(env) for env in build_envs], "total": len(build_envs)},
            }
        if operation == "upsert":
            envs = self._resolve_upsert_envs(arguments)
            if not isinstance(envs, list) or not envs:
                raise ServiceHandleException(msg="invalid envs", msg_show="参数envs无效", status_code=400)
            envs = self._normalize_envs_for_upsert(envs)
            result = self._upsert_inner_envs(team, service, envs, user.nick_name)
            result["service_id"] = service.service_id
            return result
        if operation == "create":
            attr_name = self._require_string(arguments, "attr_name")
            attr_value = self._require_string(arguments, "attr_value")
            name = arguments.get("name", "") or ""
            scope = self._normalize_env_scope(arguments.get("scope"))
            is_change = arguments.get("is_change", True)
            code, msg, env = env_var_service.add_service_env_var(
                team, service, 0, name, attr_name, attr_value, is_change, scope, user.nick_name
            )
            if code != 200:
                raise ServiceHandleException(msg="add env error", msg_show=msg, status_code=code)
            return {"created": True, "env": self._serialize_model_item(env)}
        if operation == "update":
            env_id = self._require_string(arguments, "env_id")
            self._ensure_inner_env(team, service, env_id)
            name = arguments.get("name", "") or ""
            attr_value = self._require_string(arguments, "attr_value")
            code, msg, env = env_var_service.update_env_by_env_id(team, service, env_id, name, attr_value, user.nick_name)
            if code != 200:
                raise ServiceHandleException(msg="update value error", msg_show=msg, status_code=code)
            return {"updated": True, "env": self._serialize_model_item(env)}
        if operation == "delete":
            env_id = self._require_string(arguments, "env_id")
            self._ensure_inner_env(team, service, env_id)
            env_var_service.delete_env_by_env_id(team, service, env_id, user.nick_name)
            return {"deleted": True, "env_id": env_id}
        if operation == "patch_scope":
            raise ServiceHandleException(
                msg="invalid env operation",
                msg_show="高层环境变量工具不再处理连接信息迁移，请使用自定义环境变量工具管理 inner 变量",
                status_code=400,
            )
        if operation == "replace_build_envs":
            build_env_dict = arguments.get("build_env_dict") or {}
            if not isinstance(build_env_dict, dict):
                raise ServiceHandleException(msg="invalid build_env_dict", msg_show="参数build_env_dict无效", status_code=400)
            build_envs = env_var_service.get_service_build_envs(service)
            for build_env in build_envs:
                build_env.delete()
            if build_env_dict:
                cnb_params = [
                    "CNB_FRAMEWORK", "CNB_BUILD_SCRIPT", "CNB_OUTPUT_DIR", "CNB_NODE_VERSION",
                    "CNB_NODE_ENV", "CNB_MIRROR_SOURCE", "CNB_MIRROR_NPMRC", "CNB_MIRROR_YARNRC",
                    "CNB_START_SCRIPT"
                ]
                has_cnb_params = any(key in build_env_dict for key in cnb_params)
                if has_cnb_params and "BUILD_TYPE" not in build_env_dict:
                    build_env_dict["BUILD_TYPE"] = "cnb"
                for key, value in list(build_env_dict.items()):
                    code, msg, _ = env_var_service.add_service_build_env_var(team, service, 0, "构建运行时环境变量", key, value, True)
                    if code != 200:
                        raise ServiceHandleException(msg="add build env error", msg_show=msg, status_code=code)
            compile_env = compile_env_repo.get_service_compile_env(service.service_id)
            if compile_env and compile_env.user_dependency:
                compile_env_payload, state = read_compile_env_state(compile_env.user_dependency)
                compile_env.user_dependency = json.dumps(build_compile_env_payload(compile_env_payload, state))
                compile_env.save()
            return {"updated": True, "build_envs": build_env_dict}
        raise ServiceHandleException(msg="invalid env operation", msg_show="不支持的环境变量操作类型", status_code=400)

    def manage_component_connection_envs(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        operation = self._normalize_component_operation(
            self._require_string(arguments, "operation"),
            {
                "summary": "summary",
                "list": "summary",
                "view": "summary",
                "create": "create",
                "add": "create",
                "update": "update",
                "edit": "update",
                "delete": "delete",
                "remove": "delete",
                "patch_scope": "patch_scope",
                "change_scope": "patch_scope",
            },
            ("summary", "create", "update", "delete", "patch_scope"),
            "连接信息",
        )
        if operation == "summary":
            envs = env_var_service.get_service_outer_env(service)
            return {
                "service_id": service.service_id,
                "connection_envs": {"items": [self._serialize_model_item(env) for env in envs], "total": len(envs)},
            }
        if operation == "create":
            attr_name = self._require_string(arguments, "attr_name")
            attr_value = self._require_string(arguments, "attr_value")
            name = arguments.get("name", "") or ""
            code, msg, env = env_var_service.add_service_env_var(
                team, service, 0, name, attr_name, attr_value, False, "outer", user.nick_name
            )
            if code != 200:
                raise ServiceHandleException(msg="add env error", msg_show=msg, status_code=code)
            return {"created": True, "env": self._serialize_model_item(env)}
        if operation == "update":
            env_id = self._require_string(arguments, "env_id")
            self._ensure_outer_env(team, service, env_id)
            name = arguments.get("name", "") or ""
            attr_value = self._require_string(arguments, "attr_value")
            code, msg, env = env_var_service.update_env_by_env_id(team, service, env_id, name, attr_value, user.nick_name)
            if code != 200:
                raise ServiceHandleException(msg="update value error", msg_show=msg, status_code=code)
            return {"updated": True, "env": self._serialize_model_item(env)}
        if operation == "delete":
            env_id = self._require_string(arguments, "env_id")
            self._ensure_outer_env(team, service, env_id)
            env_var_service.delete_env_by_env_id(team, service, env_id, user.nick_name)
            return {"deleted": True, "env_id": env_id}
        if operation == "patch_scope":
            env_id = self._require_string(arguments, "env_id")
            env = self._ensure_outer_env(team, service, env_id)
            scope = self._require_string(arguments, "scope")
            if scope not in ("inner", "outer"):
                raise ServiceHandleException(msg="params error", msg_show="scope范围只能是inner或outer", status_code=400)
            result = env_var_service.patch_env_scope(team, service, env_id, scope, user.nick_name)
            return {"updated": True, "env": self._serialize_model_item(result), "from_scope": env.scope, "to_scope": scope}
        raise ServiceHandleException(msg="invalid connection env operation", msg_show="不支持的组件连接信息操作类型", status_code=400)

    def change_component_image(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        image = self._require_string(arguments, "image")
        version = image.split(":")[-1] if ":" in image else "latest"
        if ":" not in image:
            image = image + ":" + version
        service.image = image
        service.version = version
        service.save()
        data = service.to_dict()
        data["app_id"] = app.ID
        return data

    def handle_component_ports(self, user, arguments):
        operation = self._require_string(arguments, "operation")
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        if operation == "list":
            ports = port_service.get_service_ports(service)
            return {
                "service_id": service.service_id,
                "items": [self._serialize_model_item(port) for port in ports],
                "total": len(ports),
            }
        if operation == "add":
            port = self._require_int(arguments, "port")
            protocol = self._require_string(arguments, "protocol")
            port_alias = arguments.get("port_alias", "") or ""
            is_inner_service = bool(arguments.get("is_inner_service", False))
            code, msg, port_info = port_service.add_service_port(
                team, service, port, protocol, port_alias, is_inner_service, False, None, user.nick_name
            )
            if code != 200:
                self._raise_port_tool_error("add port error", msg, code)
            return self._serialize_model_item(port_info)
        if operation == "update":
            port = self._require_int(arguments, "port")
            action = self._normalize_port_action(self._require_string(arguments, "action"))
            protocol = arguments.get("protocol")
            port_alias = arguments.get("port_alias")
            k8s_service_name = arguments.get("k8s_service_name", "") or ""
            code, msg, port_info = port_service.manage_port(
                team,
                service,
                app.region_name,
                port,
                action,
                protocol,
                port_alias,
                k8s_service_name,
                user.nick_name,
                app=app,
            )
            if code != 200:
                self._raise_port_tool_error("change port fail", msg, code)
            return self._serialize_model_item(port_info)
        if operation == "delete":
            port = self._require_int(arguments, "port")
            port_info = port_service.delete_port_by_container_port(team, service, port, user.nick_name)
            return {
                "deleted": True,
                "port": self._serialize_model_item(port_info),
            }
        raise ServiceHandleException(msg="invalid operation", msg_show="不支持的端口操作类型", status_code=400)

    def manage_component_ports(self, user, arguments):
        operation = self._normalize_component_operation(
            self._require_string(arguments, "operation"),
            self.HIGH_LEVEL_PORT_OPERATION_ALIASES,
            (
                "summary", "add", "update", "delete",
                "enable_inner", "disable_inner", "enable_outer", "disable_outer",
                "enable_outer_only", "update_protocol", "update_alias"
            ),
            "端口",
        )
        if operation == "summary":
            payload = dict(arguments)
            payload["operation"] = "list"
            result = self.handle_component_ports(user, payload)
            return {
                "service_id": payload["service_id"],
                "ports": {
                    "items": result.get("items", []),
                    "total": result.get("total", 0),
                }
            }
        if operation == "add":
            ports_list = arguments.get("ports")
            if ports_list:
                return self._batch_add_ports(user, arguments, ports_list)
            payload = dict(arguments)
            payload["operation"] = "add"
            if "is_inner_service" not in payload and "enable_inner" in payload:
                payload["is_inner_service"] = bool(payload.get("enable_inner"))
            return self.handle_component_ports(user, payload)

        action_map = {
            "enable_inner": "open_inner",
            "disable_inner": "close_inner",
            "enable_outer": "open_outer",
            "disable_outer": "close_outer",
            "enable_outer_only": "only_open_outer",
            "update_protocol": "change_protocol",
            "update_alias": "change_port_alias",
        }
        if operation in action_map:
            ports_list = arguments.get("ports")
            if ports_list:
                return self._batch_update_ports(user, arguments, action_map[operation], ports_list)
            payload = dict(arguments)
            payload["operation"] = "update"
            payload["action"] = action_map[operation]
            return self.handle_component_ports(user, payload)

        payload = dict(arguments)
        payload["operation"] = operation
        return self.handle_component_ports(user, payload)

    def _batch_add_ports(self, user, arguments, ports_list):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        created = port_service.batch_add_service_ports(team, service, ports_list, user.nick_name, app=app)
        return {"ports": [self._serialize_model_item(p) for p in created]}

    def _batch_update_ports(self, user, arguments, action, ports_list):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        results = []
        for item in ports_list:
            port_num = item if isinstance(item, int) else int(item.get("port", item))
            code, msg, port_info = port_service.manage_port(
                team, service, app.region_name, port_num, action,
                None, None, "", user.nick_name, app=app,
            )
            if code != 200:
                self._raise_port_tool_error("port operation failed", msg, code)
            results.append(self._serialize_model_item(port_info))
        return {"ports": results}

    def bind_component_volume(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        volume = volume_service.add_service_volume(
            team,
            service,
            self._require_string(arguments, "volume_path"),
            self._require_string(arguments, "volume_type"),
            self._require_string(arguments, "volume_name"),
            arguments.get("file_content"),
            {
                "volume_capacity": self._parse_int_with_default(arguments.get("volume_capacity"), 0),
                "provider_name": arguments.get("provider_name", "") or "",
                "access_mode": arguments.get("access_mode", "") or "",
                "share_policy": arguments.get("share_policy", "") or "",
                "back_policy": arguments.get("back_policy", "") or "",
                "reclaim_policy": arguments.get("reclaim_policy", "") or "",
                "allow_expansion": bool(arguments.get("allow_expansion", False)),
            },
            user.nick_name,
            mode=arguments.get("mode"),
        )
        result = self._serialize_model_item(volume)
        result["app_id"] = app.ID
        result["service_id"] = service.service_id
        return result

    def _mcp_assert_volume_path_available(self, service, new_volume_path):
        existing_rows = volume_repo.get_service_volumes_with_config_file(
            service.service_id
        ).values("volume_path")
        for row in existing_rows:
            existing = row["volume_path"]
            if existing == new_volume_path:
                raise ServiceHandleException(
                    msg="path already exists",
                    msg_show="持久化路径[{0}]已存在".format(existing),
                    status_code=412,
                )
            if existing.startswith(new_volume_path + "/") or new_volume_path.startswith(existing + "/"):
                raise ServiceHandleException(
                    msg="path conflict",
                    msg_show="已存在以{0}开头的路径".format(existing),
                    status_code=412,
                )

    def manage_component_storage(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        operation = self._normalize_component_operation(
            self._require_string(arguments, "operation"),
            self.STORAGE_OPERATION_ALIASES,
            ("summary", "list_unmounted", "create_volume", "update_volume", "delete_volume", "create_mnt", "delete_mnt"),
            "存储",
        )
        if operation == "summary":
            # MCP summary intentionally returns every volume type (including
            # config-file). The `is_config` argument is kept in the schema
            # only because `list_unmounted` still uses it; ignoring it here
            # avoids the historical default-False filter that hid config-file
            # volumes from AI assistants.
            volume_options = volume_service.get_service_support_volume_options(team, service)
            volumes = volume_service.get_all_service_volumes_with_status(team, service)
            mnts, total = mnt_service.get_service_mnt_details(team, service, arguments.get("volume_types"), page=1, page_size=1000)
            return {
                "service_id": service.service_id,
                "volume_options": {"items": volume_options, "total": len(volume_options)},
                "volumes": {"items": [self._serialize_model_item(v) for v in volumes], "total": len(volumes)},
                "mnts": {"items": mnts, "total": total},
            }
        if operation == "list_unmounted":
            page = self._parse_int_with_default(arguments.get("page"), 1)
            page_size = self._parse_int_with_default(arguments.get("page_size"), 20)
            dep_app_name = arguments.get("dep_app_name", "") or ""
            dep_app_group = arguments.get("dep_app_group", "") or ""
            config_name = arguments.get("config_name", "") or ""
            is_config = bool(arguments.get("is_config", False))
            services = console_app_service.get_app_list(team.tenant_id, service.service_region, dep_app_name)
            service_ids = [item.service_id for item in services]
            items, total = mnt_service.get_service_unmount_volume_list(
                team, service, service_ids, page, page_size, is_config, dep_app_group, config_name
            )
            return {"items": items, "total": total, "page": page, "page_size": page_size}
        if operation == "create_volume":
            volume_path = self._require_string(arguments, "volume_path")
            # The shared `volume_service.check_volume_path` filters out
            # config-file volumes by design (console contract). MCP creators
            # need full path-conflict coverage so the AI cannot create a
            # persistent volume whose path collides with an existing
            # config-file mount, and vice versa.
            self._mcp_assert_volume_path_available(service, volume_path)
            volume = volume_service.add_service_volume(
                team,
                service,
                volume_path,
                self._require_string(arguments, "volume_type"),
                self._require_string(arguments, "volume_name"),
                arguments.get("file_content"),
                {
                    "volume_capacity": self._parse_int_with_default(arguments.get("volume_capacity"), 0),
                    "provider_name": arguments.get("provider_name", "") or "",
                    "access_mode": arguments.get("access_mode", "") or "",
                    "share_policy": arguments.get("share_policy", "") or "",
                    "back_policy": arguments.get("back_policy", "") or "",
                    "reclaim_policy": arguments.get("reclaim_policy", "") or "",
                    "allow_expansion": bool(arguments.get("allow_expansion", False)),
                },
                user.nick_name,
                mode=arguments.get("mode"),
            )
            return {"created": True, "volume": self._serialize_model_item(volume)}
        if operation == "update_volume":
            volume_id = self._require_int(arguments, "volume_id")
            new_volume_path = self._require_string(arguments, "new_volume_path")
            new_file_content = arguments.get("new_file_content")
            volume_capacity = arguments.get("volume_capacity")
            mode = arguments.get("mode")
            if mode is not None:
                mode = self._ensure_volume_mode(mode)
            if volume_capacity is not None:
                volume_capacity = self._parse_int_with_default(volume_capacity, 0)
            volume = volume_repo.get_service_volume_by_pk(volume_id)
            if not volume:
                raise ServiceHandleException(msg="volume is null", msg_show="存储不存在", status_code=400)
            service_config = volume_repo.get_service_config_file(volume)
            if volume.volume_type == "config-file" and not service_config:
                raise ServiceHandleException(msg="file_content is null", msg_show="配置文件内容不存在", status_code=400)
            target_volume_capacity = volume.volume_capacity if volume_capacity is None else volume_capacity
            if self.service_requires_region_sync(service):
                data = {
                    "volume_name": volume.volume_name,
                    "volume_path": new_volume_path,
                    "volume_type": volume.volume_type,
                    "file_content": new_file_content,
                    "operator": user.nick_name,
                    "mode": mode,
                }
                if volume.volume_type != "config-file":
                    data["volume_capacity"] = target_volume_capacity
                res, _ = region_api.upgrade_service_volumes(service.service_region, team.tenant_name, service.service_alias, data)
                if res.status != 200:
                    raise ServiceHandleException(msg="update failed", msg_show="修改失败", status_code=405)
            volume.volume_path = new_volume_path
            if volume_capacity is not None:
                volume.volume_capacity = volume_capacity
            if mode is not None:
                volume.mode = mode
            volume.save()
            if volume.volume_type == "config-file" and service_config:
                service_config.volume_name = volume.volume_name
                service_config.file_content = new_file_content
                service_config.save()
            return {"updated": True, "volume": self._serialize_model_item(volume)}
        if operation == "delete_volume":
            volume_id = self._require_int(arguments, "volume_id")
            force = None
            if "force" in arguments:
                force = "1" if bool(arguments.get("force")) else "0"
            code, msg, volume = volume_service.delete_service_volume_by_id(
                team, service, volume_id, user.nick_name, force
            )
            if code == 202:
                return {"deleted": False, "requires_force": True, "message": msg, "dependents": volume}
            if code != 200:
                raise ServiceHandleException(msg="delete volume error", msg_show=msg, status_code=code)
            return {"deleted": True, "volume": self._serialize_model_item(volume)}
        if operation == "create_mnt":
            mounts = arguments.get("mounts") or []
            if not isinstance(mounts, list) or not mounts:
                raise ServiceHandleException(msg="invalid mounts", msg_show="参数mounts无效", status_code=400)
            mnt_service.batch_mnt_serivce_volume(team, service, mounts, user.nick_name)
            return {"created": True, "items": mnt_service.get_service_mnt_details_byid(mounts), "total": len(mounts)}
        if operation == "delete_mnt":
            dep_vol_id = self._require_int(arguments, "dep_vol_id")
            code, msg = mnt_service.delete_service_mnt_relation(team, service, dep_vol_id, user.nick_name)
            if code != 200:
                raise ServiceHandleException(msg="delete mnt error", msg_show=msg, status_code=code)
            return {"deleted": True, "dep_vol_id": dep_vol_id}
        raise ServiceHandleException(msg="invalid storage operation", msg_show="不支持的存储操作类型", status_code=400)

    def manage_component_autoscaler(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        operation = self._normalize_component_operation(
            self._require_string(arguments, "operation"),
            self.AUTOSCALER_OPERATION_ALIASES,
            ("summary", "get_rule", "create_rule", "update_rule", "records"),
            "自动伸缩",
        )
        if operation == "summary":
            rules = autoscaler_service.list_autoscaler_rules(service.service_id)
            records = scaling_records_service.list_scaling_records(app.region_name, team.tenant_name, service.service_alias, 1, 10)
            return {
                "service_id": service.service_id,
                "rules": {"items": [self._serialize_model_item(rule) for rule in rules], "total": len(rules)},
                "records": {
                    "items": records.get("list", []) if isinstance(records, dict) else [],
                    "total": records.get("total", 0) if isinstance(records, dict) else 0,
                },
            }
        if operation == "get_rule":
            rule_id = self._require_string(arguments, "rule_id")
            return autoscaler_service.get_by_rule_id(rule_id)
        if operation == "create_rule":
            data = self._build_autoscaler_payload(service, arguments)
            result = autoscaler_service.create_autoscaler_rule(app.region_name, team.tenant_name, service.service_alias, data)
            return {"created": True, "rule": result}
        if operation == "update_rule":
            rule_id = self._require_string(arguments, "rule_id")
            data = self._build_autoscaler_payload(service, arguments)
            result = autoscaler_service.update_autoscaler_rule(
                app.region_name, team.tenant_name, service.service_alias, rule_id, data, user.nick_name
            )
            return {"updated": True, "rule": result}
        if operation == "records":
            page = self._parse_int_with_default(arguments.get("page"), 1)
            page_size = self._parse_int_with_default(arguments.get("page_size"), 10)
            records = scaling_records_service.list_scaling_records(app.region_name, team.tenant_name, service.service_alias, page, page_size)
            return records
        raise ServiceHandleException(msg="invalid autoscaler operation", msg_show="不支持的自动伸缩操作类型", status_code=400)

    def manage_component_probe(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        operation = self._normalize_component_operation(
            self._require_string(arguments, "operation"),
            self.PROBE_OPERATION_ALIASES,
            ("summary", "get", "create", "update", "delete"),
            "探针",
        )
        if operation == "summary":
            code, msg, probe = probe_service.get_service_probe(service)
            _, _, modes = probe_service.get_service_probe_by_mode(service, None)
            return {
                "service_id": service.service_id,
                "probe": self._serialize_model_item(probe) if code == 200 else None,
                "mode_status": modes if isinstance(modes, list) else [],
            }
        if operation == "get":
            mode = arguments.get("mode")
            code, msg, probe = probe_service.get_service_probe_by_mode(service, mode) if mode else probe_service.get_service_probe(service)
            if code != 200:
                raise ServiceHandleException(msg="get probe error", msg_show=msg, status_code=code)
            if isinstance(probe, list):
                return {"service_id": service.service_id, "items": probe, "total": len(probe)}
            return self._serialize_model_item(probe)
        if operation == "create":
            probe_data = self._build_probe_payload(arguments)
            code, msg, probe = probe_service.add_service_probe(team, service, probe_data)
            if code != 200:
                raise ServiceHandleException(msg="add probe error", msg_show=msg, status_code=code)
            return {"created": True, "probe": self._serialize_model_item(probe)}
        if operation == "update":
            probe_data = self._build_probe_payload(arguments)
            probe = probe_service.update_service_probea(team, service, probe_data, user.nick_name)
            return {"updated": True, "probe": self._serialize_model_item(probe)}
        if operation == "delete":
            probe_id = self._require_string(arguments, "probe_id")
            code, msg = probe_service.delete_service_probe(team, service, probe_id)
            if code != 200:
                raise ServiceHandleException(msg="delete probe error", msg_show=msg, status_code=code)
            return {"deleted": True, "probe_id": probe_id}
        raise ServiceHandleException(msg="invalid probe operation", msg_show="不支持的探针操作类型", status_code=400)

    def manage_component_dependency(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        operation = self._normalize_component_operation(
            self._require_string(arguments, "operation"),
            self.DEPENDENCY_OPERATION_ALIASES,
            ("summary", "add", "add_reverse", "delete"),
            "依赖",
        )
        if operation == "summary":
            current = dependency_service.get_service_dependencies(team, service)
            reverse = dependency_service.get_service_dependencies_reverse(service)
            available = dependency_service.get_undependencies(team, service)
            available_reverse = dependency_service.get_reverse_undependencies(team, service)
            return {
                "service_id": service.service_id,
                "dependencies": self._serialize_dependency_items(current),
                "reverse_dependencies": self._serialize_dependency_items(reverse),
                "available_dependencies": self._serialize_dependency_items(available),
                "available_reverse_dependencies": self._serialize_dependency_items(available_reverse),
            }
        if operation == "add":
            dep_service_id = arguments.get("dep_service_id")
            dep_service_ids = arguments.get("dep_service_ids")
            if dep_service_ids:
                if not isinstance(dep_service_ids, list) or not dep_service_ids:
                    raise ServiceHandleException(msg="invalid dep_service_ids", msg_show="参数dep_service_ids无效", status_code=400)
                code, msg = dependency_service.patch_add_dependency(team, service, dep_service_ids, user.nick_name)
                if code != 200:
                    raise ServiceHandleException(msg="add dependency error", msg_show=msg, status_code=code)
                return {"created": True, "dep_service_ids": dep_service_ids}
            if not dep_service_id:
                raise ServiceHandleException(msg="dependency service not specify", msg_show="请指明需要依赖的组件", status_code=400)
            code, msg, data = dependency_service.add_service_dependency(
                team, service, dep_service_id, arguments.get("open_inner", False), arguments.get("container_port"), user.nick_name
            )
            if code == 201:
                return {"created": False, "requires_open_inner": True, "message": msg, "port_list": data}
            if code != 200:
                raise ServiceHandleException(msg="add dependency error", msg_show=msg, status_code=code)
            return {"created": True, "dependency": self._serialize_model_item(data)}
        if operation == "add_reverse":
            be_dep_service_ids = arguments.get("be_dep_service_ids")
            if not isinstance(be_dep_service_ids, list) or not be_dep_service_ids:
                raise ServiceHandleException(msg="invalid be_dep_service_ids", msg_show="参数be_dep_service_ids无效", status_code=400)
            data = dependency_service.patch_add_service_reverse_dependency(
                team, service, ",".join(be_dep_service_ids), user.nick_name
            )
            return {"created": True, "items": data, "total": len(data)}
        if operation == "delete":
            dep_service_id = self._require_string(arguments, "dep_service_id")
            code, msg, data = dependency_service.delete_service_dependency(team, service, dep_service_id, user.nick_name)
            if code != 200:
                raise ServiceHandleException(msg="delete dependency error", msg_show=msg, status_code=code)
            return {"deleted": True, "dependency": self._serialize_model_item(data)}
        raise ServiceHandleException(msg="invalid dependency operation", msg_show="不支持的依赖操作类型", status_code=400)

    def horizontal_scale_component(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        new_node = self._require_int(arguments, "new_node")
        app_manage_service.horizontal_upgrade(team, service, user, new_node, None)
        return {
            "scaled": True,
            "service_id": service.service_id,
            "new_node": new_node,
        }

    def vertical_scale_component(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        new_memory = self._require_int(arguments, "new_memory")
        new_gpu = arguments.get("new_gpu")
        new_cpu = arguments.get("new_cpu")
        code, msg = app_manage_service.vertical_upgrade(team, service, user, new_memory, None, new_gpu, new_cpu)
        if code != 200:
            raise ServiceHandleException(msg="vertical scale error", msg_show=msg, status_code=code)
        return {
            "scaled": True,
            "service_id": service.service_id,
            "new_memory": new_memory,
            "new_gpu": new_gpu,
            "new_cpu": new_cpu,
        }

    def close_apps(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        services = service_repo.get_tenant_region_services(region_name, team.tenant_id)
        if not services:
            return {"closed": True, "service_ids": [], "result": []}
        service_ids = list(services.values_list("service_id", flat=True))
        if arguments.get("service_ids"):
            service_ids = list(set(service_ids) & set(arguments.get("service_ids")))
        code, msg, result = app_manage_service.batch_action(region_name, team, user, "stop", service_ids, None, None)
        if code != 200:
            raise ServiceHandleException(msg="batch close error", msg_show=msg, status_code=code)
        return {
            "closed": True,
            "service_ids": service_ids,
            "result": [self._serialize_model_item(service) for service in result],
        }

    def get_team_apps(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        query = arguments.get("query")
        apps = group_service.get_apps_list(team.tenant_id, region_name, query)
        items = [self._serialize_model_item(app) for app in apps]
        return {"team_name": team.tenant_name, "region_name": region_name, "items": items, "total": len(items)}

    def get_app_version_overview(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        region = self._get_region_by_name_context(user, app.region_name)
        overview = app_version_service.get_overview(team, region, user, app)
        return {"app_id": app.ID, "overview": overview}

    def list_app_version_snapshots(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        relation, _ = app_version_service.get_hidden_template(app.ID)
        items = app_version_service.list_snapshot_versions(app.ID)
        return {
            "app_id": app.ID,
            "has_template": bool(relation),
            "items": items,
            "total": len(items),
        }

    def get_app_version_snapshot_detail(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        detail = app_version_service.get_snapshot_detail(app.ID, self._require_int(arguments, "version_id"))
        if not detail:
            raise ServiceHandleException(msg="snapshot not found", msg_show="快照不存在", status_code=404)
        return {"app_id": app.ID, "detail": detail}

    def create_app_version_snapshot(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        region = self._get_region_by_name_context(user, app.region_name)
        share_info = self._build_snapshot_share_info(arguments)
        snapshot = app_version_service.create_snapshot(
            team,
            region,
            user,
            app,
            version=arguments.get("version", "") or "",
            version_alias=arguments.get("version_alias", "") or "",
            app_version_info=arguments.get("app_version_info", "") or "",
            share_info=share_info,
        )
        return {
            "app_id": app.ID,
            "created": bool(self._value(snapshot, "created", True)),
            "snapshot": snapshot,
        }

    def delete_app_version_snapshot(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        version_id = self._require_int(arguments, "version_id")
        app_version_service.delete_snapshot(app.ID, version_id)
        return {"app_id": app.ID, "version_id": version_id, "deleted": True}

    def rollback_app_version_snapshot(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        region = self._get_region_by_name_context(user, app.region_name)
        version_id = self._require_int(arguments, "version_id")
        record = app_version_service.rollback_snapshot(team, region, user, app, version_id)
        if not record:
            raise ServiceHandleException(
                msg="snapshot rollback not supported",
                msg_show="当前快照暂不支持回滚",
                status_code=400,
            )
        detail = app_version_service.get_rollback_record(team.tenant_name, app.region_name, app.ID, self._value(record, "ID"))
        return {
            "app_id": app.ID,
            "version_id": version_id,
            "rollback_record": detail or record,
        }

    def list_app_version_rollback_records(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        items = app_version_service.list_rollback_records(team.tenant_name, app.region_name, app.ID)
        return {"app_id": app.ID, "items": items, "total": len(items)}

    def get_app_version_rollback_record_detail(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        record_id = self._require_int(arguments, "record_id")
        detail = app_version_service.get_rollback_record(team.tenant_name, app.region_name, app.ID, record_id)
        if not detail:
            raise ServiceHandleException(msg="rollback record not found", msg_show="回滚记录不存在", status_code=404)
        return {"app_id": app.ID, "record": detail}

    def delete_app_version_rollback_record(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        record_id = self._require_int(arguments, "record_id")
        app_version_service.delete_rollback_record(app.ID, record_id)
        return {"app_id": app.ID, "record_id": record_id, "deleted": True}

    def create_app_from_snapshot_version(self, user, arguments):
        team_name = self._require_string(arguments, "team_name")
        region_name = self._require_string(arguments, "region_name")
        source_app_id = self._require_int(arguments, "source_app_id")
        version_id = self._require_int(arguments, "version_id")
        target_app_name = self._require_string(arguments, "target_app_name")
        target_app_note = arguments.get("target_app_note", "") or ""
        k8s_app = arguments.get("k8s_app", "") or ""
        is_deploy = self._parse_bool_with_default(arguments.get("is_deploy"), True)

        team, source_app = self._get_team_app_context(user, team_name, region_name, source_app_id)
        region = self._get_region_by_name_context(user, region_name)
        overview = app_version_service.get_overview(team, region, user, source_app)
        template_id = self._value(overview, "template_id")
        if not template_id:
            raise ServiceHandleException(
                msg="snapshot template not found",
                msg_show="当前应用尚未生成快照模板，请先创建快照",
                status_code=404,
            )
        snapshot_detail = app_version_service.get_snapshot_detail(source_app.ID, version_id)
        if not snapshot_detail:
            raise ServiceHandleException(msg="snapshot not found", msg_show="快照不存在", status_code=404)
        snapshot_version = self._value(snapshot_detail, "version")
        if not snapshot_version:
            raise ServiceHandleException(msg="snapshot version invalid", msg_show="快照版本无效", status_code=400)

        created_app = self._create_app_with_mcp_error_details(
            team=team,
            region_name=region_name,
            app_name=target_app_name,
            app_note=target_app_note,
            username=self._get_username(user),
            k8s_app=k8s_app,
        )
        target_app_id = (
            self._value(created_app, "ID") or
            self._value(created_app, "app_id") or
            self._value(created_app, "group_id")
        )
        if not target_app_id:
            raise ServiceHandleException(msg="create target app failed", msg_show="创建目标应用失败", status_code=500)

        install_result = self.install_app_model(
            user,
            {
                "team_name": team_name,
                "region_name": region_name,
                "app_id": int(target_app_id),
                "source": "local",
                "app_model_id": template_id,
                "app_model_version": snapshot_version,
                "is_deploy": is_deploy,
            },
        )
        return {
            "source_app_id": source_app.ID,
            "source_app_name": source_app.group_name,
            "snapshot": {
                "version_id": version_id,
                "version": snapshot_version,
                "template_id": template_id,
            },
            "target_app": {
                "app_id": int(target_app_id),
                "app_name": self._value(created_app, "app_name") or target_app_name,
                "k8s_app": k8s_app or None,
            },
            "installed": True,
            "install_result": install_result,
        }

    def get_app_publish_candidates(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        scope = self._normalize_publish_scope(arguments.get("scope"))
        market_name = arguments.get("market_name", "") or arguments.get("market_id", "") or ""
        if scope == "goodrain" and not market_name:
            raise ServiceHandleException(msg="market_name is null", msg_show="发布到应用市场时必须指定 market_name", status_code=400)
        data = share_service.get_last_shared_app_and_app_list(
            team.enterprise_id,
            team,
            app.ID,
            scope,
            market_name,
            self._share_market_user_id(user),
            arguments.get("preferred_app_id", "") or None,
            arguments.get("preferred_version", "") or None,
        )
        return {
            "app_id": app.ID,
            "scope": scope,
            "market_name": market_name or None,
            "last_shared_app": data.get("last_shared_app", {}),
            "items": data.get("app_model_list", []),
            "total": len(data.get("app_model_list", []) or []),
        }

    def create_app_share_record(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        scope = arguments.get("scope", "") or ""
        if scope not in ("", "goodrain"):
            raise ServiceHandleException(msg="invalid scope", msg_show="scope只能是空字符串或goodrain", status_code=400)
        target = arguments.get("target") or {}
        if not isinstance(target, dict):
            raise ServiceHandleException(msg="invalid target", msg_show="参数target无效", status_code=400)
        snapshot_mode = self._parse_bool_with_default(arguments.get("snapshot_mode"), False)
        snapshot_app_id = arguments.get("snapshot_app_id", "") or ""
        snapshot_version = arguments.get("snapshot_version", "") or ""
        market_name = None
        if scope == "goodrain":
            market_name = self._value(target, "store_id") or self._value(target, "market_id")
            if not market_name:
                raise ServiceHandleException(msg="target.store_id is null", msg_show="发布到应用市场时必须提供 target.store_id", status_code=400)

        share_check = share_service.check_service_source(team, team.tenant_name, app.ID, app.region_name)
        if share_check and share_check.get("code") == 400:
            raise ServiceHandleException(
                msg="share check failed",
                msg_show=share_check.get("msg_show") or "当前应用不满足发布条件",
                status_code=400,
            )

        if snapshot_mode:
            _, hidden_template = app_version_service.get_or_create_hidden_template(team, user, app)
            snapshot_app_id = hidden_template.app_id if hidden_template else snapshot_app_id

        record = share_service.create_service_share_record(
            group_share_id=make_uuid(),
            group_id=app.ID,
            team_name=team.tenant_name,
            is_success=False,
            step=1,
            share_app_market_name=market_name,
            scope=scope,
            app_id=snapshot_app_id,
            share_version=snapshot_version,
            create_time=datetime.datetime.now(),
            update_time=datetime.datetime.now(),
        )
        return {"app_id": app.ID, "share_record": self._serialize_app_share_record_summary(record, user)}

    def list_app_share_records(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        page, page_size = self._parse_pagination(arguments)
        total, records = share_repo.get_service_share_records_by_groupid(team.tenant_name, app.ID, page, page_size)
        items = []
        skipped = 0
        for record in records:
            if record.status == 0 and not record.share_version:
                skipped += 1
                continue
            items.append(self._serialize_app_share_record_summary(record, user))
        return {
            "app_id": app.ID,
            "items": items,
            "total": max(total - skipped, 0),
            "page": page,
            "page_size": page_size,
        }

    def get_app_share_record(self, user, arguments):
        _, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        record = share_repo.get_service_share_record_by_id(app.ID, self._require_int(arguments, "record_id"))
        if not record:
            raise ServiceHandleException(msg="share record not found", msg_show="发布记录不存在", status_code=404)
        return {"app_id": app.ID, "record": self._serialize_app_share_record_detail(record, user)}

    def delete_app_share_record(self, user, arguments):
        _, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        record = share_repo.get_service_share_record_by_id(app.ID, self._require_int(arguments, "record_id"))
        if not record:
            raise ServiceHandleException(msg="share record not found", msg_show="发布记录不存在", status_code=404)
        record.status = 3
        record.save()
        return {"app_id": app.ID, "record_id": record.ID, "deleted": True}

    def get_app_share_info(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        share_record = self._get_app_share_record_context(team, self._require_int(arguments, "share_id"))
        if share_record.is_success or share_record.step >= 3:
            raise ServiceHandleException(msg="share record is complete", msg_show="分享流程已经完成，请重新进行分享", status_code=400)

        scope = arguments.get("scope", "") or share_record.scope
        if share_record.app_id and share_record.share_version:
            snapshot_version = rainbond_app_repo.get_app_version(share_record.app_id, share_record.share_version)
            if share_service.is_snapshot_publish_version(snapshot_version):
                app_template = json.loads(snapshot_version.app_template)
                return {
                    "share_id": share_record.ID,
                    "publish_mode": "snapshot",
                    "share_info": {
                        "share_service_list": app_template.get("apps", []),
                        "share_plugin_list": app_template.get("plugins", []),
                        "share_k8s_resources": app_template.get("k8s_resources", []),
                    },
                }
        return {
            "share_id": share_record.ID,
            "publish_mode": "runtime",
            "share_info": {
                "share_service_list": share_service.query_share_service_info(team=team, group_id=share_record.group_id, scope=scope),
                "share_plugin_list": share_service.get_group_services_used_plugins(group_id=share_record.group_id),
                "share_k8s_resources": share_service.get_k8s_resources(share_record.group_id),
            },
        }

    def submit_app_share_info(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        share_record = self._get_app_share_record_context(team, self._require_int(arguments, "share_id"))
        if share_record.is_success or share_record.step >= 3:
            raise ServiceHandleException(msg="share record is complete", msg_show="分享流程已经完成，请重新进行分享", status_code=400)
        app_version_info = arguments.get("app_version_info")
        if not isinstance(app_version_info, dict) or not app_version_info.get("app_model_id"):
            raise ServiceHandleException(msg="invalid app_version_info", msg_show="app_version_info无效", status_code=400)
        share_info = {"app_version_info": app_version_info}
        for field in ("share_service_list", "share_plugin_list", "share_k8s_resources"):
            value = arguments.get(field)
            if value is not None:
                if not isinstance(value, list):
                    raise ServiceHandleException(msg="invalid {}".format(field), msg_show="参数{}无效".format(field), status_code=400)
                share_info[field] = value
        code, msg, bean = share_service.create_share_info(
            tenant=team,
            region_name=region_name,
            share_record=share_record,
            share_team=team,
            share_user=user,
            share_info=share_info,
            use_force=self._parse_bool_with_default(arguments.get("use_force"), False),
            user_id=self._share_market_user_id(user),
        )
        if code != 200:
            raise ServiceHandleException(msg="submit share info failed", msg_show=msg, status_code=code)
        if bean and isinstance(bean, dict):
            bean["is_plugin"] = self._parse_bool_with_default(arguments.get("is_plugin"), False)
        return {"share_id": share_record.ID, "submitted": True, "record": bean}

    def list_app_share_events(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        share_record = self._get_app_share_record_context(team, self._require_int(arguments, "share_id"))
        if share_record.is_success or share_record.step >= 3:
            raise ServiceHandleException(msg="share record is complete", msg_show="分享流程已经完成，请重新进行分享", status_code=400)
        event_list = []
        is_complete = True
        for event in ServiceShareRecordEvent.objects.filter(record_id=share_record.ID):
            if event.event_status != "success":
                is_complete = False
            data = event.to_dict()
            data["type"] = "service"
            event_list.append(data)
        for event in PluginShareRecordEvent.objects.filter(record_id=share_record.ID):
            if event.event_status != "success":
                is_complete = False
            data = event.to_dict()
            data["type"] = "plugin"
            event_list.append(data)
        return {"share_id": share_record.ID, "event_list": event_list, "total": len(event_list), "is_complete": is_complete}

    def start_app_share_event(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        share_record = self._get_app_share_record_context(team, self._require_int(arguments, "share_id"))
        event_id = self._require_int(arguments, "event_id")
        event_type = self._normalize_share_event_type(arguments.get("event_type"))
        if event_type == "plugin":
            record_event = PluginShareRecordEvent.objects.filter(record_id=share_record.ID, ID=event_id).first()
            if not record_event:
                raise ServiceHandleException(msg="event not found", msg_show="分享事件不存在", status_code=404)
            bean = share_service.sync_service_plugin_event(user, region_name, team.tenant_name, share_record.ID, record_event)
            return {"share_id": share_record.ID, "event_type": "plugin", "event": self._serialize_model_item(bean) if bean else None}
        record_event = ServiceShareRecordEvent.objects.filter(record_id=share_record.ID, ID=event_id).first()
        if not record_event:
            raise ServiceHandleException(msg="event not found", msg_show="分享事件不存在", status_code=404)
        bean = share_service.sync_event(user, region_name, team.tenant_name, record_event)
        return {"share_id": share_record.ID, "event_type": "service", "event": self._serialize_model_item(bean)}

    def get_app_share_event(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        share_record = self._get_app_share_record_context(team, self._require_int(arguments, "share_id"))
        event_id = self._require_int(arguments, "event_id")
        event_type = self._normalize_share_event_type(arguments.get("event_type"))
        if event_type == "plugin":
            record_event = PluginShareRecordEvent.objects.filter(record_id=share_record.ID, ID=event_id).order_by("ID").first()
            if not record_event:
                raise ServiceHandleException(msg="event not found", msg_show="分享事件不存在", status_code=404)
            if record_event.event_status != "success":
                record_event = share_service.get_sync_plugin_events(region_name, team.tenant_name, record_event)
            return {"share_id": share_record.ID, "event_type": "plugin", "event": self._serialize_model_item(record_event)}
        record_event = ServiceShareRecordEvent.objects.filter(record_id=share_record.ID, ID=event_id).first()
        if not record_event:
            raise ServiceHandleException(msg="event not found", msg_show="分享事件不存在", status_code=404)
        if record_event.event_status != "success":
            record_event = share_service.get_sync_event_result(region_name, team.tenant_name, record_event)
        return {"share_id": share_record.ID, "event_type": "service", "event": self._serialize_model_item(record_event)}

    def complete_app_share(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        share_record = self._get_app_share_record_context(team, self._require_int(arguments, "share_id"))
        pending_count = ServiceShareRecordEvent.objects.filter(record_id=share_record.ID).exclude(event_status="success").count()
        pending_plugin_count = PluginShareRecordEvent.objects.filter(record_id=share_record.ID).exclude(event_status="success").count()
        if pending_count > 0 or pending_plugin_count > 0:
            raise ServiceHandleException(msg="share incomplete", msg_show="组件或插件同步未全部完成", status_code=415)
        app_market_url = share_service.complete(
            team,
            user,
            share_record,
            self._parse_bool_with_default(arguments.get("is_plugin"), False),
            self._share_market_user_id(user),
            region_name,
        )
        return {
            "share_id": share_record.ID,
            "completed": True,
            "record": self._serialize_model_item(share_record),
            "app_market_url": app_market_url,
        }

    def giveup_app_share(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        share_record = self._get_app_share_record_context(team, self._require_int(arguments, "share_id"))
        if share_record.is_success or share_record.step >= 3:
            raise ServiceHandleException(msg="share record is complete", msg_show="分享流程已经完成，无法放弃", status_code=400)
        if share_record.app_id:
            share_service.get_app_version_by_app_id(app_id=share_record.app_id, is_complete=False).delete()
            app = share_service.get_app_by_key(key=share_record.app_id)
            if app:
                app_versions = share_service.get_app_version_by_app_id(app_id=share_record.app_id, is_complete=True)
                archs = list(set([version.arch for version in app_versions if getattr(version, "arch", None)]))
                app.arch = ",".join(archs)
        share_service.delete_record(share_record)
        return {"share_id": share_record.ID, "given_up": True}

    def build_component(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        build_info = arguments.get("build_info") or {}
        if not isinstance(build_info, dict):
            raise ServiceHandleException(msg="invalid build_info", msg_show="参数build_info无效", status_code=400)
        if service.create_status not in ("checked", "complete"):
            raise ServiceHandleException(
                msg="component create status is {}".format(service.create_status),
                msg_show="组件未完成创建，禁止构建",
                status_code=400,
            )
        repo_url = build_info.get("repo_url")
        if repo_url:
            if service.service_source == "source_code":
                service.git_url = repo_url
                service.code_version = build_info.get("branch", "master")
            elif service.service_source in ("docker_run", "docker_compose", "docker_image"):
                service.image = repo_url
            service.save()
        if build_info.get("username") or build_info.get("password"):
            service_source = service_source_repo.get_service_source(service.tenant_id, service.service_id)
            if service_source:
                service_source.user_name = build_info.get("username")
                service_source.password = build_info.get("password")
                service_source.save()
            else:
                console_app_service.create_service_source_info(
                    team, service, build_info.get("username"), build_info.get("password")
                )
        is_deploy = bool(arguments.get("is_deploy", True))
        if service.create_status != "complete":
            if service.service_source == "third_party":
                is_deploy = False
                service = console_app_service.create_third_party_service(team, service, self._get_username(user))
            else:
                service = console_app_service.create_region_service(team, service, self._get_username(user))

        event_id = None
        if is_deploy:
            arch_service.update_affinity_by_arch(service.arch, team, app.region_name, service)
            code, message, event_id = app_manage_service.deploy(team, service, user)
            if code != 200:
                raise ServiceHandleException(msg=message, msg_show=message, status_code=code)
            deploy_repo.create_deploy_relation_by_service_id(service_id=service.service_id)
        return {
            "app_id": app.ID,
            "service_id": service.service_id,
            "event_id": event_id,
            "create_status": service.create_status,
            "built": True,
            "is_deploy": is_deploy,
        }

    def get_app_last_upgrade_record(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        upgrade_group_id = self._parse_optional_positive_int(arguments.get("upgrade_group_id"), "upgrade_group_id")
        record_type = self._normalize_upgrade_record_type(arguments.get("record_type"))
        record = upgrade_service.get_latest_upgrade_record(team, app, upgrade_group_id, record_type)
        serialized = self._serialize_upgrade_record_basic(record)
        return {
            "app_id": app.ID,
            "upgrade_group_id": upgrade_group_id,
            "record_type": record_type or self._value(serialized, "record_type"),
            "exists": bool(serialized),
            "record": serialized,
        }

    def query_app_upgrade_records(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        page, page_size = self._parse_pagination(arguments)
        record_type = self._normalize_upgrade_record_type(arguments.get("record_type")) or "upgrade"
        items, total = upgrade_service.list_records(team.tenant_name, app.region_name, app.ID, record_type, page, page_size)
        items = [self._serialize_upgrade_record_basic(item) for item in items]
        return {
            "app_id": app.ID,
            "record_type": record_type,
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def create_app_upgrade_record(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        upgrade_group_id = self._require_int(arguments, "upgrade_group_id")
        record = upgrade_service.create_upgrade_record(user.enterprise_id, team, app, upgrade_group_id)
        return {
            "app_id": app.ID,
            "upgrade_group_id": upgrade_group_id,
            "created": True,
            "record": self._serialize_upgrade_record_basic(record),
        }

    def get_app_upgrade_record(self, user, arguments):
        team, app, record = self._get_team_app_upgrade_record_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_int(arguments, "record_id"),
        )
        detail = upgrade_service.get_app_upgrade_record(team.tenant_name, app.region_name, record.ID)
        return {
            "app_id": app.ID,
            "record": self._serialize_upgrade_record_detail(detail),
        }

    def get_app_upgrade_detail(self, user, arguments):
        _, app, record = self._get_team_app_upgrade_record_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_int(arguments, "record_id"),
        )
        versions = market_app_service.list_app_upgradeable_versions(user.enterprise_id, record)
        return {
            "app_id": app.ID,
            "detail": {
                "record": self._serialize_upgrade_record_basic(record),
                "versions": versions,
                "total": len(versions or []),
            },
        }

    def get_app_upgrade_changes(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        region = self._get_region_by_name_context(user, app.region_name)
        version = self._require_string(arguments, "version")
        upgrade_group_id = self._parse_optional_positive_int(arguments.get("upgrade_group_id"), "upgrade_group_id")
        app_changes, changes = upgrade_service.get_property_changes(team, region, user, app, upgrade_group_id, version)
        return {
            "app_id": app.ID,
            "upgrade_group_id": upgrade_group_id,
            "version": version,
            "app_changes": app_changes,
            "changes": changes,
            "total": len(changes or []),
        }

    def execute_app_upgrade_record(self, user, arguments):
        team, app, record = self._get_team_app_upgrade_record_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_int(arguments, "record_id"),
        )
        region = self._get_region_by_name_context(user, app.region_name)
        version = self._require_string(arguments, "version")
        services = arguments.get("services") or []
        if services and not isinstance(services, list):
            raise ServiceHandleException(msg="invalid services", msg_show="参数services无效", status_code=400)
        component_keys = []
        for component in services:
            if not isinstance(component, dict):
                raise ServiceHandleException(msg="invalid services", msg_show="参数services无效", status_code=400)
            service_info = component.get("service") or {}
            service_key = service_info.get("service_key")
            if not service_key:
                raise ServiceHandleException(
                    msg="invalid services",
                    msg_show="services[*].service.service_key不能为空",
                    status_code=400,
                )
            component_keys.append(service_key)
        upgraded_record, app_template_name = upgrade_service.upgrade(
            team, region, user, app, version, record, component_keys
        )
        return {
            "app_id": app.ID,
            "record_id": self._value(upgraded_record, "ID"),
            "version": version,
            "upgraded": True,
            "app_template_name": app_template_name,
            "record": self._serialize_upgrade_record_detail(upgraded_record),
        }

    def deploy_app_upgrade_record(self, user, arguments):
        team, app, record = self._get_team_app_upgrade_record_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_int(arguments, "record_id"),
        )
        upgrade_service.deploy(team, app.region_name, user, record)
        detail = upgrade_service.get_app_upgrade_record(team.tenant_name, app.region_name, record.ID)
        return {
            "app_id": app.ID,
            "record_id": record.ID,
            "deployed": True,
            "record": self._serialize_upgrade_record_detail(detail),
        }

    def get_app_rollback_records(self, user, arguments):
        _, app, record = self._get_team_app_upgrade_record_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_int(arguments, "record_id"),
        )
        items = upgrade_service.list_rollback_record(record)
        items = [self._serialize_upgrade_record_basic(item) for item in items]
        return {
            "app_id": app.ID,
            "parent_record_id": record.ID,
            "items": items,
            "total": len(items),
        }

    def rollback_app_upgrade_record(self, user, arguments):
        team, app, record = self._get_team_app_upgrade_record_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_int(arguments, "record_id"),
        )
        region = self._get_region_by_name_context(user, app.region_name)
        rollback_record, component_group_alias = upgrade_service.restore(team, region, user, app, record)
        return {
            "app_id": app.ID,
            "record_id": self._value(rollback_record, "ID"),
            "rolled_back": True,
            "component_group_alias": component_group_alias,
            "record": self._serialize_upgrade_record_detail(rollback_record),
        }

    def get_app_upgrade_info(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        items = market_app_service.get_market_apps_in_app(app.region_name, team, app)
        return {"app_id": app.ID, "items": items, "total": len(items)}

    def upgrade_app(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        update_versions = arguments.get("update_versions")
        if not isinstance(update_versions, list) or not update_versions:
            raise ServiceHandleException(msg="invalid update_versions", msg_show="参数update_versions无效", status_code=400)
        upgrade_service.openapi_upgrade_app_models(user, team, app.region_name, None, app.ID, {
            "update_versions": update_versions
        })
        items = market_app_service.get_market_apps_in_app(app.region_name, team, app)
        return {"app_id": app.ID, "upgraded": True, "items": items, "total": len(items)}

    def get_copy_app_info(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        items = groupapp_copy_service.get_group_services_with_build_source(team, app.region_name, app.ID)
        return {"app_id": app.ID, "items": items, "total": len(items)}

    def copy_app(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        target_team_name = self._require_string(arguments, "target_team_name")
        target_region_name = self._require_string(arguments, "target_region_name")
        target_app_id = self._require_int(arguments, "target_app_id")
        services = arguments.get("services") or []
        if not isinstance(services, list):
            raise ServiceHandleException(msg="invalid services", msg_show="参数services无效", status_code=400)
        target_team, target_group = groupapp_copy_service.check_and_get_team_group(
            user, target_team_name, target_region_name, target_app_id
        )
        copied_services = groupapp_copy_service.copy_group_services(
            user, team, app.region_name, target_team, target_region_name, target_group, app.ID, services
        )
        copied_services = domain_service.get_components_that_contains_gateway_rules(target_region_name, copied_services)
        items = [self._serialize_service_with_gateway_rules(service) for service in copied_services]
        return {
            "app_id": app.ID,
            "target_app_id": target_group.ID,
            "target_team_name": target_team.tenant_name,
            "target_region_name": target_region_name,
            "items": items,
            "total": len(items),
        }

    def install_app_by_market(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        market_url = self._require_string(arguments, "market_url")
        market_domain = self._require_string(arguments, "market_domain")
        market_type = self._require_string(arguments, "market_type")
        market_access_key = self._require_string(arguments, "market_access_key")
        app_model_id = self._require_string(arguments, "app_model_id")
        app_model_version = self._require_string(arguments, "app_model_version")
        is_deploy = bool(arguments.get("is_deploy", False))

        market = app_market_service.get_app_market_by_domain_url(team.enterprise_id, market_domain, market_url)
        if not market:
            market_name = make_uuid()
            app_market_service.create_app_market({
                "name": market_name,
                "url": market_url,
                "type": market_type,
                "enterprise_id": team.enterprise_id,
                "access_key": market_access_key,
                "domain": market_domain,
            })
            _, market = app_market_service.get_app_market(team.enterprise_id, market_name, raise_exception=True)

        market_app, app_version_info = app_market_service.cloud_app_model_to_db_model(
            market, app_model_id, app_model_version, for_install=True
        )
        if not market_app:
            raise ServiceHandleException(status_code=404, msg="not found", msg_show="云端应用不存在")
        if not app_version_info:
            raise ServiceHandleException(status_code=404, msg="not found", msg_show="云端应用版本不存在")

        market_app_service.install_service(
            team, app.region_name, user, app.ID, market_app, app_version_info, is_deploy, True, market_name=market.name
        )
        services = group_service.get_group_services(app.ID)
        return {
            "installed": True,
            "app_id": app.ID,
            "app_name": app.group_name,
            "market_name": market.name,
            "service_list": [self._serialize_model_item(service) for service in services],
        }

    def query_cloud_markets(self, user, arguments):
        enterprise_id = self._require_string(arguments, "enterprise_id")
        self._ensure_enterprise_access(user, enterprise_id)
        extend = "true" if self._parse_bool_with_default(arguments.get("extend"), True) else "false"
        items = app_market_service.get_app_markets(enterprise_id, extend)
        return {
            "enterprise_id": enterprise_id,
            "items": [self._serialize_model_item(item) for item in items],
            "total": len(items),
        }

    def query_local_app_models(self, user, arguments):
        enterprise_id = self._require_string(arguments, "enterprise_id")
        self._ensure_enterprise_access(user, enterprise_id)
        page, page_size = self._parse_pagination(arguments)
        query = arguments.get("query") or arguments.get("app_name")
        scope = (arguments.get("scope") or "enterprise").strip().lower()
        if scope not in ("enterprise", "team", ""):
            raise ServiceHandleException(msg="invalid scope", msg_show="参数scope无效", status_code=400)
        arch = (arguments.get("arch") or "").strip()
        tenant_name = (arguments.get("tenant_name") or "").strip()
        is_plugin = self._normalize_bool_query_value(arguments.get("is_plugin"))
        apps, total, _ = market_app_service.get_visiable_apps(
            scope, query, True, page, page_size, "", arch, tenant_name, is_plugin
        )
        items = []
        for app_model in apps:
            data = self._serialize_model_item(app_model)
            data["versions_info"] = getattr(app_model, "versions_info", [])
            data["min_memory"] = getattr(app_model, "min_memory", 0)
            items.append(data)
        return {
            "enterprise_id": enterprise_id,
            "scope": scope or "all",
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def query_cloud_app_models(self, user, arguments):
        enterprise_id = self._require_string(arguments, "enterprise_id")
        market_name = self._require_string(arguments, "market_name")
        self._ensure_enterprise_access(user, enterprise_id)
        page, page_size = self._parse_pagination(arguments)
        query = arguments.get("query")
        arch = (arguments.get("arch") or "").strip()
        query_all = self._parse_bool_with_default(arguments.get("query_all"), False)
        is_plugin = self._parse_bool_with_default(arguments.get("is_plugin"), False)
        _, market = app_market_service.get_app_market(enterprise_id, market_name, raise_exception=True)
        if is_plugin:
            items, page, page_size, total = app_market_service.get_market_plugins_apps(
                market, page, page_size, query=query, query_all=query_all, extend=True
            )
        else:
            items, page, page_size, total = app_market_service.get_market_app_list(
                market, page, page_size, query=query, query_all=query_all, extend=True, arch=arch
            )
        return {
            "enterprise_id": enterprise_id,
            "market_name": market_name,
            "items": [self._serialize_model_item(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def query_app_model_versions(self, user, arguments):
        enterprise_id = self._require_string(arguments, "enterprise_id")
        app_model_id = self._require_string(arguments, "app_model_id")
        source = self._normalize_app_model_source(arguments.get("source"))
        self._ensure_enterprise_access(user, enterprise_id)

        if source == "local":
            page, page_size = self._parse_pagination(arguments)
            app_model, versions, total = market_app_service.get_rainbond_app_and_versions(
                enterprise_id, app_model_id, page, page_size
            )
            return {
                "enterprise_id": enterprise_id,
                "source": source,
                "app_model": self._serialize_model_item(app_model),
                "items": [self._serialize_model_item(item) for item in (versions or [])],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        market_name = self._require_string(arguments, "market_name")
        _, market = app_market_service.get_app_market(enterprise_id, market_name, raise_exception=True)
        app_model = app_market_service.get_market_app_model(market, app_model_id, extend=True)
        items = app_market_service.get_market_app_model_versions(
            market, app_model_id, query_all=self._parse_bool_with_default(arguments.get("query_all"), False), extend=True
        )
        serialized_items = [self._serialize_model_item(item) for item in (items or [])]
        page, page_size = self._parse_pagination(arguments)
        result = self._paginate_data(serialized_items, page, page_size)
        result.update({
            "enterprise_id": enterprise_id,
            "source": source,
            "market_name": market_name,
            "app_model": self._serialize_model_item(app_model),
            "app_model_id": app_model_id,
        })
        return result

    def install_app_model(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        region = self._get_region_by_name_context(user, app.region_name)
        source = self._normalize_app_model_source(arguments.get("source"))
        market_name = (arguments.get("market_name") or "").strip()
        if source == "cloud" and not market_name:
            raise ServiceHandleException(
                msg="invalid market_name", msg_show="云市场安装时必须提供market_name", status_code=400
            )

        installed_app_name = market_app_service.install_app(
            team,
            region,
            user,
            app.ID,
            self._require_string(arguments, "app_model_id"),
            self._require_string(arguments, "app_model_version"),
            market_name,
            source == "cloud",
            self._parse_bool_with_default(arguments.get("is_deploy"), True),
        )
        services = group_service.get_group_services(app.ID)
        return {
            "installed": True,
            "source": source,
            "app_id": app.ID,
            "app_name": app.group_name,
            "installed_app_name": installed_app_name,
            "market_name": market_name or None,
            "service_list": [self._serialize_model_item(service) for service in services],
        }

    def create_component_from_source(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        return source_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            service_cname=self._require_string(arguments, "service_cname"),
            code_from=self._require_string(arguments, "code_from"),
            git_url=self._require_string(arguments, "git_url"),
            git_project_id=arguments.get("git_project_id"),
            code_version=arguments.get("code_version", "master") or "master",
            server_type=arguments.get("server_type"),
            version_type=arguments.get("version_type"),
            subdirectories=arguments.get("subdirectories"),
            username=arguments.get("username", "") or "",
            password=arguments.get("password", "") or "",
            check_uuid=arguments.get("check_uuid"),
            event_id=arguments.get("event_id"),
            oauth_service_id=arguments.get("oauth_service_id"),
            full_name=arguments.get("full_name"),
            k8s_component_name=arguments.get("k8s_component_name", "") or "",
            arch=arguments.get("arch", "amd64") or "amd64",
            is_deploy=bool(arguments.get("is_deploy", True)),
            prefer_dockerfile_when_detected=bool(arguments.get("prefer_dockerfile_when_detected", False)),
        )

    def create_component_from_package(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        return package_component_service.auto_create_component(
            team=team,
            app=app,
            user=user,
            event_id=self._require_string(arguments, "event_id"),
            service_cname=self._require_string(arguments, "service_cname"),
            k8s_component_name=arguments.get("k8s_component_name", "") or "",
            arch=arguments.get("arch", "amd64") or "amd64",
            is_deploy=bool(arguments.get("is_deploy", True)),
        )

    def init_package_upload(self, user, arguments):
        team_name = self._require_string(arguments, "team_name")
        region_name = self._require_string(arguments, "region_name")
        self._get_team_context(user, team_name)
        self._get_region_by_name_context(user, region_name)
        return package_upload_tool_service.init_upload(
            team_name,
            region_name,
            arguments.get("component_id", "") or "",
        )

    def upload_package_file(self, user, arguments):
        team_name = self._require_string(arguments, "team_name")
        region_name = self._require_string(arguments, "region_name")
        self._get_team_context(user, team_name)
        self._get_region_by_name_context(user, region_name)
        return package_upload_tool_service.upload_package(
            team_name,
            region_name,
            self._require_string(arguments, "event_id"),
            self._require_string(arguments, "local_path"),
            arguments.get("archive_name", "") or "",
        )

    def get_package_upload_status(self, user, arguments):
        team_name = self._require_string(arguments, "team_name")
        region_name = self._require_string(arguments, "region_name")
        self._get_team_context(user, team_name)
        self._get_region_by_name_context(user, region_name)
        return package_upload_tool_service.get_upload_status(
            team_name,
            region_name,
            self._require_string(arguments, "event_id"),
        )

    def delete_package_upload(self, user, arguments):
        team_name = self._require_string(arguments, "team_name")
        region_name = self._require_string(arguments, "region_name")
        self._get_team_context(user, team_name)
        self._get_region_by_name_context(user, region_name)
        return package_upload_tool_service.delete_upload(
            team_name,
            region_name,
            self._require_string(arguments, "event_id"),
        )

    def create_component_from_local_package(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        return package_upload_tool_service.auto_create_component_from_local_path(
            team=team,
            app=app,
            user=user,
            local_path=self._require_string(arguments, "local_path"),
            service_cname=self._require_string(arguments, "service_cname"),
            k8s_component_name=arguments.get("k8s_component_name", "") or "",
            arch=arguments.get("arch", "amd64") or "amd64",
            is_deploy=bool(arguments.get("is_deploy", True)),
            archive_name=arguments.get("archive_name", "") or "",
        )

    def check_component(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        is_again = bool(arguments.get("is_again", False))
        event_id = arguments.get("event_id", "") or ""
        code, msg, service_info = app_check_service.check_service(team, service, is_again, event_id, user)
        if code != 200:
            raise ServiceHandleException(msg="check service error", msg_show=msg, status_code=code)
        return {
            "app_id": app.ID,
            "service_id": service.service_id,
            "check_uuid": service.check_uuid,
            "check_event_id": service.check_event_id,
            "create_status": service.create_status,
            "workflow_stage": "checking",
            "next_action": "rainbond_get_component_check_result",
            "check_info": service_info,
        }

    def get_component_check_result(self, user, arguments):
        team, app, service = self._get_team_app_service_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
            self._require_string(arguments, "service_id"),
        )
        prefer_dockerfile_when_detected = bool(arguments.get("prefer_dockerfile_when_detected", False))
        check_uuid = arguments.get("check_uuid") or service.check_uuid
        if not check_uuid:
            raise ServiceHandleException(msg="check_uuid required", msg_show="参数check_uuid无效", status_code=400)
        code, msg, data = app_check_service.get_service_check_info(team, service.service_region, check_uuid)
        if code != 200:
            raise ServiceHandleException(msg="get check result error", msg_show=msg, status_code=code)

        if service.create_status == "complete":
            service_info = data.get("service_info")
            if not (service_info is not None and len(service_info) > 1 and service_info[0].get("language") == "Java-maven"):
                app_check_service.update_service_check_info(team, service, data)
            check_brief_info = app_check_service.wrap_service_check_info(service, data)
        else:
            service_info_list = data.get("service_info") or []
            if service_info_list and len(service_info_list) < 2:
                if prefer_dockerfile_when_detected:
                    # Re-detect recovery path: apply the same Dockerfile preference
                    # create_component_from_source uses, so a component whose
                    # language is CNB-classified but ships a Dockerfile persists as
                    # a Dockerfile build (build_strategy="") instead of dead-ending
                    # on CNB (e.g. .NET 7 rejected by the CNB version policy).
                    service_info_list[0] = source_component_service._select_service_info(
                        service_info_list[0], True
                    )
                    data["service_info"] = service_info_list
                app_check_service.save_service_check_info(team, app.ID, service, data)
            check_brief_info = app_check_service.wrap_service_check_info(service, data)

        return {
            "app_id": app.ID,
            "service_id": service.service_id,
            "check_uuid": check_uuid,
            "create_status": service.create_status,
            "workflow_stage": "checked" if check_brief_info.get("check_status") == "success" else check_brief_info.get(
                "check_status"
            ),
            "can_build": check_brief_info.get("check_status") == "success" and service.create_status in (
                "checked", "complete"
            ),
            "next_action": "rainbond_build_component" if check_brief_info.get("check_status") == "success" else None,
            "check_result": check_brief_info,
        }

    def create_component_from_image(self, user, arguments):
        return self.create_component(user, arguments)

    def create_app_from_yaml(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        app_id = self._require_int(arguments, "app_id")
        app = group_service.get_app_by_id(team, region_name, app_id)
        if not app:
            raise ServiceHandleException(msg="app not found", msg_show="应用不存在", status_code=404)
        event_id = self._require_string(arguments, "event_id")
        compose_file_path = arguments.get("compose_file_path", "docker-compose.yml") or "docker-compose.yml"
        code, msg, group_compose = compose_service.create_group_compose(
            team,
            region_name,
            app.ID,
            event_id,
            compose_file_path,
            arguments.get("user_name", "") or "",
            arguments.get("password", "") or "",
        )
        if code != 200:
            raise ServiceHandleException(msg="create group compose error", msg_show=msg, status_code=code)
        return {
            "app_id": app.ID,
            "app_name": app.group_name,
            "group_id": group_compose.group_id,
            "compose_id": group_compose.compose_id,
        }

    def check_yaml_app(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        compose_id = self._require_string(arguments, "compose_id")
        code, msg, compose_bean = compose_service.check_compose(app.region_name, team, compose_id)
        if code != 200:
            raise ServiceHandleException(msg="check compose error", msg_show=msg, status_code=code)
        return compose_bean

    def get_yaml_app_check_result(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        compose_id = self._require_string(arguments, "compose_id")
        check_uuid = self._require_string(arguments, "check_uuid")
        group_compose = compose_service.get_group_compose_by_compose_id(compose_id)
        if not group_compose:
            raise ServiceHandleException(msg="compose not found", msg_show="compose不存在", status_code=404)
        code, msg, data = app_check_service.get_service_check_info(team, app.region_name, check_uuid)
        if code != 200:
            raise ServiceHandleException(msg="check info failure", msg_show=msg, status_code=code)
        save_code, save_msg, service_list = compose_service.save_compose_services(
            team, user, app.region_name, group_compose, data, arguments.get("arch", "amd64")
        )
        if save_code != 200:
            raise ServiceHandleException(msg="save compose info error", msg_show=save_msg, status_code=save_code)
        compose_check_brief = compose_service.wrap_compose_check_info(data)
        return {
            "compose_id": compose_id,
            "check_uuid": check_uuid,
            "bean": compose_check_brief,
            "services": [self._serialize_model_item(service) for service in service_list],
        }

    def query_app_monitor(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        is_outer = bool(arguments.get("is_outer", False))
        services = self._get_app_monitor_services(app, is_outer)
        data = []
        for service in services:
            monitors = []
            for key, query in list(monitor_query_items.items()):
                _, body = region_api.get_query_data(app.region_name, team.tenant_name, query % service.service_id)
                if body.get("data") and body["data"].get("result"):
                    result_list = []
                    for result in body["data"]["result"]:
                        result["value"] = [str(value) for value in result["value"]]
                        result_list.append(result)
                    body["data"]["result"] = result_list
                    monitors.append({"monitor_item": key, "data": body["data"]})
            data.append({
                "service_id": service.service_id,
                "service_cname": service.service_cname,
                "service_alias": service.service_alias,
                "monitors": monitors,
            })
        return {"app_id": app.ID, "items": data, "total": len(data)}

    def query_app_monitor_range(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        start = self._require_string(arguments, "start")
        end = self._require_string(arguments, "end")
        step = self._parse_int_with_default(arguments.get("step"), 60)
        is_outer = bool(arguments.get("is_outer", False))
        services = self._get_app_monitor_services(app, is_outer)
        data = []
        for service in services:
            monitors = []
            for key, query in list(monitor_query_range_items.items()):
                _, body = region_api.get_query_range_data(
                    app.region_name, team.tenant_name, query % (service.service_id, start, end, step)
                )
                if body.get("data") and body["data"].get("result"):
                    result_list = []
                    for result in body["data"]["result"]:
                        result["value"] = [str(value) for value in result["value"]]
                        result_list.append(result)
                    body["data"]["result"] = result_list
                    monitors.append({"monitor_item": key, "data": body["data"]})
            data.append({
                "service_id": service.service_id,
                "service_cname": service.service_cname,
                "service_alias": service.service_alias,
                "monitors": monitors,
            })
        return {"app_id": app.ID, "items": data, "total": len(data), "start": start, "end": end, "step": step}

    def create_gateway_rules(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        protocol = self._require_string(arguments, "protocol")
        if protocol == "http":
            httpdomain = arguments.get("http")
            if not isinstance(httpdomain, dict):
                raise ServiceHandleException(msg="missing http", msg_show="缺少参数http", status_code=400)
            httpdomain["domain_heander"] = httpdomain.get("domain_header", None)
            httpdomain["domain_type"] = "www"
            httpdomain["protocol"] = "https" if httpdomain.get("certificate_id") else "http"
            service = self._get_service_in_team_app(team, app, self._require_string(httpdomain, "service_id"))
            if domain_service.check_domain_exist(
                    httpdomain["service_id"], httpdomain["container_port"], httpdomain["domain_name"],
                    httpdomain["protocol"], httpdomain.get("domain_path"), httpdomain.get("rule_extensions")):
                raise ServiceHandleException(msg="exist", msg_show="策略已存在", status_code=400)
            if service.service_source == "third_party":
                msg, msg_show, code = port_service.check_domain_thirdpart(team, service)
                if code != 200:
                    raise ServiceHandleException(msg=msg, msg_show=msg_show, status_code=code)
            if httpdomain.get("whether_open", True):
                tenant_service_port = port_service.get_service_port_by_port(service, httpdomain["container_port"])
                code, msg, _ = port_service.manage_port(
                    team, service, service.service_region, int(tenant_service_port.container_port), "only_open_outer",
                    tenant_service_port.protocol, tenant_service_port.port_alias
                )
                if code != 200:
                    raise ServiceHandleException(msg="change port fail", msg_show=msg, status_code=code)
            tenant_service_port = port_service.get_service_port_by_port(service, httpdomain["container_port"])
            if not tenant_service_port or not tenant_service_port.is_outer_service:
                raise ServiceHandleException(msg="port not open", msg_show="没有开启对外端口", status_code=400)
            data = domain_service.bind_httpdomain(team, user, service, httpdomain, True)
            try:
                region_api.api_gateway_bind_http_domain(
                    service.service_alias, app.region_name, team.tenant_name, [httpdomain["domain_name"]],
                    tenant_service_port, app.ID)
            except Exception as e:
                logger.warning("create apisix route failed: %s", str(e))
            return self._serialize_model_item(data)
        if protocol == "tcp":
            tcpdomain = arguments.get("tcp")
            if not isinstance(tcpdomain, dict):
                raise ServiceHandleException(msg="missing tcp", msg_show="缺少参数tcp", status_code=400)
            service = self._get_service_in_team_app(team, app, self._require_string(tcpdomain, "service_id"))
            if service.service_source == "third_party":
                msg, msg_show, code = port_service.check_domain_thirdpart(team, service)
                if code != 200:
                    raise ServiceHandleException(msg=msg, msg_show=msg_show, status_code=code)
            tenant_service_port = port_service.get_service_port_by_port(service, tcpdomain["container_port"])
            code, msg, _ = port_service.manage_port(
                team, service, service.service_region, int(tenant_service_port.container_port), "only_open_outer",
                tenant_service_port.protocol, tenant_service_port.port_alias
            )
            if code != 200:
                raise ServiceHandleException(msg="change port fail", msg_show="open port failure", status_code=code)
            data = domain_service.bind_tcpdomain(
                team, user, service, tcpdomain["end_point"], tcpdomain["container_port"], tcpdomain["default_port"],
                tcpdomain.get("rule_extensions"), tcpdomain.get("default_ip")
            )
            return data
        raise ServiceHandleException(msg="error parameters: protocol", msg_show="错误参数: protocol", status_code=400)

    def check_helm_app(self, user, arguments):
        team = self._get_team_context(user, self._require_string(arguments, "team_name"))
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        name = self._require_string(arguments, "name")
        repo_name = self._require_string(arguments, "repo_name")
        chart_name = self._require_string(arguments, "chart_name")
        version = self._require_string(arguments, "version")
        overrides = arguments.get("overrides") or []
        _, data = helm_app_service.check_helm_app(
            name, repo_name, chart_name, version, overrides, region_name, team.tenant_name, team
        )
        return data

    def build_helm_app(self, user, arguments):
        team, app = self._get_team_app_context(
            user,
            self._require_string(arguments, "team_name"),
            self._require_string(arguments, "region_name"),
            self._require_int(arguments, "app_id"),
        )
        name = self._require_string(arguments, "name")
        repo_name = self._require_string(arguments, "repo_name")
        chart_name = self._require_string(arguments, "chart_name")
        version = self._require_string(arguments, "version")
        app_model_id = self._require_string(arguments, "app_model_id")
        overrides = arguments.get("overrides") or {}
        overrides_list = []
        if isinstance(overrides, dict):
            for key, value in overrides.items():
                overrides_list.append("{}={}".format(key, value))
        elif isinstance(overrides, list):
            overrides_list = overrides
        cvdata = helm_app_service.yaml_conversion(
            name, repo_name, chart_name, version, overrides_list, app.region_name, team.tenant_name, team,
            team.enterprise_id, self._value(self._get_region_by_name_context(user, app.region_name), "region_id")
        )
        helm_center_app = rainbond_app_repo.get_rainbond_app_by_app_id(app_model_id)
        chart = repo_name + "/" + chart_name
        helm_app_service.generate_template(
            cvdata, helm_center_app, version, team, chart, app.region_name, team.enterprise_id, user.user_id,
            overrides_list, app.ID
        )
        return {
            "built": True,
            "app_id": app.ID,
            "app_model_id": app_model_id,
            "chart": chart,
            "version": version,
        }

    def query_enterprises(self, user, arguments):
        self._ensure_enterprise_admin(user)
        query = (arguments.get("query") or "").strip().lower()
        page, page_size = self._parse_pagination(arguments)
        enterprise_list = self._get_user_enterprises(user)

        items = []
        for enterprise in enterprise_list:
            enterprise_name = getattr(enterprise, "enterprise_name", "") or ""
            enterprise_alias = getattr(enterprise, "enterprise_alias", "") or ""
            if query and query not in enterprise_name.lower() and query not in enterprise_alias.lower():
                continue
            items.append(self._serialize_enterprise(enterprise))

        return self._paginate_data(items, page, page_size)

    def query_regions(self, user, arguments):
        self._ensure_enterprise_admin(user)
        enterprise_id = (arguments.get("enterprise_id") or getattr(user, "enterprise_id", "") or "").strip()
        if not enterprise_id:
            raise ServiceHandleException(msg="invalid enterprise_id", msg_show="参数enterprise_id无效", status_code=400)
        if enterprise_id != getattr(user, "enterprise_id", None):
            self._raise_permission_denied("无该企业集群访问权限")

        page, page_size = self._parse_pagination(arguments)
        query = (arguments.get("query") or "").strip().lower()
        regions = region_services.get_enterprise_regions(enterprise_id)

        items = []
        for region in regions:
            region_name = self._value(region, "region_name", "") or ""
            region_alias = self._value(region, "region_alias", "") or ""
            if query and query not in region_name.lower() and query not in region_alias.lower():
                continue
            items.append(self._serialize_region(region))

        return self._paginate_data(items, page, page_size)

    def get_region_detail(self, user, arguments):
        self._ensure_enterprise_admin(user)
        region_id = self._require_string(arguments, "region_id")
        region_model = self._get_region_model(user, region_id)
        region_data = self._serialize_region(region_model)
        if arguments.get("extend_info", False):
            region_detail = self._get_region_context(user, region_id, check_status=True)
            merged = dict(region_data)
            merged.update(self._serialize_region(region_detail))
            return merged
        return region_data

    def create_region(self, user, arguments):
        self._ensure_enterprise_admin(user)
        region_data = self._build_create_region_data(arguments, user.enterprise_id)
        region = region_services.add_region(region_data, user)
        return {
            "created": True,
            "region": self._serialize_region(region),
        }

    def update_region(self, user, arguments):
        self._ensure_enterprise_admin(user)
        region_id = self._require_string(arguments, "region_id")
        region_model = self._get_region_model(user, region_id)
        current_region_data = self._build_region_update_data(region_model)
        update_data = self._build_update_region_data(arguments)
        region_data = dict(current_region_data)
        region_data.update(update_data)
        region = region_services.update_region(region_data)
        return {
            "updated": True,
            "region": self._serialize_region(region),
        }

    def delete_region(self, user, arguments):
        self._ensure_enterprise_admin(user)
        region_id = self._require_string(arguments, "region_id")
        self._get_region_model(user, region_id)
        deleted_region = region_services.del_by_region_id(region_id)
        return {
            "deleted": True,
            "region": self._serialize_region(deleted_region),
        }

    def query_region_nodes(self, user, arguments):
        self._ensure_enterprise_admin(user)
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        nodes, cluster_role_count = enterprise_services.get_nodes(region_name)
        return {
            "region_name": region_name,
            "nodes": nodes,
            "cluster_role_count": cluster_role_count,
            "total": len(nodes),
        }

    def get_region_node_detail(self, user, arguments):
        self._ensure_enterprise_admin(user)
        region_name = self._require_string(arguments, "region_name")
        node_name = self._require_string(arguments, "node_name")
        self._get_region_by_name_context(user, region_name)
        return enterprise_services.get_node_detail(region_name, node_name)

    def query_region_rbd_components(self, user, arguments):
        self._ensure_enterprise_admin(user)
        region_name = self._require_string(arguments, "region_name")
        self._get_region_by_name_context(user, region_name)
        items = enterprise_services.get_rbdcomponents(region_name)
        return {
            "region_name": region_name,
            "items": items,
            "total": len(items),
        }

    def query_teams(self, user, arguments):
        enterprise_id = self._require_string(arguments, "enterprise_id")
        self._ensure_enterprise_access(user, enterprise_id)
        page, page_size = self._parse_pagination(arguments)
        query = arguments.get("query")

        teams, total = team_services.get_enterprise_teams(
            enterprise_id=enterprise_id,
            query=query,
            page=page,
            page_size=page_size,
            user=user,
        )

        return {
            "items": teams,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def query_apps(self, user, arguments):
        enterprise_id = self._require_string(arguments, "enterprise_id")
        self._ensure_enterprise_access(user, enterprise_id)
        page, page_size = self._parse_pagination(arguments)
        query = (arguments.get("query") or "").strip().lower()

        tenant_ids = enterprise_repo.get_enterprise_tenant_ids(enterprise_id, user)
        if not tenant_ids:
            return self._empty_page(page, page_size)

        apps_queryset = group_repo.get_groups_by_tenant_ids(tenant_ids)
        items = []
        for app in apps_queryset:
            app_name = getattr(app, "group_name", "") or ""
            app_k8s_name = getattr(app, "k8s_app", "") or ""
            if query and query not in app_name.lower() and query not in app_k8s_name.lower():
                continue
            items.append(self._serialize_app(app))

        return self._paginate_data(items, page, page_size)

    def query_components(self, user, arguments):
        enterprise_id = self._require_string(arguments, "enterprise_id")
        app_id = self._require_int(arguments, "app_id")
        self._ensure_enterprise_access(user, enterprise_id)

        app, tenant = self._get_app_context(app_id)
        self._ensure_app_in_enterprise(app, tenant, enterprise_id)
        self._ensure_team_access(user, tenant)

        page, page_size = self._parse_pagination(arguments)
        query = (arguments.get("query") or "").strip().lower()

        service_relations = group_service_relation_repo.get_services_by_group(app_id)
        if hasattr(service_relations, "values_list"):
            service_ids = list(service_relations.values_list("service_id", flat=True))
        else:
            service_ids = [relation.service_id for relation in service_relations]
        services = service_repo.get_services_by_service_ids(service_ids)

        items = []
        for service in services:
            service_cname = getattr(service, "service_cname", "") or ""
            service_alias = getattr(service, "service_alias", "") or ""
            service_id = getattr(service, "service_id", "") or ""
            if query and (
                query not in service_cname.lower()
                and query not in service_alias.lower()
                and query != service_id.lower()
            ):
                continue
            items.append(self._serialize_component(service, app, tenant))

        return self._paginate_data(items, page, page_size)

    def delete_app(self, user, arguments):
        app_id = self._require_int(arguments, "app_id")
        confirm = bool(arguments.get("confirm", False))
        confirmation_token = arguments.get("confirmation_token")

        app, tenant = self._get_app_context(app_id)
        enterprise_id = arguments.get("enterprise_id") or tenant.enterprise_id
        team_name = arguments.get("team_name")
        region_name = arguments.get("region_name")

        self._ensure_enterprise_access(user, enterprise_id)
        self._ensure_app_in_enterprise(app, tenant, enterprise_id)
        self._ensure_team_access(user, tenant)

        if team_name and team_name != tenant.tenant_name:
            raise ServiceHandleException(msg="team mismatch", msg_show="团队信息不匹配", status_code=400)
        if region_name and region_name != app.region_name:
            raise ServiceHandleException(msg="region mismatch", msg_show="集群信息不匹配", status_code=400)

        component_count = group_service_relation_repo.count_service_by_app_id(app.ID)

        if not confirm:
            payload = {
                "action": "delete_app",
                "user_id": user.user_id,
                "app_id": app_id,
                "team_name": tenant.tenant_name,
                "region_name": app.region_name,
                "enterprise_id": tenant.enterprise_id,
            }
            token = signing.dumps(payload, salt=self.CONFIRM_SALT)
            return {
                "requires_confirmation": True,
                "confirmation_token": token,
                "warning": "This operation is destructive and cannot be undone.",
                "warning_cn": "该操作属于高危删除操作，删除后不可恢复，请前端二次确认。",
                "app": {
                    "app_id": app.ID,
                    "app_name": app.group_name,
                    "team_name": tenant.tenant_name,
                    "region_name": app.region_name,
                    "component_count": component_count,
                }
            }

        if not confirmation_token:
            raise ServiceHandleException(msg="confirmation token required", msg_show="缺少确认令牌", status_code=400)

        try:
            token_payload = signing.loads(
                confirmation_token, salt=self.CONFIRM_SALT, max_age=self.CONFIRM_MAX_AGE_SECONDS
            )
        except signing.SignatureExpired:
            raise ServiceHandleException(msg="confirmation token expired", msg_show="确认令牌已过期，请重新确认", status_code=400)
        except signing.BadSignature:
            raise ServiceHandleException(msg="invalid confirmation token", msg_show="确认令牌无效", status_code=400)

        if token_payload.get("action") != "delete_app":
            raise ServiceHandleException(msg="invalid action", msg_show="确认动作无效", status_code=400)
        if token_payload.get("user_id") != user.user_id:
            raise ServiceHandleException(
                msg="token user mismatch",
                msg_show="没有权限执行该操作：确认令牌与当前用户不匹配",
                status_code=403,
            )
        if int(token_payload.get("app_id", 0)) != app_id:
            raise ServiceHandleException(msg="token app mismatch", msg_show="确认令牌与目标应用不匹配", status_code=400)

        group_service.delete_app(tenant, app.region_name, app)

        return {
            "requires_confirmation": False,
            "deleted": True,
            "app": {
                "app_id": app.ID,
                "app_name": app.group_name,
                "team_name": tenant.tenant_name,
                "region_name": app.region_name,
            }
        }

    def _get_user_enterprises(self, user):
        try:
            enterprises = enterprise_repo.get_enterprises_by_user_id(user.user_id)
        except ExterpriseNotExistError:
            enterprises = []
        return list(enterprises) if enterprises else []

    def _get_region_context(self, user, region_id, check_status=False):
        region = region_services.get_enterprise_region(
            getattr(user, "enterprise_id", None), region_id, check_status="yes" if check_status else "no"
        )
        if not region:
            raise ServiceHandleException(msg="region not found", msg_show="集群不存在", status_code=404)
        return region

    def _get_region_model(self, user, region_id):
        region = region_services.get_region_by_region_id(region_id)
        if not region:
            raise ServiceHandleException(msg="region not found", msg_show="集群不存在", status_code=404)
        if getattr(region, "enterprise_id", None) != getattr(user, "enterprise_id", None):
            self._raise_permission_denied("无该企业集群访问权限")
        return region

    def _get_region_by_name_context(self, user, region_name):
        region = region_services.get_enterprise_region_by_region_name(getattr(user, "enterprise_id", None), region_name)
        if not region:
            raise ServiceHandleException(msg="region not found", msg_show="集群不存在", status_code=404)
        return region

    def _get_team_context(self, user, team_name):
        team = team_services.get_enterprise_tenant_by_tenant_name(getattr(user, "enterprise_id", None), team_name)
        if not team:
            raise ServiceHandleException(msg="team not found", msg_show="团队不存在", status_code=404)
        self._ensure_team_access(user, team)
        return team

    def _get_team_app_context(self, user, team_name, region_name, app_id):
        team = self._get_team_context(user, team_name)
        self._get_region_by_name_context(user, region_name)
        app = group_service.get_app_by_id(team, region_name, app_id)
        if not app:
            raise ServiceHandleException(msg="app not found", msg_show="应用不存在", status_code=404)
        return team, app

    def _get_team_app_service_context(self, user, team_name, region_name, app_id, service_id):
        team, app = self._get_team_app_context(user, team_name, region_name, app_id)
        service = service_repo.get_service_by_service_id(service_id)
        if not service:
            raise ServiceHandleException(msg="service not found", msg_show="组件不存在", status_code=404)
        if service.tenant_id != team.tenant_id or service.service_region != region_name:
            self._raise_permission_denied("无该组件访问权限")
        app_service_ids = self._get_app_service_ids(app)
        if service.service_id not in app_service_ids:
            raise ServiceHandleException(msg="service not found", msg_show="组件不属于该应用", status_code=404)
        return team, app, service

    def _get_service_in_team_app(self, team, app, service_id):
        service = service_repo.get_service_by_service_id(service_id)
        if not service:
            raise ServiceHandleException(msg="service not found", msg_show="组件不存在", status_code=404)
        if service.tenant_id != team.tenant_id or service.service_region != app.region_name:
            self._raise_permission_denied("无该组件访问权限")
        app_service_ids = self._get_app_service_ids(app)
        if service.service_id not in app_service_ids:
            raise ServiceHandleException(msg="service not found", msg_show="组件不属于该应用", status_code=404)
        return service

    def _is_enterprise_admin(self, user):
        if user is None:
            return False
        if getattr(user, "is_enterprise_admin", None) is not None:
            return bool(getattr(user, "is_enterprise_admin"))
        enterprise_id = getattr(user, "enterprise_id", None)
        user_id = getattr(user, "user_id", None)
        if not enterprise_id or not user_id:
            return False
        return enterprise_user_perm_repo.is_admin(enterprise_id, user_id)

    def _ensure_enterprise_admin(self, user):
        if not self._is_enterprise_admin(user):
            self._raise_permission_denied("当前用户不是企业管理员")

    def _ensure_enterprise_access(self, user, enterprise_id):
        if getattr(user, "enterprise_id", None) == enterprise_id:
            return

        user_enterprises = self._get_user_enterprises(user)
        available_ids = set([ent.enterprise_id for ent in user_enterprises])
        if user.enterprise_id:
            available_ids.add(user.enterprise_id)

        if enterprise_id not in available_ids:
            self._raise_permission_denied("无该企业访问权限")

    def _ensure_team_access(self, user, tenant):
        if user.user_id == tenant.creater:
            return

        if enterprise_user_perm_repo.is_admin(tenant.enterprise_id, user.user_id):
            return

        user_team = team_repo.get_user_tenant_by_name(user.user_id, tenant.tenant_name)
        if user_team is None:
            self._raise_permission_denied("无该团队访问权限")

    @staticmethod
    def _raise_permission_denied(detail):
        raise ServiceHandleException(
            msg="permission denied",
            msg_show="没有权限执行该操作：{}".format(detail),
            status_code=403,
        )

    @staticmethod
    def _ensure_app_in_enterprise(app, tenant, enterprise_id):
        if tenant.enterprise_id != enterprise_id:
            raise ServiceHandleException(msg="app not in enterprise", msg_show="应用不属于该企业", status_code=400)
        if app.tenant_id != tenant.tenant_id:
            raise ServiceHandleException(msg="tenant mismatch", msg_show="应用与团队信息不匹配", status_code=400)

    @staticmethod
    def _get_app_context(app_id):
        app = group_repo.get_group_by_id(app_id)
        if not app:
            raise ServiceHandleException(msg="app not found", msg_show="应用不存在", status_code=404)
        try:
            tenant = team_repo.get_team_by_team_id(app.tenant_id)
        except TenantNotExistError:
            raise ServiceHandleException(msg="team not found", msg_show="团队不存在", status_code=404)
        return app, tenant

    @staticmethod
    def _require_string(arguments, field):
        value = arguments.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ServiceHandleException(msg="invalid {}".format(field), msg_show="参数{}无效".format(field), status_code=400)
        return value.strip()

    @staticmethod
    def _require_int(arguments, field):
        value = arguments.get(field)
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            raise ServiceHandleException(msg="invalid {}".format(field), msg_show="参数{}无效".format(field), status_code=400)
        if ivalue <= 0:
            raise ServiceHandleException(msg="invalid {}".format(field), msg_show="参数{}无效".format(field), status_code=400)
        return ivalue

    @staticmethod
    def _require_command(arguments):
        value = arguments.get("command")
        if not isinstance(value, list) or not value:
            raise ServiceHandleException(
                msg="invalid command",
                msg_show="参数command无效，必须是非空字符串数组，如 [\"cat\", \"/app/config.yml\"]",
                status_code=400)
        command = []
        for item in value:
            if not isinstance(item, str) or item == "":
                raise ServiceHandleException(
                    msg="invalid command",
                    msg_show="参数command无效，数组元素必须是非空字符串",
                    status_code=400)
            command.append(item)
        return command

    @staticmethod
    def _parse_optional_positive_int(value, field, allow_zero=False):
        if value in (None, ""):
            return None
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            raise ServiceHandleException(msg="invalid {}".format(field), msg_show="参数{}无效".format(field), status_code=400)
        floor = 0 if allow_zero else 1
        if ivalue < floor:
            raise ServiceHandleException(msg="invalid {}".format(field), msg_show="参数{}无效".format(field), status_code=400)
        return ivalue

    def _parse_pagination(self, arguments):
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 20)
        try:
            page = int(page)
            page_size = int(page_size)
        except (TypeError, ValueError):
            raise ServiceHandleException(msg="invalid pagination", msg_show="分页参数无效", status_code=400)

        if page <= 0 or page_size <= 0:
            raise ServiceHandleException(msg="invalid pagination", msg_show="分页参数无效", status_code=400)
        if page_size > self.MAX_PAGE_SIZE:
            page_size = self.MAX_PAGE_SIZE

        return page, page_size

    @staticmethod
    def _parse_bool_with_default(value, default=False):
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value = value.strip().lower()
            if value in ("true", "1", "yes", "y", "on"):
                return True
            if value in ("false", "0", "no", "n", "off"):
                return False
        raise ServiceHandleException(msg="invalid boolean", msg_show="布尔参数无效", status_code=400)

    @classmethod
    def _normalize_bool_query_value(cls, value):
        if value is None or value == "":
            return None
        return "true" if cls._parse_bool_with_default(value, False) else "false"

    def _normalize_app_model_source(self, source):
        source = (source or "local").strip().lower()
        normalized = self.APP_MODEL_SOURCE_ALIASES.get(source)
        if normalized:
            return normalized
        raise ServiceHandleException(
            msg="invalid source",
            msg_show="source 无效，可选值为: local, cloud",
            status_code=400,
        )

    @staticmethod
    def _resolve_upsert_envs(arguments):
        envs = arguments.get("envs")
        if envs:
            return envs
        attr_name = arguments.get("attr_name") or arguments.get("name")
        attr_value = arguments.get("attr_value")
        if attr_name and attr_value is not None:
            return [{
                "name": arguments.get("name") or attr_name,
                "attr_name": attr_name,
                "value": attr_value,
                "scope": arguments.get("scope", "inner"),
                "is_change": arguments.get("is_change", True),
                "note": arguments.get("name", "") or "",
            }]
        return envs

    def _build_create_app_error_details(self, exc, app_name, k8s_app):
        msg = getattr(exc, "msg", "") or ""
        msg_show = getattr(exc, "msg_show", "") or ""
        error_code = getattr(exc, "error_code", None)
        if msg == "app_name illegal":
            if "最多支持128个字符" in msg_show:
                return {
                    "field": "app_name",
                    "reason": "too_long",
                    "provided_value": app_name,
                    "max_length": self.DISPLAY_APP_NAME_MAX_LENGTH,
                    "suggestion": "请将应用名称缩短到128个字符以内。",
                    "retryable": False,
                }
            return {
                "field": "app_name",
                "reason": "pattern_mismatch",
                "provided_value": app_name,
                "expected_pattern": self.DISPLAY_APP_NAME_PATTERN,
                "max_length": self.DISPLAY_APP_NAME_MAX_LENGTH,
                "examples": ["demo-app", "演示应用", "demo_app.v1"],
                "suggestion": "请使用中文、英文、数字、下划线、中划线或点，不要包含空格或其他特殊字符。",
                "retryable": False,
            }
        if error_code in (11011, 21003) or "k8s app" in msg.lower() or "应用英文名已存在" in msg_show:
            return {
                "field": "k8s_app",
                "reason": "duplicate",
                "expected_pattern": self.K8S_APP_NAME_PATTERN,
                "provided_value": k8s_app or None,
                "suggestion": (
                    "默认建议不传 k8s_app；若必须指定，请换一个在同团队同集群下唯一的英文名。"
                ),
                "retryable": False,
            }
        if "应用英文名称只能由小写字母" in msg_show or "集群内应用名称只能由小写字母" in msg_show:
            return {
                "field": "k8s_app",
                "reason": "pattern_mismatch",
                "expected_pattern": self.K8S_APP_NAME_PATTERN,
                "provided_value": k8s_app or None,
                "examples": ["demo-app", "wordpress-01"],
                "suggestion": "若需要指定 k8s_app，请使用小写字母开头、仅包含小写字母、数字和连字符的唯一名称。",
                "retryable": False,
            }
        if "应用名称已存在" in msg_show:
            return {
                "field": "app_name",
                "reason": "duplicate",
                "provided_value": app_name,
                "suggestion": "请更换一个在当前团队和集群下未使用的应用名称。",
                "retryable": False,
            }
        return None

    def _create_app_with_mcp_error_details(self, team, region_name, app_name, app_note, username, k8s_app=""):
        try:
            return group_service.create_app(
                team,
                region_name,
                app_name,
                app_note,
                username,
                k8s_app=k8s_app if k8s_app else "",
            )
        except ServiceHandleException as exc:
            raise ServiceHandleException(
                msg=exc.msg,
                msg_show=exc.msg_show,
                status_code=exc.status_code,
                error_code=exc.error_code,
                details=self._build_create_app_error_details(exc, app_name, k8s_app),
            )

    @staticmethod
    def _parse_int_with_default(value, default):
        if value is None or value == "":
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ServiceHandleException(msg="invalid integer", msg_show="整型参数无效", status_code=400)

    @staticmethod
    def _normalize_source_git_url(git_url, subdirectories=None):
        git_url = (git_url or "").strip()
        subdirectories = (subdirectories or "").strip()
        if not subdirectories or "dir=" in git_url:
            return git_url
        separator = "&" if "?" in git_url else "?"
        return "{}{}dir={}".format(git_url, separator, subdirectories)

    @staticmethod
    def _normalize_source_code_version(code_version, version_type=None):
        code_version = (code_version or "master").strip()
        if (version_type or "").strip() == "tag" and not code_version.startswith("tag:"):
            return "tag:{}".format(code_version)
        return code_version

    def _normalize_port_action(self, action):
        action = (action or "").strip().lower()
        normalized = self.PORT_ACTION_ALIASES.get(action)
        if normalized:
            return normalized
        raise ServiceHandleException(
            msg="invalid port action",
            msg_show="端口 action 无效，可选值为: {}".format(", ".join(self.PORT_ACTION_ENUM)),
            status_code=400,
        )

    @staticmethod
    def _normalize_component_operation(operation, aliases, allowed, label):
        operation = (operation or "").strip().lower()
        normalized = aliases.get(operation)
        if normalized and normalized in allowed:
            return normalized
        raise ServiceHandleException(
            msg="invalid operation",
            msg_show="{} operation 无效，可选值为: {}".format(label, ", ".join(allowed)),
            status_code=400,
        )

    @classmethod
    def _port_alias_schema(cls):
        return {
            "type": "string",
            "pattern": cls.PORT_ALIAS_PATTERN,
            "description": cls.PORT_ALIAS_DESCRIPTION,
        }

    @classmethod
    def _k8s_service_name_schema(cls):
        return {
            "type": "string",
            "pattern": cls.K8S_SERVICE_NAME_PATTERN,
            "maxLength": 63,
            "description": cls.K8S_SERVICE_NAME_DESCRIPTION,
        }

    def _build_port_tool_error_details(self, msg_show):
        if msg_show == "端口别名不合法":
            return {
                "field": "port_alias",
                "reason": "pattern_mismatch",
                "expected_pattern": self.PORT_ALIAS_PATTERN,
                "examples": ["WEB", "P80", "METRICS_8080"],
                "suggestion": (
                    "新增端口时可省略 port_alias，由系统自动生成；"
                    "若手动填写，请使用全大写别名。"
                ),
                "retryable": False,
            }
        if msg_show == "端口别名不能为空":
            return {
                "field": "port_alias",
                "reason": "required",
                "expected_pattern": self.PORT_ALIAS_PATTERN,
                "suggestion": (
                    "新增端口时可省略 port_alias；"
                    "修改别名时必须提供符合规则的全大写别名。"
                ),
                "retryable": False,
            }
        if msg_show == "内部域名格式不正确":
            return {
                "field": "k8s_service_name",
                "reason": "pattern_mismatch",
                "expected_pattern": self.K8S_SERVICE_NAME_PATTERN,
                "max_length": 63,
                "examples": ["web", "api-80"],
                "suggestion": "请使用小写字母开头、仅包含小写字母、数字和连字符的内部域名。",
                "retryable": False,
            }
        if msg_show == "端口必须为1到65535的整数":
            return {
                "field": "port",
                "reason": "out_of_range",
                "minimum": 1,
                "maximum": 65535,
                "retryable": False,
            }
        return None

    def _raise_port_tool_error(self, msg, msg_show, status_code):
        raise ServiceHandleException(
            msg=msg,
            msg_show=msg_show,
            status_code=status_code,
            details=self._build_port_tool_error_details(msg_show),
        )

    def _normalize_env_scope(self, scope):
        scope = (scope or "inner").strip().lower()
        normalized = self.ENV_SCOPE_ALIASES.get(scope)
        if normalized:
            return normalized
        raise ServiceHandleException(
            msg="params error",
            msg_show="scope范围只能是inner（也支持 local/self/runtime 别名）",
            status_code=400,
        )

    def _normalize_envs_for_upsert(self, envs):
        normalized_items = []
        for env in envs:
            if not isinstance(env, dict):
                raise ServiceHandleException(msg="invalid env", msg_show="envs中的单项必须是对象", status_code=400)
            env_name = env.get("name") or env.get("attr_name")
            if not env_name:
                raise ServiceHandleException(msg="invalid env", msg_show="环境变量缺少 name/attr_name", status_code=400)
            if "value" not in env and "attr_value" not in env:
                raise ServiceHandleException(msg="invalid env", msg_show="环境变量缺少 value/attr_value", status_code=400)
            normalized_items.append({
                "note": env.get("note", env.get("name_desc", env.get("name", ""))) or "",
                "name": env_name,
                "value": env.get("value", env.get("attr_value")),
                "is_change": bool(env.get("is_change", True)),
                "scope": self._normalize_env_scope(env.get("scope")),
            })
        return normalized_items

    def _lookup_env_or_raise(self, team, service, env_id):
        try:
            return env_var_repo.get_env_by_ids_and_env_id(team.tenant_id, service.service_id, env_id)
        except ObjectDoesNotExist:
            raise ServiceHandleException(
                msg="env not found",
                msg_show="环境变量不存在（env_id={}），请先用 operation=summary 重新获取最新 env_id".format(env_id),
                status_code=404,
            )

    def _ensure_inner_env(self, team, service, env_id):
        env = self._lookup_env_or_raise(team, service, env_id)
        if getattr(env, "scope", "") != "inner":
            raise ServiceHandleException(
                msg="invalid env scope",
                msg_show="该工具只操作自定义环境变量（inner），不能直接修改组件连接信息",
                status_code=400,
            )
        return env

    def _ensure_outer_env(self, team, service, env_id):
        env = self._lookup_env_or_raise(team, service, env_id)
        if getattr(env, "scope", "") not in ("outer", "both"):
            raise ServiceHandleException(
                msg="invalid env scope",
                msg_show="该工具只操作组件连接信息（outer），不能直接修改自定义环境变量",
                status_code=400,
            )
        return env

    def _upsert_inner_envs(self, team, service, envs, user_name):
        inner_envs = env_var_service.get_service_inner_env(service)
        env_attr_names = {env.attr_name: env for env in inner_envs}
        for env in envs:
            if env["name"] in env_attr_names:
                code, msg, _ = env_var_service.update_env_by_env_id(
                    team, service, str(env_attr_names[env["name"]].ID), env["note"], env["value"], user_name
                )
                if code != 200:
                    raise ServiceHandleException(status_code=code, msg="update or create envs error", msg_show=msg)
            else:
                code, msg, _ = env_var_service.add_service_env_var(
                    team, service, 0, env["note"], env["name"], env["value"], env["is_change"], "inner", user_name
                )
                if code != 200:
                    raise ServiceHandleException(status_code=code, msg="update or create envs error", msg_show=msg)
        total_envs = env_var_service.get_service_inner_env(service)
        dt = []
        for env in total_envs:
            dt.append({
                "note": env.name,
                "name": env.attr_name,
                "value": env.attr_value,
                "is_change": env.is_change,
                "scope": env.scope,
            })
        return {"envs": dt}

    def _get_component_resource(self, team, service):
        try:
            body = region_api.get_service_resources(team.tenant_name, service.service_region, {
                "service_ids": [service.service_id]
            })
            bean = body.get("bean", {})
            result = bean.get(service.service_id)
            return {
                "memory": result.get("memory", 0) if result else 0,
                "disk": result.get("disk", 0) if result else 0,
                "cpu": result.get("cpu", 0) if result else 0,
            }
        except Exception:
            return {"memory": 0, "disk": 0, "cpu": 0}

    @staticmethod
    def service_requires_region_sync(service):
        return getattr(service, "create_status", "") == "complete"

    @staticmethod
    def _ensure_volume_mode(mode):
        mode = int(mode)
        if mode < 0 or mode > 777:
            raise ServiceHandleException(msg="invalid mode", msg_show="权限必须是在0和777之间的八进制数", status_code=400)
        if not str(mode).isdigit() or any(ch not in "01234567" for ch in str(mode)):
            raise ServiceHandleException(msg="invalid mode", msg_show="权限必须是在0和777之间的八进制数", status_code=400)
        return mode

    def _build_autoscaler_payload(self, service, arguments):
        metrics = arguments.get("metrics")
        if not isinstance(metrics, list) or not metrics:
            raise ServiceHandleException(msg="invalid metrics", msg_show="参数metrics无效", status_code=400)
        xpa_type = arguments.get("xpa_type", "hpa")
        if xpa_type not in ("hpa",):
            raise ServiceHandleException(msg="invalid xpa_type", msg_show="参数xpa_type无效", status_code=400)
        min_replicas = self._require_int(arguments, "min_replicas")
        max_replicas = self._require_int(arguments, "max_replicas")
        if min_replicas > 65535:
            raise ServiceHandleException(msg="invalid min_replicas", msg_show="参数min_replicas无效", status_code=400)
        if max_replicas > 65535 or max_replicas < min_replicas:
            raise ServiceHandleException(msg="invalid max_replicas", msg_show="参数max_replicas无效", status_code=400)

        normalized_metrics = []
        for metric in metrics:
            if not isinstance(metric, dict):
                raise ServiceHandleException(msg="invalid metrics", msg_show="参数metrics无效", status_code=400)
            metric_type = metric.get("metric_type")
            metric_name = metric.get("metric_name")
            metric_target_type = metric.get("metric_target_type")
            try:
                metric_target_value = int(metric.get("metric_target_value"))
            except (TypeError, ValueError):
                raise ServiceHandleException(msg="invalid metrics", msg_show="参数metrics无效", status_code=400)
            if metric_type not in ("resource_metrics",):
                raise ServiceHandleException(msg="invalid metrics", msg_show="参数metrics无效", status_code=400)
            if metric_name not in ("cpu", "memory"):
                raise ServiceHandleException(msg="invalid metrics", msg_show="参数metrics无效", status_code=400)
            if metric_target_type not in ("utilization", "average_value"):
                raise ServiceHandleException(msg="invalid metrics", msg_show="参数metrics无效", status_code=400)
            if metric_target_value < 0 or metric_target_value > 65535:
                raise ServiceHandleException(msg="invalid metrics", msg_show="参数metrics无效", status_code=400)
            normalized_metrics.append({
                "metric_type": metric_type,
                "metric_name": metric_name,
                "metric_target_type": metric_target_type,
                "metric_target_value": metric_target_value,
            })
        return {
            "service_id": service.service_id,
            "xpa_type": xpa_type,
            "enable": self._parse_bool_with_default(arguments.get("enable"), True),
            "min_replicas": min_replicas,
            "max_replicas": max_replicas,
            "metrics": normalized_metrics,
        }

    def _build_probe_payload(self, arguments):
        payload = {
            "mode": self._require_string(arguments, "mode"),
            "port": self._require_int(arguments, "port"),
        }
        optional_keys = (
            "scheme", "path", "cmd", "http_header", "initial_delay_second", "period_second",
            "timeout_second", "failure_threshold", "success_threshold", "is_used"
        )
        for key in optional_keys:
            if key in arguments:
                payload[key] = arguments.get(key)
        return payload

    def _serialize_dependency_items(self, services):
        items = [self._serialize_model_item(service) for service in services]
        service_ids = [item.get("service_id") for item in items if item.get("service_id")]
        group_map = group_service.get_services_group_name(service_ids) if service_ids else {}
        for item in items:
            service_id = item.get("service_id")
            if service_id and service_id in group_map:
                item["group_name"] = group_map[service_id].get("group_name")
                item["group_id"] = group_map[service_id].get("group_id")
            service_obj = service_repo.get_service_by_service_id(service_id) if service_id else None
            if service_obj:
                ports = port_service.get_service_ports(service_obj)
                item["ports_list"] = [port.container_port for port in ports]
        return {"items": items, "total": len(items)}

    def _read_component_pod_logs(self, team, region_name, service_alias, pod_name, lines, container_name="", previous=False):
        # read_timeout governs how long urllib3 waits for the next chunk
        # (or the initial HTTP response). 3s was tight enough that
        # rbd-api regularly took longer than that to send the response
        # headers, surfacing as 500 -> ReadTimeoutError to MCP clients.
        # Bumping to 30s keeps streaming responsive for healthy pods
        # while tolerating a slow-to-respond region service.
        resp = region_api.get_component_pod_log(
            team.tenant_name, region_name, service_alias, pod_name, lines, container_name,
            read_timeout=30, follow=False, previous=previous
        )
        log_list = []
        buffer = ""
        try:
            for chunk in resp.stream(1024):
                text = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
                buffer += text.replace("\r\n", "\n")
                parts = buffer.split("\n")
                buffer = parts.pop()
                for raw_line in parts:
                    parsed_line = self._parse_component_log_line(raw_line)
                    if parsed_line is None:
                        continue
                    log_list.append(parsed_line)
                    if len(log_list) >= lines:
                        return log_list[:lines]
        except Exception:
            if log_list:
                return log_list[:lines]
            raise
        finally:
            try:
                resp.close()
            except Exception:
                pass
            try:
                resp.release_conn()
            except Exception:
                pass
        parsed_line = self._parse_component_log_line(buffer)
        if parsed_line is not None:
            log_list.append(parsed_line)
        return log_list[:lines]

    @staticmethod
    def _parse_component_log_line(raw_line):
        if raw_line is None:
            return None
        line = raw_line.strip()
        if not line:
            return None
        if line.startswith(("event:", "id:", "retry:", ":")):
            return None
        if line.startswith("data:"):
            message = line[5:].lstrip()
            return message or None
        return line

    @staticmethod
    def _extract_pod_container_names(container_data):
        if not container_data:
            return []
        if isinstance(container_data, list):
            result = []
            for item in container_data:
                if isinstance(item, dict) and item.get("container_name"):
                    result.append(item.get("container_name"))
            return result
        if isinstance(container_data, dict):
            return [name for name in container_data.keys() if name and name != "POD"]
        return []

    @staticmethod
    def _extract_region_pod_detail(payload):
        if not isinstance(payload, dict):
            return payload
        bean = payload.get("bean")
        if isinstance(bean, dict):
            return bean
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("bean"), dict):
            return data.get("bean")
        return payload

    def _extract_component_pods(self, pods_data):
        if not isinstance(pods_data, dict):
            return []
        pod_groups = {}
        if isinstance(pods_data.get("bean"), dict):
            pod_groups = pods_data.get("bean") or {}
        elif isinstance(pods_data.get("list"), dict):
            pod_groups = pods_data.get("list") or {}
        pods = []
        for group_name in ("new_pods", "old_pods"):
            group_items = pod_groups.get(group_name) or []
            if not isinstance(group_items, list):
                continue
            for pod in group_items:
                if not isinstance(pod, dict):
                    continue
                pod_copy = dict(pod)
                pod_copy["_group"] = group_name
                pod_copy["_container_names"] = self._extract_pod_container_names(pod.get("container"))
                pods.append(pod_copy)
        # Backward compatibility for legacy tests or alternate region responses.
        bean_items = pods_data.get("bean")
        if not pods and isinstance(bean_items, list):
            for pod in bean_items:
                if not isinstance(pod, dict):
                    continue
                pod_copy = dict(pod)
                pod_copy["_group"] = "new_pods"
                pod_copy["_container_names"] = self._extract_pod_container_names(pod.get("container"))
                pods.append(pod_copy)
        return pods

    def _infer_component_log_target(self, team, region_name, service):
        data = region_api.get_service_pods(region_name, team.tenant_name, service.service_alias, team.enterprise_id)
        pods = self._extract_component_pods(data)
        if not pods:
            return None, None
        # Prefer running pods from the current rollout, then any remaining pod.
        pod = None
        for item in pods:
            if item.get("pod_status") == "RUNNING" and item.get("_group") == "new_pods":
                pod = item
                break
        if not pod:
            for item in pods:
                if item.get("pod_status") == "RUNNING":
                    pod = item
                    break
        if not pod:
            pod = pods[0]
        pod_name = pod.get("pod_name")
        containers = pod.get("_container_names") or []
        preferred = getattr(service, "k8s_component_name", "") or getattr(service, "service_alias", "")
        if preferred and preferred in containers:
            return pod_name, preferred
        for container_name in containers:
            return pod_name, container_name
        return pod_name, None

    @staticmethod
    def _get_username(user):
        if hasattr(user, "get_username") and callable(user.get_username):
            return user.get_username()
        return getattr(user, "nick_name", "")

    @staticmethod
    def _serialize_datetime(value):
        if not value:
            return None
        try:
            return value.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return str(value)

    @staticmethod
    def _value(data, key, default=None):
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    def _serialize_enterprise(self, enterprise):
        return {
            "enterprise_id": enterprise.enterprise_id,
            "enterprise_name": enterprise.enterprise_name,
            "enterprise_alias": enterprise.enterprise_alias,
            "is_active": enterprise.is_active,
            "create_time": self._serialize_datetime(getattr(enterprise, "create_time", None)),
        }

    def _serialize_region(self, region):
        return {
            "region_id": self._value(region, "region_id"),
            "enterprise_id": self._value(region, "enterprise_id"),
            "enterprise_alias": self._value(region, "enterprise_alias"),
            "region_name": self._value(region, "region_name"),
            "region_alias": self._value(region, "region_alias"),
            "region_type": self._value(region, "region_type", []),
            "url": self._value(region, "url"),
            "token": self._value(region, "token"),
            "wsurl": self._value(region, "wsurl"),
            "httpdomain": self._value(region, "httpdomain"),
            "tcpdomain": self._value(region, "tcpdomain"),
            "scope": self._value(region, "scope"),
            "ssl_ca_cert": self._value(region, "ssl_ca_cert"),
            "cert_file": self._value(region, "cert_file"),
            "key_file": self._value(region, "key_file"),
            "status": self._value(region, "status"),
            "desc": self._value(region, "desc"),
            "provider": self._value(region, "provider"),
            "provider_cluster_id": self._value(region, "provider_cluster_id"),
            "total_memory": self._value(region, "total_memory"),
            "used_memory": self._value(region, "used_memory"),
            "total_cpu": self._value(region, "total_cpu"),
            "used_cpu": self._value(region, "used_cpu"),
            "total_disk": self._value(region, "total_disk"),
            "used_disk": self._value(region, "used_disk"),
            "rbd_version": self._value(region, "rbd_version"),
            "health_status": self._value(region, "health_status"),
            "resource_proxy_status": self._value(region, "resource_proxy_status"),
            "k8s_version": self._value(region, "k8s_version"),
            "all_nodes": self._value(region, "all_nodes"),
            "pods": self._value(region, "pods"),
            "run_pod_number": self._value(region, "run_pod_number"),
            "node_ready": self._value(region, "node_ready"),
            "services_status": self._value(region, "services_status"),
            "arch": self._value(region, "arch"),
            "create_time": self._serialize_datetime(self._value(region, "create_time")),
        }

    def _serialize_app(self, app):
        team_name = None
        team_alias = None
        try:
            team = team_services.get_team_by_team_id(app.tenant_id)
            team_name = team.tenant_name
            team_alias = team.tenant_alias
        except Exception:
            logger.warning("failed to resolve team for app %s", app.ID)

        return {
            "app_id": app.ID,
            "app_name": app.group_name,
            "app_type": app.app_type,
            "k8s_app": app.k8s_app,
            "team_id": app.tenant_id,
            "team_name": team_name,
            "team_alias": team_alias,
            "region_name": app.region_name,
            "note": app.note,
            "create_time": self._serialize_datetime(getattr(app, "create_time", None)),
            "update_time": self._serialize_datetime(getattr(app, "update_time", None)),
        }

    def _serialize_component(self, service, app, tenant):
        return {
            "service_id": service.service_id,
            "service_alias": service.service_alias,
            "service_cname": service.service_cname,
            "service_region": getattr(service, "service_region", ""),
            "service_source": getattr(service, "service_source", ""),
            "create_status": getattr(service, "create_status", ""),
            "app_id": app.ID,
            "app_name": app.group_name,
            "team_id": tenant.tenant_id,
            "team_name": tenant.tenant_name,
            "enterprise_id": tenant.enterprise_id,
            "create_time": self._serialize_datetime(getattr(service, "create_time", None)),
            "update_time": self._serialize_datetime(getattr(service, "update_time", None)),
        }

    def _get_app_service_ids(self, app):
        relations = group_service_relation_repo.get_services_by_group(app.ID)
        return [relation.service_id for relation in relations]

    def _get_app_services_and_status(self, team, app):
        services = group_service.get_group_services(app.ID)
        service_ids = [service.service_id for service in services]
        status_list = []
        if service_ids:
            status_list = base_service.status_multi_service(
                region=app.region_name,
                tenant_name=team.tenant_name,
                service_ids=service_ids,
                enterprise_id=team.enterprise_id,
            )
        status_map = {}
        for status in status_list or []:
            status_map[status["service_id"]] = status["status"]
        result = []
        for service in services:
            data = service.to_dict()
            data["status"] = status_map.get(service.service_id, "")
            result.append(data)
        return result

    @staticmethod
    def _get_services_cpu_memory(services):
        used_memory = 0
        used_cpu = 0
        for service in services:
            memory = service.get("min_memory", 0) or 0
            used_memory += memory
            used_cpu += memory / 128 * 30
        return used_cpu, used_memory

    @staticmethod
    def _get_running_service_count(services):
        count = 0
        for service in services:
            if service.get("status") == "running":
                count += 1
        return count

    @staticmethod
    def _get_app_status(running_count, total_count):
        if running_count <= 0:
            return "closed"
        if running_count < total_count:
            return "part_running"
        return "running"

    def _get_app_monitor_services(self, app, is_outer):
        services_relation = group_service_relation_repo.get_services_by_group(app.ID)
        if hasattr(services_relation, "values_list"):
            service_ids = list(services_relation.values_list("service_id", flat=True))
        else:
            service_ids = [relation.service_id for relation in services_relation]
        if not service_ids:
            return []
        services = service_repo.get_services_by_service_ids(service_ids)
        if hasattr(services, "exclude"):
            services = services.exclude(service_source="third_party")
        else:
            services = [service for service in services if getattr(service, "service_source", None) != "third_party"]
        result = []
        for service in services:
            has_plugin = False
            service_abled_plugins = app_plugin_service.get_service_abled_plugin(service)
            for plugin in service_abled_plugins:
                if plugin.category == PluginCategoryConstants.PERFORMANCE_ANALYSIS:
                    has_plugin = True
            if not has_plugin:
                continue
            if is_outer:
                tenant_service_ports = port_service.get_service_ports(service)
                is_outer_service = False
                for service_port in tenant_service_ports:
                    if service_port.is_outer_service:
                        is_outer_service = True
                        break
                if not is_outer_service:
                    continue
            result.append(service)
        return result

    @staticmethod
    def _serialize_model_item(obj):
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, dict):
            return {k: MCPQueryService._serialize_model_item(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [MCPQueryService._serialize_model_item(v) for v in obj]
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return MCPQueryService._serialize_model_item(obj.to_dict())
        data = {}
        for key, value in getattr(obj, "__dict__", {}).items():
            if not key.startswith("_") and not callable(value):
                data[key] = MCPQueryService._serialize_model_item(value)
        return data

    def _serialize_app_share_record_summary(self, record, user):
        app_model_name = getattr(record, "share_app_model_name", None)
        app_model_id = getattr(record, "app_id", None)
        version_alias = getattr(record, "share_version_alias", None)
        upgrade_time = None
        store_name = getattr(record, "share_store_name", None)
        store_id = getattr(record, "share_app_market_name", None)
        scope = getattr(record, "scope", None)
        if scope != "goodrain" and not app_model_name and app_model_id:
            app = rainbond_app_repo.get_rainbond_app_by_app_id(app_model_id)
            app_model_name = app.app_name if app else app_model_name
            app_version = rainbond_app_repo.get_rainbond_app_version_by_record_id(record.ID)
            if app_version:
                upgrade_time = self._serialize_datetime(getattr(app_version, "upgrade_time", None))
                version_alias = app_version.version_alias
        if scope == "goodrain" and store_id and app_model_id and not app_model_name:
            try:
                market = app_market_service.get_app_market_by_name(
                    getattr(user, "enterprise_id", None),
                    store_id,
                    user_id=self._share_market_user_id(user),
                    raise_exception=True,
                )
                cloud_app = app_market_service.get_market_app_model(market, app_model_id, True)
                if cloud_app:
                    store_name = getattr(cloud_app, "market_name", None) or store_name
                    app_model_name = getattr(cloud_app, "app_name", None) or app_model_name
            except Exception:
                logger.exception("failed to resolve cloud app publish record %s", record.ID)
        return {
            "app_model_id": app_model_id,
            "app_model_name": app_model_name,
            "version": getattr(record, "share_version", None),
            "version_alias": version_alias,
            "scope": scope,
            "create_time": self._serialize_datetime(getattr(record, "create_time", None)),
            "upgrade_time": upgrade_time,
            "step": getattr(record, "step", None),
            "is_success": getattr(record, "is_success", False),
            "status": getattr(record, "status", None),
            "scope_target": {
                "store_name": store_name,
                "store_id": store_id,
            },
            "record_id": record.ID,
            "app_version_info": getattr(record, "share_app_version_info", ""),
        }

    def _serialize_app_share_record_detail(self, record, user):
        data = self._serialize_app_share_record_summary(record, user)
        store_version = "1.0"
        store_id = data["scope_target"]["store_id"]
        if store_id:
            try:
                market_info = app_market_service.get_app_market(
                    getattr(user, "enterprise_id", None),
                    store_id,
                    self._share_market_user_id(user),
                    "true",
                    raise_exception=True,
                )
                extend = market_info[0] if isinstance(market_info, tuple) else {}
                store_version = self._value(extend, "version", store_version)
            except Exception:
                logger.exception("failed to resolve market version for share record %s", record.ID)
        data["scope_target"]["store_version"] = store_version
        return data

    @staticmethod
    def _share_market_user_id(user):
        return getattr(user, "user_id", None) if os.getenv("USE_SAAS") else None

    @staticmethod
    def _normalize_publish_scope(scope):
        if scope in (None, "", "local"):
            return "local"
        if scope == "goodrain":
            return "goodrain"
        raise ServiceHandleException(msg="invalid scope", msg_show="scope只能是local或goodrain", status_code=400)

    @staticmethod
    def _normalize_share_event_type(event_type):
        if event_type in (None, "", "service"):
            return "service"
        if event_type == "plugin":
            return "plugin"
        raise ServiceHandleException(msg="invalid event_type", msg_show="event_type只能是service或plugin", status_code=400)

    def _get_app_share_record_context(self, team, share_id):
        share_record = share_service.get_service_share_record_by_ID(ID=share_id, team_name=team.tenant_name)
        if not share_record:
            raise ServiceHandleException(msg="share record not found", msg_show="分享流程不存在，请退出重试", status_code=404)
        return share_record

    @staticmethod
    def _build_snapshot_share_info(arguments):
        share_info = {}
        for field in ("share_service_list", "share_plugin_list", "share_k8s_resources"):
            value = arguments.get(field)
            if value is not None:
                if not isinstance(value, list):
                    raise ServiceHandleException(msg="invalid {}".format(field), msg_show="参数{}无效".format(field), status_code=400)
                share_info[field] = value
        return share_info

    def _serialize_upgrade_record_basic(self, record):
        if not record:
            return None
        data = self._serialize_model_item(record)
        snapshot_id = data.get("snapshot_id")
        data["snapshot"] = {
            "snapshot_id": snapshot_id,
            "exists": self._upgrade_snapshot_exists(snapshot_id),
        }
        return data

    def _serialize_upgrade_record_detail(self, record):
        if not record:
            return None
        data = self._serialize_model_item(record)
        service_records = data.get("service_record") or []
        data["service_record"] = [self._serialize_model_item(item) for item in service_records]
        snapshot_id = data.get("snapshot_id")
        data["snapshot"] = {
            "snapshot_id": snapshot_id,
            "exists": self._upgrade_snapshot_exists(snapshot_id),
        }
        return data

    def _upgrade_snapshot_exists(self, snapshot_id):
        if not snapshot_id:
            return False
        try:
            app_snapshot_repo.get_by_snapshot_id(snapshot_id)
            return True
        except ServiceHandleException:
            return False
        except Exception:
            logger.exception("failed to resolve app upgrade snapshot %s", snapshot_id)
            return False

    @staticmethod
    def _normalize_upgrade_record_type(record_type):
        if record_type in (None, ""):
            return None
        normalized = str(record_type).strip().lower()
        if normalized not in ("upgrade", "rollback"):
            raise ServiceHandleException(msg="invalid record_type", msg_show="record_type只能是upgrade或rollback", status_code=400)
        return normalized

    def _get_team_app_upgrade_record_context(self, user, team_name, region_name, app_id, record_id):
        team, app = self._get_team_app_context(user, team_name, region_name, app_id)
        record = upgrade_repo.get_by_record_id(record_id)
        if self._value(record, "group_id") != app.ID:
            raise ServiceHandleException(msg="record not found", msg_show="升级记录不存在", status_code=404)
        if self._value(record, "tenant_id") != team.tenant_id:
            self._raise_permission_denied("无该升级记录访问权限")
        return team, app, record

    def _serialize_service_with_gateway_rules(self, service):
        data = self._serialize_model_item(service)
        gateway_rules = getattr(service, "gateway_rules", None)
        if gateway_rules:
            data["gateway_rules"] = {
                "http": [self._serialize_model_item(rule) for rule in gateway_rules.get("http", [])],
                "tcp": [self._serialize_model_item(rule) for rule in gateway_rules.get("tcp", [])],
            }
        return data

    @staticmethod
    def _empty_page(page, page_size):
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        }

    def _paginate_data(self, items, page, page_size):
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "items": items[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def _tool_get_current_user(self):
        return {
            "name": "rainbond_get_current_user",
            "description": "Get current authenticated user information and whether the user is an enterprise administrator.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }

    def _tool_get_app_detail(self):
        return {
            "name": "rainbond_get_app_detail",
            "description": "Get application detail by team, region and app ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_create_app(self):
        return {
            "name": "rainbond_create_app",
            "description": "Create an application in the specified team and region.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_name": {
                        "type": "string",
                        "description": self.DISPLAY_APP_NAME_DESCRIPTION,
                        "pattern": self.DISPLAY_APP_NAME_PATTERN,
                        "maxLength": self.DISPLAY_APP_NAME_MAX_LENGTH,
                    },
                    "app_note": {"type": "string"},
                    "k8s_app": {
                        "type": "string",
                        "pattern": self.K8S_APP_NAME_PATTERN,
                        "description": self.K8S_APP_NAME_DESCRIPTION,
                    }
                },
                "required": ["team_name", "region_name", "app_name"]
            }
        }

    def _tool_get_component_summary(self):
        return {
            "name": "rainbond_get_component_summary",
            "description": "Get an aggregated summary of the component, including status, resources, ports, envs, build envs, storage, autoscaler rules, and recent events. Logs are excluded.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "event_limit": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_get_component_logs(self):
        return {
            "name": "rainbond_get_component_logs",
            "description": "获取组件日志。推荐优先使用 action=container 查询指定 pod/container 的容器日志；action=service 为组件普通日志，并在失败时自动回退到首个 pod/container。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "action": {"type": "string", "enum": ["service", "container"], "description": "service=组件普通日志；container=指定 Pod 容器日志"},
                    "lines": {"type": "integer", "minimum": 1, "description": "仅 action=service 时使用，默认 100"},
                    "pod_name": {"type": "string", "description": "仅 action=container 时必填"},
                    "container_name": {"type": "string", "description": "仅 action=container 时必填"},
                    "follow": {"type": "boolean", "description": "仅 action=container 时使用，是否跟随日志输出"},
                    "previous": {"type": "boolean", "description": "是否读取容器上一次（崩溃退出前）的日志。当容器处于 CrashLoopBackOff 或刚重启、当前实例无有效输出时，设为 true 可获取退出前的日志用于排查"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_exec_component(self):
        return {
            "name": "rainbond_exec",
            "description": (
                "在指定 Pod 容器内一次性执行命令（one-shot exec），返回 stdout/stderr/exit_code。"
                "仅适用于处于 Running 状态的容器，用于在线排查（例如 cat 配置文件、env、ls、ps、curl 健康检查等）。"
                "目标容器若正在崩溃重启（CrashLoopBackOff）或尚未运行，exec 无法连接，"
                "此时请改用 rainbond_get_component_logs（设置 previous=true 读取上一次退出前日志）排查；"
                "若需在 Pod 宕机时确认配置文件内容，请使用 rainbond_get_config_file。"
                "command 必须是字符串数组（如 [\"cat\", \"/app/config.yml\"]），不要传单个字符串。这是调试工具，stdout 会原样返回。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "pod_name": {"type": "string", "description": "目标 Pod 名称，可通过 rainbond_get_component_pods 获取"},
                    "container_name": {"type": "string", "description": "目标容器名，缺省时由 region 选择 Pod 的默认容器"},
                    "command": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "description": "要执行的命令及参数，字符串数组形式，如 [\"cat\", \"/app/config.yml\"] 或 [\"sh\", \"-c\", \"env | grep DB\"]"
                    },
                    "timeout_seconds": {"type": "integer", "minimum": 1, "description": "命令执行超时时间（秒），默认 30"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "pod_name", "command"]
            }
        }

    def _tool_get_config_file(self):
        return {
            "name": "rainbond_get_config_file",
            "description": (
                "读取组件的配置文件类（config-file）存储卷的内容。配置文件内容由平台持久化存储，"
                "即使 Pod 处于宕机/崩溃状态也可读取，适合在排查时确认实际下发到容器的配置（如 config.yml 是否被覆盖）。"
                "默认返回该组件全部 config-file 存储卷；可用 volume_name 或 volume_path 精确定位某个挂载。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "volume_name": {"type": "string", "description": "可选，配置文件存储卷名称，用于只返回某个配置文件"},
                    "volume_path": {"type": "string", "description": "可选，配置文件在容器内的挂载路径，用于按路径定位某个配置文件"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_manage_component_envs(self):
        return {
            "name": "rainbond_manage_component_envs",
            "description": "高层自定义环境变量管理工具。只用于组件自身环境变量（custom envs, inner）和构建环境变量（build envs），不要用于组件连接信息（outer）。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "operation": {"type": "string", "enum": ["summary", "upsert", "create", "update", "delete", "patch_scope", "replace_build_envs"]},
                    "envs": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "用于 upsert 的批量环境变量列表。若只 upsert 单条，也兼容直接传 attr_name/attr_value/name/is_change/scope。"
                    },
                    "env_id": {"type": "string"},
                    "name": {"type": "string", "description": "单条 upsert/create/update 时的人类可读名称；upsert 单条时可与 attr_name 相同。"},
                    "attr_name": {"type": "string", "description": "单条 upsert/create 时的环境变量名。"},
                    "attr_value": {"type": "string", "description": "单条 upsert/create/update 时的环境变量值。"},
                    "scope": {
                        "type": "string",
                        "description": "环境变量范围，默认 inner。该工具只支持 inner，也支持别名 local/self/runtime"
                    },
                    "is_change": {"type": "boolean"},
                    "build_env_dict": {
                        "type": "object",
                        "description": (
                            "全量替换源码构建参数字典。适合 replace_build_envs；不要把普通运行时环境变量放到这里。"
                            "常见键：通用 BUILD_TYPE=cnb、BUILD_NO_CACHE=true、BUILD_PROCFILE；"
                            "Node.js/static 用 CNB_FRAMEWORK、CNB_NODE_VERSION、CNB_NODE_ENV、CNB_BUILD_SCRIPT、"
                            "CNB_OUTPUT_DIR、CNB_START_SCRIPT、CNB_PACKAGE_TOOL、CNB_MIRROR_SOURCE、"
                            "CNB_MIRROR_NPMRC/CNB_MIRROR_YARNRC/CNB_MIRROR_PNPMRC；"
                            "Java 用 BP_JVM_VERSION、BP_JVM_TYPE、BP_MAVEN_SETTINGS_PATH、"
                            "BP_MAVEN_BUILD_ARGUMENTS、BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS、"
                            "BP_MAVEN_BUILT_MODULE、BP_MAVEN_BUILT_ARTIFACT、"
                            "BP_GRADLE_BUILD_ARGUMENTS、BP_GRADLE_ADDITIONAL_BUILD_ARGUMENTS，"
                            "兼容键 BUILD_MAVEN_SETTING_NAME；"
                            "Python 用 BP_CPYTHON_VERSION、BUILD_PIP_INDEX_URL、BUILD_PIP_TRUSTED_HOST、"
                            "BUILD_CONDA_SOLVER、BUILD_PROCFILE；"
                            "Golang 用 BP_GO_VERSION、GOPROXY、GOPRIVATE、BP_GO_TARGETS、"
                            "BP_GO_BUILD_FLAGS、BP_GO_BUILD_LDFLAGS、BUILD_PROCFILE；"
                            "PHP 用 BP_PHP_VERSION、BP_COMPOSER_INSTALL_OPTIONS、BP_PHP_WEB_DIR、BUILD_PROCFILE；"
                            ".NET 用 BP_DOTNET_FRAMEWORK_VERSION、BP_DOTNET_PROJECT_PATH、"
                            "BP_DOTNET_PUBLISH_FLAGS、BUILD_NUGET_CONFIG_NAME、BUILD_PROCFILE。"
                            "敏感认证如 COMPOSER_AUTH、运行期变量如 NODE_OPTIONS/JAVA_TOOL_OPTIONS "
                            "建议改用普通环境变量工具。"
                        )
                    }
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "operation"]
            }
        }

    def _tool_manage_component_connection_envs(self):
        return {
            "name": "rainbond_manage_component_connection_envs",
            "description": "高层组件连接信息管理工具。只用于组件连接信息（connection envs, outer），不要用于自定义环境变量（inner）。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "operation": {"type": "string", "enum": ["summary", "create", "update", "delete", "patch_scope"]},
                    "env_id": {"type": "string"},
                    "name": {"type": "string"},
                    "attr_name": {"type": "string"},
                    "attr_value": {"type": "string"},
                    "scope": {"type": "string", "description": "仅在 patch_scope 时使用。inner 表示迁移到自定义环境变量，outer 表示保持为组件连接信息"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "operation"]
            }
        }

    def _tool_get_component_detail(self):
        return {
            "name": "rainbond_get_component_detail",
            "description": "Get component detail by team, region, app and service ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_get_component_pods(self):
        return {
            "name": "rainbond_get_component_pods",
            "description": "List runtime pods of the component with normalized group and container names.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_get_pod_detail(self):
        return {
            "name": "rainbond_get_pod_detail",
            "description": (
                "Get runtime diagnostic detail of a specified pod under the component. "
                "pod_name MUST come from a prior rainbond_get_component_pods response — "
                "do not guess, construct, or recall pod names. Pods outside the given "
                "service_id (including platform-internal pods such as rbd-*) are not accessible."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "pod_name": {
                        "type": "string",
                        "description": "Pod 名称。必须来自最近一次 rainbond_get_component_pods 的返回结果，禁止凭空构造。"
                    }
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "pod_name"]
            }
        }

    def _tool_get_component_events(self):
        return {
            "name": "rainbond_get_component_events",
            "description": "Get component events with pagination.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_get_component_build_logs(self):
        return {
            "name": "rainbond_get_component_build_logs",
            "description": (
                "Get build event logs for a component by event_id. The event_id usually comes from build/create/deploy "
                "responses. For large projects (Maven monorepo, multi-stage Node.js builds, etc.) prefer narrowing the "
                "response with tail/grep/offset/limit — without them the upstream LLM client may middle-truncate the "
                "response and drop the real error which is usually near the tail."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "event_id": {"type": "string", "description": "构建事件 ID，一般来自构建、创建或部署操作的返回值。**必须**通过 rainbond_get_component_events 等只读工具拿到真实 UUID；不要从其它工具返回的 DB 行号（如 summary.recent_events[*].ID）当成 event_id 传入。"},
                    "tail": {"type": "integer", "minimum": 1, "description": "只返回末尾 N 条日志。构建失败时错误几乎总在尾部，优先用 tail（例如 tail=500）而不是拉全量再截断。与 offset/limit 同传时 tail 优先。"},
                    "offset": {"type": "integer", "minimum": 0, "description": "起始偏移（从 0 开始）。与 limit 搭配做翻页。"},
                    "limit": {"type": "integer", "minimum": 1, "description": "返回最多 N 条。与 offset 搭配做翻页。"},
                    "grep": {"type": "string", "description": "按 substring 匹配每条日志的 message 字段，常用于过滤 ERROR / BUILD FAILURE / Caused by 等关键行。grep 在 tail/offset/limit 之前生效。"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "event_id"]
            }
        }

    def _tool_get_component_build_source(self):
        return {
            "name": "rainbond_get_component_build_source",
            "description": "Get current build source summary for a component, including source type, repo/image info, build strategy, build envs, and available arch options. Passwords are not returned.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_update_component_build_source(self):
        return {
            "name": "rainbond_update_component_build_source",
            "description": "Update the component build source. Use this for switching between source_code and docker_run/image-manual style inputs; do not use it for build_env_dict updates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "service_source": {
                        "type": "string",
                        "enum": ["source_code", "docker_run", "docker_image"],
                        "description": "目标构建源类型。source_code=源码构建；docker_run/docker_image=镜像构建。"
                    },
                    "git_url": {"type": "string", "description": "源码仓库地址或对象存储制品地址。"},
                    "subdirectories": {"type": "string", "description": "源码子目录，会标准化追加到 git_url，例如 ?dir=services/api。"},
                    "code_version": {"type": "string", "description": "源码分支、提交或标签名。"},
                    "version_type": {"type": "string", "description": "源码版本类型；tag 会被标准化为 tag:<name>。"},
                    "server_type": {
                        "type": "string",
                        "enum": ["git", "svn", "oss"],
                        "description": "源码地址类型：git=Git仓库，svn=SVN仓库，oss=对象存储制品地址。"
                    },
                    "username": {"type": "string", "description": "源码仓库或镜像仓库用户名。"},
                    "password": {"type": "string", "description": "源码仓库或镜像仓库密码/令牌。"},
                    "is_oauth": {"type": "boolean", "description": "为 true 时按 OAuth 代码仓库处理。"},
                    "oauth_service_id": {"type": "string", "description": "仅 is_oauth=true 时使用。"},
                    "full_name": {"type": "string", "description": "仅 OAuth 代码仓库时使用的仓库全名。"},
                    "image": {"type": "string", "description": "镜像地址；目标为 docker_run/docker_image 时使用。"},
                    "cmd": {"type": "string", "description": "镜像启动命令；目标为 docker_run/docker_image 时使用。"},
                    "arch": {"type": "string", "description": "目标架构，例如 amd64、arm64。"},
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "service_source"]
            }
        }

    def _tool_create_component(self):
        return {
            "name": "rainbond_create_component",
            "description": (
                "Create a component from image in the specified application. "
                + self.IMAGE_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_cname": {"type": "string"},
                    "image": {"type": "string"},
                    "docker_cmd": {"type": "string"},
                    "k8s_component_name": {"type": "string"},
                    "user_name": {"type": "string"},
                    "password": {"type": "string"},
                    "is_deploy": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "service_cname", "image"]
            }
        }

    def _tool_delete_component(self):
        return {
            "name": "rainbond_delete_component",
            "description": "Delete a component from the specified application.",
            "annotations": {
                "destructiveHint": True
            },
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_operate_app(self):
        return {
            "name": "rainbond_operate_app",
            "description": "Batch operate application components. Supported actions: start, stop, restart, upgrade, deploy.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop", "restart", "upgrade", "deploy"]
                    },
                    "service_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["team_name", "region_name", "app_id", "action"]
            }
        }

    def _tool_update_component_envs(self):
        return {
            "name": "rainbond_update_component_envs",
            "description": "Update component environment variables.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "envs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "note": {"type": "string"},
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                                "is_change": {"type": "boolean"},
                                "scope": {"type": "string"}
                            },
                            "required": ["name", "value", "is_change", "scope"]
                        }
                    }
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "envs"]
            }
        }

    def _tool_change_component_image(self):
        return {
            "name": "rainbond_change_component_image",
            "description": "Change image of a docker-based component.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "image": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "image"]
            }
        }

    def _tool_get_team_apps(self):
        return {
            "name": "rainbond_get_team_apps",
            "description": "Get application list under the specified team and region.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "query": {"type": "string"}
                },
                "required": ["team_name", "region_name"]
            }
        }

    def _tool_get_app_version_overview(self):
        return {
            "name": "rainbond_get_app_version_overview",
            "description": "Get the overview data used by the app version center, including current baseline snapshot and change summary.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_list_app_version_snapshots(self):
        return {
            "name": "rainbond_list_app_version_snapshots",
            "description": "List snapshot versions for the specified app version center.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_get_app_version_snapshot_detail(self):
        return {
            "name": "rainbond_get_app_version_snapshot_detail",
            "description": "Get one snapshot version detail, including diff summary and template content.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "version_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "version_id"]
            }
        }

    def _tool_create_app_version_snapshot(self):
        return {
            "name": "rainbond_create_app_version_snapshot",
            "description": "Create a new snapshot version for the app. Optional share payload lets you persist the exact draft content from the snapshot configuration page.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "version": {"type": "string"},
                    "version_alias": {"type": "string"},
                    "app_version_info": {"type": "string"},
                    "share_service_list": {"type": "array", "items": {"type": "object"}},
                    "share_plugin_list": {"type": "array", "items": {"type": "object"}},
                    "share_k8s_resources": {"type": "array", "items": {"type": "object"}}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_delete_app_version_snapshot(self):
        return {
            "name": "rainbond_delete_app_version_snapshot",
            "description": "Delete a non-current historical snapshot version.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "version_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "version_id"]
            }
        }

    def _tool_rollback_app_version_snapshot(self):
        return {
            "name": "rainbond_rollback_app_version_snapshot",
            "description": "Rollback the current app runtime state to a target snapshot version.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "version_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "version_id"]
            }
        }

    def _tool_list_app_version_rollback_records(self):
        return {
            "name": "rainbond_list_app_version_rollback_records",
            "description": "List rollback records created by app version snapshot rollback actions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_get_app_version_rollback_record_detail(self):
        return {
            "name": "rainbond_get_app_version_rollback_record_detail",
            "description": "Get one app version rollback record with service-level status detail.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_delete_app_version_rollback_record(self):
        return {
            "name": "rainbond_delete_app_version_rollback_record",
            "description": "Delete a finished app version rollback record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_create_app_from_snapshot_version(self):
        return {
            "name": "rainbond_create_app_from_snapshot_version",
            "description": "Create a new app directly from a snapshot-generated hidden template without publishing it to the local library first.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "source_app_id": {"type": "integer", "minimum": 1},
                    "version_id": {"type": "integer", "minimum": 1},
                    "target_app_name": {
                        "type": "string",
                        "description": self.DISPLAY_APP_NAME_DESCRIPTION,
                        "pattern": self.DISPLAY_APP_NAME_PATTERN,
                        "maxLength": self.DISPLAY_APP_NAME_MAX_LENGTH,
                    },
                    "target_app_note": {"type": "string"},
                    "k8s_app": {
                        "type": "string",
                        "pattern": self.K8S_APP_NAME_PATTERN,
                        "description": self.K8S_APP_NAME_DESCRIPTION
                    },
                    "is_deploy": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "source_app_id", "version_id", "target_app_name"]
            }
        }

    def _tool_get_app_publish_candidates(self):
        return {
            "name": "rainbond_get_app_publish_candidates",
            "description": "Get publish candidate app models for the version publish page. Use scope=local for local component library or scope=goodrain for cloud app market.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "scope": {"type": "string", "enum": ["local", "goodrain"]},
                    "market_name": {"type": "string"},
                    "preferred_app_id": {"type": "string"},
                    "preferred_version": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_create_app_share_record(self):
        return {
            "name": "rainbond_create_app_share_record",
            "description": "Create a draft share record for publish or snapshot configuration. For local publish keep scope empty; for cloud publish set scope=goodrain and target.store_id. Set snapshot_mode=true to enter the snapshot creation flow.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "scope": {"type": "string", "enum": ["", "goodrain"]},
                    "target": {"type": "object"},
                    "snapshot_mode": {"type": "boolean"},
                    "snapshot_app_id": {"type": "string"},
                    "snapshot_version": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_list_app_share_records(self):
        return {
            "name": "rainbond_list_app_share_records",
            "description": "List publish records shown in the app version publish drawer.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "page": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_get_app_share_record(self):
        return {
            "name": "rainbond_get_app_share_record",
            "description": "Get one publish record used by the publish configuration page.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_delete_app_share_record(self):
        return {
            "name": "rainbond_delete_app_share_record",
            "description": "Delete or hide a finished publish record from the publish record drawer.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_get_app_share_info(self):
        return {
            "name": "rainbond_get_app_share_info",
            "description": "Get the draft share content for share step one. Returns publish_mode=snapshot when the draft is based on a snapshot version, otherwise publish_mode=runtime.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "share_id": {"type": "integer", "minimum": 1},
                    "scope": {"type": "string"}
                },
                "required": ["team_name", "region_name", "share_id"]
            }
        }

    def _tool_submit_app_share_info(self):
        return {
            "name": "rainbond_submit_app_share_info",
            "description": "Submit share step one data. app_version_info is required; runtime publish may also include share_service_list, share_plugin_list, and share_k8s_resources.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "share_id": {"type": "integer", "minimum": 1},
                    "use_force": {"type": "boolean"},
                    "is_plugin": {"type": "boolean"},
                    "app_version_info": {"type": "object"},
                    "share_service_list": {"type": "array", "items": {"type": "object"}},
                    "share_plugin_list": {"type": "array", "items": {"type": "object"}},
                    "share_k8s_resources": {"type": "array", "items": {"type": "object"}}
                },
                "required": ["team_name", "region_name", "share_id", "app_version_info"]
            }
        }

    def _tool_list_app_share_events(self):
        return {
            "name": "rainbond_list_app_share_events",
            "description": "List share step two events for both components and plugins.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "share_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "share_id"]
            }
        }

    def _tool_start_app_share_event(self):
        return {
            "name": "rainbond_start_app_share_event",
            "description": "Trigger a share step two event. Use event_type=service for component media sync or event_type=plugin for plugin sync.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "share_id": {"type": "integer", "minimum": 1},
                    "event_id": {"type": "integer", "minimum": 1},
                    "event_type": {"type": "string", "enum": ["service", "plugin"]}
                },
                "required": ["team_name", "region_name", "share_id", "event_id"]
            }
        }

    def _tool_get_app_share_event(self):
        return {
            "name": "rainbond_get_app_share_event",
            "description": "Query one share step two event status for a component or plugin event.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "share_id": {"type": "integer", "minimum": 1},
                    "event_id": {"type": "integer", "minimum": 1},
                    "event_type": {"type": "string", "enum": ["service", "plugin"]}
                },
                "required": ["team_name", "region_name", "share_id", "event_id"]
            }
        }

    def _tool_complete_app_share(self):
        return {
            "name": "rainbond_complete_app_share",
            "description": "Complete the publish workflow after all share events succeed.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "share_id": {"type": "integer", "minimum": 1},
                    "is_plugin": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "share_id"]
            }
        }

    def _tool_giveup_app_share(self):
        return {
            "name": "rainbond_giveup_app_share",
            "description": "Abort an unfinished share workflow and clean up its draft state.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "share_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "share_id"]
            }
        }

    def _tool_build_component(self):
        return {
            "name": "rainbond_build_component",
            "description": (
                "Step 4 of component creation: confirm creation and build or deploy the component. "
                + self.BUILD_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "build_info": {
                        "type": "object",
                        "description": (
                            "构建确认阶段使用的少量结构化参数。支持 repo_url、branch、username、password。"
                            "repo_url=源码仓库地址或镜像地址；branch=源码分支或标签（源码构建时生效）；"
                            "username/password=仓库或镜像仓库凭据。构建参数请不要放在 build_info 中，"
                            "应改用 rainbond_manage_component_envs(operation=replace_build_envs, build_env_dict=...)."
                        ),
                        "properties": {
                            "repo_url": {"type": "string", "description": "源码仓库地址或镜像地址。"},
                            "branch": {"type": "string", "description": "源码分支或标签；仅源码构建组件生效。"},
                            "username": {"type": "string", "description": "源码仓库或镜像仓库用户名。"},
                            "password": {"type": "string", "description": "源码仓库或镜像仓库密码/令牌。"},
                        }
                    },
                    "is_deploy": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_get_app_last_upgrade_record(self):
        return {
            "name": "rainbond_get_app_last_upgrade_record",
            "description": "Get the latest upgrade or rollback record for the specified application.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "upgrade_group_id": {"type": "integer", "minimum": 1},
                    "record_type": {"type": "string", "enum": ["upgrade", "rollback"]}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_query_app_upgrade_records(self):
        return {
            "name": "rainbond_query_app_upgrade_records",
            "description": "Query paginated upgrade records for the specified application.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_type": {"type": "string", "enum": ["upgrade", "rollback"]},
                    "page": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_create_app_upgrade_record(self):
        return {
            "name": "rainbond_create_app_upgrade_record",
            "description": "Create a new upgrade record for a specific upgrade group in the application.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "upgrade_group_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "upgrade_group_id"]
            }
        }

    def _tool_get_app_upgrade_record(self):
        return {
            "name": "rainbond_get_app_upgrade_record",
            "description": "Get one upgrade record with service-level status details and snapshot metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_get_app_upgrade_detail(self):
        return {
            "name": "rainbond_get_app_upgrade_detail",
            "description": "Get upgrade record context together with available target versions for that record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_get_app_upgrade_changes(self):
        return {
            "name": "rainbond_get_app_upgrade_changes",
            "description": "Get property changes for a target upgrade version before executing the upgrade.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "version": {"type": "string"},
                    "upgrade_group_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "version"]
            }
        }

    def _tool_execute_app_upgrade_record(self):
        return {
            "name": "rainbond_execute_app_upgrade_record",
            "description": "Execute one upgrade record with the selected target version and optional component subset.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1},
                    "version": {"type": "string"},
                    "services": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "required": ["team_name", "region_name", "app_id", "record_id", "version"]
            }
        }

    def _tool_deploy_app_upgrade_record(self):
        return {
            "name": "rainbond_deploy_app_upgrade_record",
            "description": "Redeploy or continue a specific upgrade/rollback record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_get_app_rollback_records(self):
        return {
            "name": "rainbond_get_app_rollback_records",
            "description": "List rollback records derived from a specific upgrade record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_rollback_app_upgrade_record(self):
        return {
            "name": "rainbond_rollback_app_upgrade_record",
            "description": "Rollback a specific upgrade record using its internal snapshot.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "record_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "record_id"]
            }
        }

    def _tool_get_app_upgrade_info(self):
        return {
            "name": "rainbond_get_app_upgrade_info",
            "description": "Get upgradeable application model information for the specified app.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_upgrade_app(self):
        return {
            "name": "rainbond_upgrade_app",
            "description": "Upgrade an application using the direct high-level console upgrade flow.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "update_versions": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "required": ["team_name", "region_name", "app_id", "update_versions"]
            }
        }

    def _tool_get_copy_app_info(self):
        return {
            "name": "rainbond_get_copy_app_info",
            "description": "Get component metadata required before copying an application.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_copy_app(self):
        return {
            "name": "rainbond_copy_app",
            "description": "Copy application components to another team/region/app using direct console copy flow.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "target_team_name": {"type": "string"},
                    "target_region_name": {"type": "string"},
                    "target_app_id": {"type": "integer", "minimum": 1},
                    "services": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "required": ["team_name", "region_name", "app_id", "target_team_name", "target_region_name", "target_app_id"]
            }
        }

    def _tool_query_cloud_markets(self):
        return {
            "name": "rainbond_query_cloud_markets",
            "description": "List configured cloud application markets for an enterprise.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enterprise_id": {"type": "string"},
                    "extend": {"type": "boolean", "description": "Whether to include extended market metadata."}
                },
                "required": ["enterprise_id"]
            }
        }

    def _tool_query_local_app_models(self):
        return {
            "name": "rainbond_query_local_app_models",
            "description": "List local application templates available inside the enterprise market.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enterprise_id": {"type": "string"},
                    "scope": {"type": "string", "enum": ["enterprise", "team", ""]},
                    "query": {"type": "string"},
                    "app_name": {"type": "string"},
                    "arch": {"type": "string"},
                    "tenant_name": {"type": "string"},
                    "is_plugin": {"type": "boolean"},
                    "page": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                },
                "required": ["enterprise_id"]
            }
        }

    def _tool_query_cloud_app_models(self):
        return {
            "name": "rainbond_query_cloud_app_models",
            "description": "List app templates from a specific cloud market.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enterprise_id": {"type": "string"},
                    "market_name": {"type": "string"},
                    "query": {"type": "string"},
                    "query_all": {"type": "boolean"},
                    "arch": {"type": "string"},
                    "is_plugin": {"type": "boolean"},
                    "page": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                },
                "required": ["enterprise_id", "market_name"]
            }
        }

    def _tool_query_app_model_versions(self):
        return {
            "name": "rainbond_query_app_model_versions",
            "description": "List versions for a local or cloud app template.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enterprise_id": {"type": "string"},
                    "source": {"type": "string", "enum": ["local", "cloud"]},
                    "market_name": {"type": "string", "description": "Required when source=cloud."},
                    "app_model_id": {"type": "string"},
                    "query_all": {"type": "boolean"},
                    "page": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                },
                "required": ["enterprise_id", "source", "app_model_id"]
            }
        }

    def _tool_install_app_model(self):
        return {
            "name": "rainbond_install_app_model",
            "description": "Install a local or cloud app template into an existing app.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "source": {"type": "string", "enum": ["local", "cloud"]},
                    "market_name": {"type": "string", "description": "Required when source=cloud."},
                    "app_model_id": {"type": "string"},
                    "app_model_name": {"type": "string", "description": "Optional display-only template name."},
                    "app_model_version": {"type": "string"},
                    "is_deploy": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "source", "app_model_id", "app_model_version"]
            }
        }

    def _tool_install_app_by_market(self):
        return {
            "name": "rainbond_install_app_by_market",
            "description": "Install application components from market into an existing app.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "market_url": {"type": "string"},
                    "market_domain": {"type": "string"},
                    "market_type": {"type": "string"},
                    "market_access_key": {"type": "string"},
                    "app_model_id": {"type": "string"},
                    "app_model_version": {"type": "string"},
                    "is_deploy": {"type": "boolean"}
                },
                "required": [
                    "team_name", "region_name", "app_id", "market_url", "market_domain", "market_type",
                    "market_access_key", "app_model_id", "app_model_version"
                ]
            }
        }

    def _tool_create_component_from_source(self):
        return {
            "name": "rainbond_create_component_from_source",
            "description": (
                "Create a source-code component with automatic detection and default configuration, then build it in one flow. "
                + self.SOURCE_PACKAGE_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "code_from": {
                        "type": "string",
                        "description": (
                            "源码来源标识。推荐优先使用 git/github/oauth_xxx："
                            "git（通用 Git/Gitee/GitLab 仓库）、"
                            "github（GitHub 仓库）、oauth_xxx（OAuth 代码仓库，如 oauth_github）。"
                            "也兼容 gitlab_manual、gitlab_self、gitlab_new、gitlab_exit、gitlab_demo；"
                            "若不确定，优先传 git。"
                        )
                    },
                    "service_cname": {"type": "string"},
                    "git_url": {"type": "string", "description": "源码仓库地址或对象存储制品地址。"},
                    "git_project_id": {"type": "string"},
                    "code_version": {"type": "string"},
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "server_type": {
                        "type": "string",
                        "enum": ["git", "svn", "oss"],
                        "description": "源码地址类型：git=Git仓库，svn=SVN仓库，oss=对象存储制品地址"
                    },
                    "version_type": {"type": "string", "description": "源码版本类型；tag 会被标准化为 tag:<name>。"},
                    "subdirectories": {
                        "type": "string",
                        "description": "源码子目录。MCP 会把它标准化追加到 git_url，例如 ?dir=services/api。"
                    },
                    "check_uuid": {"type": "string"},
                    "event_id": {"type": "string"},
                    "oauth_service_id": {"type": "string"},
                    "full_name": {"type": "string"},
                    "k8s_component_name": {"type": "string"},
                    "arch": {"type": "string"},
                    "is_deploy": {"type": "boolean"},
                    "prefer_dockerfile_when_detected": {
                        "type": "boolean",
                        "description": (
                            "仅 MCP 使用。若检测结果同时命中 Dockerfile 和语言型构建方式（如 Node.js），"
                            "优先选择 Dockerfile。默认 false，不影响前端默认流程。"
                            "当前 MCP 仅支持布尔偏好，不支持指定具体 dockerfile_path。"
                        )
                    }
                },
                "required": ["team_name", "region_name", "app_id", "code_from", "service_cname", "git_url"]
            }
        }

    def _tool_create_component_from_package(self):
        return {
            "name": "rainbond_create_component_from_package",
            "description": (
                "Create a component from an uploaded software package event in one flow after upload is complete. "
                + self.SOURCE_PACKAGE_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "event_id": {"type": "string", "description": "上传软件包后返回的 event_id"},
                    "service_cname": {"type": "string"},
                    "k8s_component_name": {"type": "string"},
                    "arch": {"type": "string"},
                    "is_deploy": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "event_id", "service_cname"]
            }
        }

    def _tool_init_package_upload(self):
        return {
            "name": "rainbond_init_package_upload",
            "description": "Initialize a package upload event and return the upload endpoint before sending the package file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "component_id": {"type": "string", "description": "可选。已有组件重传时用于关联历史上传记录。"}
                },
                "required": ["team_name", "region_name"]
            }
        }

    def _tool_upload_package_file(self):
        return {
            "name": "rainbond_upload_package_file",
            "description": "Upload a local package file or directory to an initialized package upload event; directories are zipped automatically.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "event_id": {"type": "string"},
                    "local_path": {
                        "type": "string",
                        "description": self.SERVER_LOCAL_PATH_DESCRIPTION
                    },
                    "archive_name": {
                        "type": "string",
                        "description": "可选。目录压缩时使用的 zip 文件名；未传则默认用目录名并自动补齐 .zip。"
                    }
                },
                "required": ["team_name", "region_name", "event_id", "local_path"]
            }
        }

    def _tool_get_package_upload_status(self):
        return {
            "name": "rainbond_get_package_upload_status",
            "description": "Get uploaded package file names for a package upload event.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "event_id": {"type": "string"}
                },
                "required": ["team_name", "region_name", "event_id"]
            }
        }

    def _tool_delete_package_upload(self):
        return {
            "name": "rainbond_delete_package_upload",
            "description": "Delete uploaded package artifacts for a package upload event and mark the upload record as deleted.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "event_id": {"type": "string"}
                },
                "required": ["team_name", "region_name", "event_id"]
            }
        }

    def _tool_create_component_from_local_package(self):
        return {
            "name": "rainbond_create_component_from_local_package",
            "description": (
                "Create a component from a local package file or directory in one flow: zip if needed, upload, detect, build, and optionally deploy. "
                + self.SOURCE_PACKAGE_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "local_path": {
                        "type": "string",
                        "description": self.SERVER_LOCAL_PATH_DESCRIPTION
                    },
                    "archive_name": {
                        "type": "string",
                        "description": "可选。目录压缩时使用的 zip 文件名；未传则默认使用目录名。"
                    },
                    "service_cname": {"type": "string"},
                    "k8s_component_name": {"type": "string"},
                    "arch": {"type": "string"},
                    "is_deploy": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "local_path", "service_cname"]
            }
        }

    def _tool_check_component(self):
        return {
            "name": "rainbond_check_component",
            "description": "Step 2 of component creation: start source or package detection for the specified component.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "event_id": {"type": "string"},
                    "is_again": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_get_component_check_result(self):
        return {
            "name": "rainbond_get_component_check_result",
            "description": "Step 3 of component creation: get detection result and persist detected metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "check_uuid": {"type": "string"},
                    "prefer_dockerfile_when_detected": {
                        "type": "boolean",
                        "description": (
                            "仅 MCP 使用。重新检测后若结果同时命中 Dockerfile 和语言型构建方式，"
                            "优先选择 Dockerfile（与 create 时同名参数一致）。用于恢复路径强制 Dockerfile，"
                            "避免 CNB 不支持的语言/版本（如 .NET 7）卡死。默认 false。"
                        )
                    }
                },
                "required": ["team_name", "region_name", "app_id", "service_id"]
            }
        }

    def _tool_create_component_from_image(self):
        return {
            "name": "rainbond_create_component_from_image",
            "description": (
                "Create a component from image in the specified application. "
                + self.IMAGE_COMPONENT_DEFAULT_RESOURCE_DESCRIPTION
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_cname": {"type": "string"},
                    "image": {"type": "string"},
                    "docker_cmd": {"type": "string"},
                    "k8s_component_name": {"type": "string"},
                    "user_name": {"type": "string"},
                    "password": {"type": "string"},
                    "is_deploy": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "service_cname", "image"]
            }
        }

    def _tool_create_app_from_yaml(self):
        return {
            "name": "rainbond_create_app_from_yaml",
            "description": "Create a compose application from uploaded YAML event metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "event_id": {"type": "string"},
                    "compose_file_path": {"type": "string"},
                    "user_name": {"type": "string"},
                    "password": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id", "event_id"]
            }
        }

    def _tool_check_yaml_app(self):
        return {
            "name": "rainbond_check_yaml_app",
            "description": "Check a compose application created from YAML.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "compose_id": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id", "compose_id"]
            }
        }

    def _tool_get_yaml_app_check_result(self):
        return {
            "name": "rainbond_get_yaml_app_check_result",
            "description": "Get and persist compose YAML check result, returning generated services.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "compose_id": {"type": "string"},
                    "check_uuid": {"type": "string"},
                    "arch": {"type": "string"}
                },
                "required": ["team_name", "region_name", "app_id", "compose_id", "check_uuid"]
            }
        }

    def _tool_query_app_monitor(self):
        return {
            "name": "rainbond_query_app_monitor",
            "description": "Query real-time monitor data of components under an application.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "is_outer": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id"]
            }
        }

    def _tool_query_app_monitor_range(self):
        return {
            "name": "rainbond_query_app_monitor_range",
            "description": "Query historical monitor data of components under an application.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "step": {"type": "integer", "minimum": 1},
                    "is_outer": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "start", "end"]
            }
        }

    def _tool_create_gateway_rules(self):
        return {
            "name": "rainbond_create_gateway_rules",
            "description": "Create HTTP or TCP gateway rules for an application.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "protocol": {"type": "string"},
                    "http": {"type": "object"},
                    "tcp": {"type": "object"}
                },
                "required": ["team_name", "region_name", "app_id", "protocol"]
            }
        }

    def _tool_check_helm_app(self):
        return {
            "name": "rainbond_check_helm_app",
            "description": "Check helm application information before generating template or deployment.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "name": {"type": "string"},
                    "repo_name": {"type": "string"},
                    "chart_name": {"type": "string"},
                    "version": {"type": "string"},
                    "overrides": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["team_name", "region_name", "name", "repo_name", "chart_name", "version"]
            }
        }

    def _tool_build_helm_app(self):
        return {
            "name": "rainbond_build_helm_app",
            "description": "Generate helm application template directly through console helm flow.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "name": {"type": "string"},
                    "repo_name": {"type": "string"},
                    "chart_name": {"type": "string"},
                    "version": {"type": "string"},
                    "app_model_id": {"type": "string"},
                    "overrides": {"type": "object"}
                },
                "required": ["team_name", "region_name", "app_id", "name", "repo_name", "chart_name", "version", "app_model_id"]
            }
        }

    def _tool_handle_component_ports(self):
        return {
            "name": "rainbond_handle_component_ports",
            "description": "List, add, update, or delete component ports.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "operation": {"type": "string"},
                    "port": {"type": "integer", "minimum": 1},
                    "protocol": {"type": "string"},
                    "port_alias": self._port_alias_schema(),
                    "is_inner_service": {"type": "boolean"},
                    "action": {
                        "type": "string",
                        "enum": list(self.PORT_ACTION_ENUM),
                        "description": (
                            "端口更新动作。可选值: open_outer=开启对外访问, only_open_outer=仅开启对外访问, "
                            "close_outer=关闭对外访问, open_inner=开启对内访问, close_inner=关闭对内访问, "
                            "change_protocol=修改协议, change_port_alias=修改端口别名。"
                        )
                    },
                    "k8s_service_name": self._k8s_service_name_schema(),
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "operation"]
            }
        }

    def _tool_manage_component_ports(self):
        return {
            "name": "rainbond_manage_component_ports",
            "description": (
                "高层端口管理工具。明确区分对内服务和对外服务：对内服务用于组件间访问，对外服务用于外部访问。"
                "推荐优先使用 enable_inner / enable_outer / disable_inner / disable_outer / enable_outer_only 这些显式动作。"
                "批量操作：operation=add 时可传 ports 数组一次创建多个端口；"
                "enable_inner/disable_inner/enable_outer/disable_outer 时可传 ports 数组批量开关服务。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "operation": {
                        "type": "string",
                        "enum": [
                            "summary", "add", "delete",
                            "enable_inner", "disable_inner",
                            "enable_outer", "disable_outer",
                            "enable_outer_only",
                            "update_protocol", "update_alias",
                            "update"
                        ],
                        "description": (
                            "推荐动作：summary=查看端口；add=新增端口（支持 ports 数组批量）；"
                            "enable_inner=开启对内服务（支持 ports 数组批量）；"
                            "disable_inner=关闭对内服务（支持 ports 数组批量）；"
                            "enable_outer=开启对外服务，要求已开启对内服务（支持 ports 数组批量）；"
                            "disable_outer=关闭对外服务（支持 ports 数组批量）；"
                            "enable_outer_only=仅开启对外服务；"
                            "update_protocol=修改协议；update_alias=修改端口别名。"
                        )
                    },
                    "port": {"type": "integer", "minimum": 1},
                    "ports": {
                        "type": "array",
                        "description": (
                            "批量端口列表，与 operation 配合使用。"
                            "operation=add 时每项需含 port(int) 和 protocol(str)，可选 is_inner_service/enable_inner(bool)、port_alias(str)；"
                            "enable_inner/disable_inner/enable_outer/disable_outer 时每项为 {\"port\": <int>} 或直接为整数。"
                            "传入 ports 时忽略顶层 port 字段。"
                        ),
                        "items": {
                            "oneOf": [
                                {"type": "integer", "minimum": 1},
                                {
                                    "type": "object",
                                    "properties": {
                                        "port": {"type": "integer", "minimum": 1},
                                        "protocol": {"type": "string"},
                                        "is_inner_service": {"type": "boolean"},
                                        "enable_inner": {"type": "boolean"},
                                        "port_alias": self._port_alias_schema(),
                                    },
                                    "required": ["port"],
                                },
                            ]
                        },
                    },
                    "protocol": {"type": "string"},
                    "port_alias": self._port_alias_schema(),
                    "is_inner_service": {"type": "boolean", "description": "新增端口时是否默认开启对内服务"},
                    "enable_inner": {"type": "boolean", "description": "新增端口时更推荐用这个字段表达是否开启对内服务"},
                    "action": {
                        "type": "string",
                        "enum": list(self.PORT_ACTION_ENUM),
                        "description": "兼容旧调用时使用。新调用推荐直接使用 operation 的显式动作，不推荐模型自行填写 action。"
                    },
                    "k8s_service_name": self._k8s_service_name_schema(),
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "operation"]
            }
        }

    def _tool_bind_component_volume(self):
        return {
            "name": "rainbond_bind_component_volume",
            "description": "Bind a storage volume to a component.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "volume_name": {"type": "string"},
                    "volume_type": {"type": "string"},
                    "volume_path": {"type": "string"},
                    "volume_capacity": {"type": "integer", "minimum": 0},
                    "provider_name": {"type": "string"},
                    "access_mode": {"type": "string"},
                    "share_policy": {"type": "string"},
                    "back_policy": {"type": "string"},
                    "reclaim_policy": {"type": "string"},
                    "allow_expansion": {"type": "boolean"},
                    "file_content": {"type": "string"},
                    "mode": {"type": "integer"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "volume_name", "volume_type", "volume_path"]
            }
        }

    def _tool_manage_component_storage(self):
        return {
            "name": "rainbond_manage_component_storage",
            "description": "高层存储管理工具，统一处理组件 volume 和挂载关系 mnt。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "operation": {
                        "type": "string",
                        "enum": [
                            "summary", "list_unmounted", "create_volume", "update_volume",
                            "delete_volume", "create_mnt", "delete_mnt"
                        ]
                    },
                    "is_config": {"type": "boolean"},
                    "volume_types": {"type": "array", "items": {"type": "string"}},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1},
                    "dep_app_name": {"type": "string"},
                    "dep_app_group": {"type": "string"},
                    "config_name": {"type": "string"},
                    "volume_id": {"type": "integer", "minimum": 1},
                    "new_volume_path": {"type": "string"},
                    "new_file_content": {"type": "string"},
                    "force": {"type": "boolean"},
                    "volume_name": {"type": "string"},
                    "volume_type": {"type": "string"},
                    "volume_path": {"type": "string"},
                    "volume_capacity": {"type": "integer", "minimum": 0},
                    "provider_name": {"type": "string"},
                    "access_mode": {"type": "string"},
                    "share_policy": {"type": "string"},
                    "back_policy": {"type": "string"},
                    "reclaim_policy": {"type": "string"},
                    "allow_expansion": {"type": "boolean"},
                    "file_content": {"type": "string"},
                    "mode": {"type": "integer"},
                    "mounts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "minimum": 1},
                                "path": {"type": "string"}
                            }
                        }
                    },
                    "dep_vol_id": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "operation"]
            }
        }

    def _tool_manage_component_autoscaler(self):
        return {
            "name": "rainbond_manage_component_autoscaler",
            "description": "高层自动伸缩管理工具，统一处理伸缩规则和伸缩记录。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "operation": {"type": "string", "enum": ["summary", "get_rule", "create_rule", "update_rule", "records"]},
                    "rule_id": {"type": "string"},
                    "xpa_type": {"type": "string", "enum": ["hpa"]},
                    "enable": {"type": "boolean"},
                    "min_replicas": {"type": "integer", "minimum": 1},
                    "max_replicas": {"type": "integer", "minimum": 1},
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "metric_type": {"type": "string", "enum": ["resource_metrics"]},
                                "metric_name": {"type": "string", "enum": ["cpu", "memory"]},
                                "metric_target_type": {"type": "string", "enum": ["utilization", "average_value"]},
                                "metric_target_value": {"type": "integer", "minimum": 0, "maximum": 65535}
                            },
                            "required": ["metric_type", "metric_name", "metric_target_type", "metric_target_value"]
                        }
                    },
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "operation"]
            }
        }

    def _tool_manage_component_probe(self):
        return {
            "name": "rainbond_manage_component_probe",
            "description": "高层探针管理工具，统一处理组件健康探针的查看、新增、修改、删除。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "operation": {"type": "string", "enum": ["summary", "get", "create", "update", "delete"]},
                    "probe_id": {"type": "string"},
                    "mode": {"type": "string", "enum": ["readiness", "liveness", "ignore"]},
                    "port": {"type": "integer", "minimum": 1},
                    "scheme": {"type": "string"},
                    "path": {"type": "string"},
                    "cmd": {"type": "string"},
                    "http_header": {"type": "string"},
                    "initial_delay_second": {"type": "integer", "minimum": 1},
                    "period_second": {"type": "integer", "minimum": 1},
                    "timeout_second": {"type": "integer", "minimum": 1},
                    "failure_threshold": {"type": "integer", "minimum": 1},
                    "success_threshold": {"type": "integer", "minimum": 1},
                    "is_used": {"type": "boolean"}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "operation"]
            }
        }

    def _tool_manage_component_dependency(self):
        return {
            "name": "rainbond_manage_component_dependency",
            "description": "高层依赖管理工具，统一处理组件依赖、反向依赖及可依赖组件查询。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "operation": {"type": "string", "enum": ["summary", "add", "add_reverse", "delete"]},
                    "dep_service_id": {"type": "string", "description": "要依赖的目标组件 ID。"},
                    "dep_service_ids": {"type": "array", "items": {"type": "string"}},
                    "be_dep_service_ids": {"type": "array", "items": {"type": "string"}},
                    "open_inner": {
                        "type": "boolean",
                        "description": "为 true 时，自动开启被依赖组件的对内端口。若目标组件尚未开启对内端口，推荐优先让系统返回可选端口列表后再决定。"
                    },
                    "container_port": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "仅在 open_inner=true 时使用，表示被依赖组件 dep_service_id 的 container_port，而不是当前组件的端口。"
                    }
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "operation"]
            }
        }

    def _tool_horizontal_scale_component(self):
        return {
            "name": "rainbond_horizontal_scale_component",
            "description": "Horizontally scale a component.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "new_node": {"type": "integer", "minimum": 0}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "new_node"]
            }
        }

    def _tool_vertical_scale_component(self):
        return {
            "name": "rainbond_vertical_scale_component",
            "description": "Vertically scale a component.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "service_id": {"type": "string"},
                    "new_memory": {"type": "integer", "minimum": 0},
                    "new_gpu": {"type": "integer", "minimum": 0},
                    "new_cpu": {"type": "integer", "minimum": 0}
                },
                "required": ["team_name", "region_name", "app_id", "service_id", "new_memory"]
            }
        }

    def _tool_close_apps(self):
        return {
            "name": "rainbond_close_apps",
            "description": "Batch stop application components in a team and region.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "service_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["team_name", "region_name"]
            }
        }

    def _tool_query_enterprises(self):
        return {
            "name": "rainbond_query_enterprises",
            "description": "Query enterprises that current enterprise administrator can access.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                }
            }
        }

    def _tool_query_regions(self):
        return {
            "name": "rainbond_query_regions",
            "description": "Query cluster regions under the specified enterprise. Only available for enterprise administrators.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enterprise_id": {"type": "string"},
                    "query": {"type": "string"},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                }
            }
        }

    def _tool_get_region_detail(self):
        return {
            "name": "rainbond_get_region_detail",
            "description": "Get cluster detail by region ID. Only available for enterprise administrators.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region_id": {"type": "string"},
                    "extend_info": {"type": "boolean"}
                },
                "required": ["region_id"]
            }
        }

    def _tool_create_region(self):
        return {
            "name": "rainbond_create_region",
            "description": "Create a new cluster metadata record.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region_name": {"type": "string"},
                    "region_alias": {"type": "string"},
                    "url": {"type": "string"},
                    "token": {"type": "string"},
                    "wsurl": {"type": "string"},
                    "httpdomain": {"type": "string"},
                    "tcpdomain": {"type": "string"},
                    "scope": {"type": "string"},
                    "ssl_ca_cert": {"type": "string"},
                    "cert_file": {"type": "string"},
                    "key_file": {"type": "string"},
                    "status": {"type": "string"},
                    "desc": {"type": "string"}
                },
                "required": ["region_name", "region_alias", "url", "wsurl", "httpdomain", "tcpdomain"]
            }
        }

    def _tool_update_region(self):
        return {
            "name": "rainbond_update_region",
            "description": "Update cluster metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region_id": {"type": "string"},
                    "region_alias": {"type": "string"},
                    "url": {"type": "string"},
                    "token": {"type": "string"},
                    "wsurl": {"type": "string"},
                    "httpdomain": {"type": "string"},
                    "tcpdomain": {"type": "string"},
                    "scope": {"type": "string"},
                    "ssl_ca_cert": {"type": "string"},
                    "cert_file": {"type": "string"},
                    "key_file": {"type": "string"},
                    "status": {"type": "string"},
                    "desc": {"type": "string"}
                },
                "required": ["region_id"]
            }
        }

    def _tool_delete_region(self):
        return {
            "name": "rainbond_delete_region",
            "description": "Delete cluster metadata.",
            "annotations": {
                "destructiveHint": True
            },
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region_id": {"type": "string"}
                },
                "required": ["region_id"]
            }
        }

    def _tool_query_region_nodes(self):
        return {
            "name": "rainbond_query_region_nodes",
            "description": "Query cluster nodes under the specified region.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region_name": {"type": "string"}
                },
                "required": ["region_name"]
            }
        }

    def _tool_get_region_node_detail(self):
        return {
            "name": "rainbond_get_region_node_detail",
            "description": "Get detail of a cluster node in the specified region.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region_name": {"type": "string"},
                    "node_name": {"type": "string"}
                },
                "required": ["region_name", "node_name"]
            }
        }

    def _tool_query_region_rbd_components(self):
        return {
            "name": "rainbond_query_region_rbd_components",
            "description": "Query Rainbond platform components running in the specified region.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region_name": {"type": "string"}
                },
                "required": ["region_name"]
            }
        }

    def _build_create_region_data(self, arguments, enterprise_id):
        return {
            "region_id": arguments.get("region_id") or make_uuid(),
            "enterprise_id": enterprise_id,
            "region_name": self._require_string(arguments, "region_name"),
            "region_alias": self._require_string(arguments, "region_alias"),
            "url": self._require_string(arguments, "url"),
            "token": arguments.get("token", "") or "",
            "wsurl": self._require_string(arguments, "wsurl"),
            "httpdomain": self._require_string(arguments, "httpdomain"),
            "tcpdomain": self._require_string(arguments, "tcpdomain"),
            "scope": (arguments.get("scope") or "private").strip(),
            "ssl_ca_cert": arguments.get("ssl_ca_cert", "") or "",
            "cert_file": arguments.get("cert_file", "") or "",
            "key_file": arguments.get("key_file", "") or "",
            "status": (arguments.get("status") or "1").strip(),
            "desc": arguments.get("desc", "") or "",
        }

    def _build_update_region_data(self, arguments):
        allowed_fields = [
            "region_alias", "url", "token", "wsurl", "httpdomain", "tcpdomain", "scope", "ssl_ca_cert", "cert_file",
            "key_file", "status", "desc"
        ]
        update_data = {}
        for field in allowed_fields:
            if field in arguments:
                update_data[field] = arguments.get(field)
        if not update_data:
            raise ServiceHandleException(msg="invalid update payload", msg_show="至少需要提供一个可更新字段", status_code=400)
        return update_data

    def _build_region_update_data(self, region):
        return {
            "region_id": self._value(region, "region_id"),
            "region_alias": self._value(region, "region_alias"),
            "url": self._value(region, "url"),
            "token": self._value(region, "token", "") or "",
            "wsurl": self._value(region, "wsurl"),
            "httpdomain": self._value(region, "httpdomain"),
            "tcpdomain": self._value(region, "tcpdomain"),
            "scope": self._value(region, "scope"),
            "ssl_ca_cert": self._value(region, "ssl_ca_cert", "") or "",
            "cert_file": self._value(region, "cert_file", "") or "",
            "key_file": self._value(region, "key_file", "") or "",
            "status": self._value(region, "status"),
            "desc": self._value(region, "desc", "") or "",
            "region_name": self._value(region, "region_name"),
            "enterprise_id": self._value(region, "enterprise_id"),
        }


    def _tool_query_teams(self):
        return {
            "name": "rainbond_query_teams",
            "description": "Query teams under the specified enterprise.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enterprise_id": {"type": "string"},
                    "query": {"type": "string"},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                },
                "required": ["enterprise_id"]
            }
        }

    def _tool_query_apps(self):
        return {
            "name": "rainbond_query_apps",
            "description": "Query applications under the specified enterprise.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enterprise_id": {"type": "string"},
                    "query": {"type": "string"},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                },
                "required": ["enterprise_id"]
            }
        }

    def _tool_query_components(self):
        return {
            "name": "rainbond_query_components",
            "description": "Query components under the specified application.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "enterprise_id": {"type": "string"},
                    "app_id": {"type": "integer", "minimum": 1},
                    "query": {"type": "string"},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": self.MAX_PAGE_SIZE}
                },
                "required": ["enterprise_id", "app_id"]
            }
        }

    def _tool_delete_app(self):
        return {
            "name": "rainbond_delete_app",
            "description": "Delete an application. This is a destructive operation and requires confirmation.",
            "annotations": {
                "destructiveHint": True
            },
            "inputSchema": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "integer", "minimum": 1},
                    "enterprise_id": {"type": "string"},
                    "team_name": {"type": "string"},
                    "region_name": {"type": "string"},
                    "confirm": {"type": "boolean"},
                    "confirmation_token": {"type": "string"}
                },
                "required": ["app_id"]
            }
        }


mcp_query_service = MCPQueryService()
