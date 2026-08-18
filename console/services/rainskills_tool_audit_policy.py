# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Dict, FrozenSet


@dataclass(frozen=True)
class ToolAuditSpec:
    operation_class: str
    risk: str
    scope: str


def _write(risk: str, scope: str) -> ToolAuditSpec:
    return ToolAuditSpec("write", risk, scope)


# This policy is authoritative for the Console audit gate. Keep the explicit
# coverage test in sync whenever the RainSkills-visible tool catalog changes.
MUTABLE_TOOL_POLICY: Dict[str, ToolAuditSpec] = {
    "rainbond_build_component": _write("medium", "component"),
    "rainbond_build_helm_app": _write("medium", "app"),
    "rainbond_change_component_image": _write("medium", "component"),
    "rainbond_check_component": _write("low", "component"),
    "rainbond_check_helm_app": _write("low", "app"),
    "rainbond_check_yaml_app": _write("low", "app"),
    "rainbond_close_apps": _write("medium", "app"),
    "rainbond_complete_app_share": _write("low", "app"),
    "rainbond_copy_app": _write("medium", "app"),
    "rainbond_create_app": _write("medium", "team"),
    "rainbond_create_app_from_snapshot_version": _write("medium", "app"),
    "rainbond_create_app_from_yaml": _write("medium", "app"),
    "rainbond_create_app_share_record": _write("low", "app"),
    "rainbond_create_app_upgrade_record": _write("low", "app"),
    "rainbond_create_app_version_snapshot": _write("low", "app"),
    "rainbond_create_component": _write("medium", "component"),
    "rainbond_create_component_from_image": _write("medium", "component"),
    "rainbond_create_component_from_package": _write("medium", "component"),
    "rainbond_create_component_from_source": _write("medium", "component"),
    "rainbond_create_gateway_rules": _write("medium", "app"),
    "rainbond_create_region": _write("medium", "enterprise"),
    "rainbond_delete_app": _write("high", "app"),
    "rainbond_delete_app_share_record": _write("high", "app"),
    "rainbond_delete_app_version_rollback_record": _write("high", "app"),
    "rainbond_delete_app_version_snapshot": _write("high", "app"),
    "rainbond_delete_component": _write("high", "component"),
    "rainbond_delete_package_upload": _write("low", "component"),
    "rainbond_delete_region": _write("high", "enterprise"),
    "rainbond_deploy_app_upgrade_record": _write("medium", "app"),
    "rainbond_execute_app_upgrade_record": _write("medium", "app"),
    "rainbond_giveup_app_share": _write("low", "app"),
    "rainbond_horizontal_scale_component": _write("medium", "component"),
    "rainbond_init_package_upload": _write("low", "component"),
    "rainbond_install_app_by_market": _write("medium", "app"),
    "rainbond_install_app_model": _write("medium", "app"),
    "rainbond_manage_component_autoscaler": _write("medium", "component"),
    "rainbond_manage_component_connection_envs": _write("medium", "component"),
    "rainbond_manage_component_dependency": _write("medium", "component"),
    "rainbond_manage_component_envs": _write("medium", "component"),
    "rainbond_manage_component_ports": _write("medium", "component"),
    "rainbond_manage_component_probe": _write("medium", "component"),
    "rainbond_manage_component_storage": _write("medium", "component"),
    "rainbond_operate_app": _write("medium", "component"),
    "rainbond_publish_snapshot_to_store": _write("medium", "app"),
    "rainbond_rewrite_snapshot_images": _write("medium", "app"),
    "rainbond_rollback_app_upgrade_record": _write("medium", "app"),
    "rainbond_rollback_app_version_snapshot": _write("medium", "app"),
    "rainbond_start_app_share_event": _write("low", "app"),
    "rainbond_submit_app_share_info": _write("low", "app"),
    "rainbond_update_component_build_source": _write("medium", "component"),
    "rainbond_update_region": _write("medium", "enterprise"),
    "rainbond_upgrade_app": _write("medium", "app"),
    "rainbond_vertical_scale_component": _write("medium", "component"),
}

READ_ONLY_TOOL_NAMES: FrozenSet[str] = frozenset({
    "rainbond_analyze_env_conflicts",
    "rainbond_exec",
    "rainbond_get_app_detail",
    "rainbond_get_app_health_overview",
    "rainbond_get_app_last_upgrade_record",
    "rainbond_get_app_publish_candidates",
    "rainbond_get_app_rollback_records",
    "rainbond_get_app_share_event",
    "rainbond_get_app_share_info",
    "rainbond_get_app_share_record",
    "rainbond_get_app_upgrade_changes",
    "rainbond_get_app_upgrade_detail",
    "rainbond_get_app_upgrade_info",
    "rainbond_get_app_upgrade_record",
    "rainbond_get_app_version_overview",
    "rainbond_get_app_version_rollback_record_detail",
    "rainbond_get_app_version_snapshot_detail",
    "rainbond_get_component_build_logs",
    "rainbond_get_component_build_source",
    "rainbond_get_component_check_result",
    "rainbond_get_component_detail",
    "rainbond_get_component_events",
    "rainbond_get_component_logs",
    "rainbond_get_component_pods",
    "rainbond_get_component_summary",
    "rainbond_get_config_file",
    "rainbond_get_copy_app_info",
    "rainbond_get_current_user",
    "rainbond_get_operation_failure_context",
    "rainbond_get_package_upload_status",
    "rainbond_get_pod_detail",
    "rainbond_get_region_detail",
    "rainbond_get_region_node_detail",
    "rainbond_get_team_apps",
    "rainbond_get_yaml_app_check_result",
    "rainbond_list_app_share_events",
    "rainbond_list_app_share_records",
    "rainbond_list_app_version_rollback_records",
    "rainbond_list_app_version_snapshots",
    "rainbond_query_app_model_versions",
    "rainbond_query_app_monitor",
    "rainbond_query_app_monitor_range",
    "rainbond_query_app_upgrade_records",
    "rainbond_query_apps",
    "rainbond_query_cloud_app_models",
    "rainbond_query_cloud_markets",
    "rainbond_query_components",
    "rainbond_query_enterprises",
    "rainbond_query_local_app_models",
    "rainbond_query_region_nodes",
    "rainbond_query_region_rbd_components",
    "rainbond_query_regions",
    "rainbond_query_teams",
    "rainbond_wait_for_build_completion",
})


def classify_tool(tool_name: str) -> ToolAuditSpec:
    if tool_name in READ_ONLY_TOOL_NAMES:
        return ToolAuditSpec("read", "none", "enterprise")
    return MUTABLE_TOOL_POLICY.get(tool_name, _write("medium", "enterprise"))
