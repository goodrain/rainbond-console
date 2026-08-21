# -*- coding: utf-8 -*-
from typing import Any, List, Tuple

from addict import Dict
from www.models.plugin import PluginBuildVersion, TenantPlugin, TenantServicePluginRelation


def list_plugins_for_service(region: str, tenant_id: str, service_id: str,
                             category: str, include_runtime_resources: bool = False) -> Tuple[List[Any], List[Any]]:
    """Return installed and installable plugins without database-specific joins."""
    plugins = TenantPlugin.objects.filter(tenant_id=tenant_id, region=region)  # type: ignore[attr-defined]
    category_values = _category_values(category)
    if category_values:
        plugins = plugins.filter(category__in=category_values)
    plugin_map = {plugin.plugin_id: plugin for plugin in plugins}

    relations = list(
        TenantServicePluginRelation.objects.filter(service_id=service_id)  # type: ignore[attr-defined]
    )
    installed_plugin_ids = {relation.plugin_id for relation in relations}
    version_plugin_ids = installed_plugin_ids | set(plugin_map)
    versions = PluginBuildVersion.objects.filter(  # type: ignore[attr-defined]
        tenant_id=tenant_id, plugin_id__in=version_plugin_ids).order_by("-ID")
    version_map = {}
    for version in versions:
        version_map.setdefault((version.plugin_id, version.build_version), version)

    installed = []
    for relation in relations:
        plugin = plugin_map.get(relation.plugin_id)
        version = version_map.get((relation.plugin_id, relation.build_version))
        if plugin is None or version is None:
            continue
        row = Dict({
            "plugin_id": plugin.plugin_id,
            "desc": plugin.desc,
            "plugin_alias": plugin.plugin_alias,
            "category": plugin.category,
            "build_version": version.build_version,
            "plugin_status": relation.plugin_status,
        })
        if include_runtime_resources:
            row.origin_share_id = plugin.origin_share_id
            row.min_memory = relation.min_memory
            row.min_cpu = relation.min_cpu
        installed.append(row)

    installable = []
    successful_versions = PluginBuildVersion.objects.filter(  # type: ignore[attr-defined]
        tenant_id=tenant_id, plugin_id__in=set(plugin_map) - installed_plugin_ids,
        build_status="build_success")
    for version in successful_versions:
        plugin = plugin_map.get(version.plugin_id)
        if plugin is None:
            continue
        installable.append(Dict({
            "plugin_id": plugin.plugin_id,
            "desc": plugin.desc,
            "plugin_alias": plugin.plugin_alias,
            "category": plugin.category,
            "build_version": version.build_version,
        }))
    return installed, installable


def _category_values(category: str) -> Tuple[str, ...]:
    if category == "analysis":
        return ("analyst-plugin:perf",)
    if category == "net_manage":
        return ("net-plugin:down", "net-plugin:up", "net-plugin:in-and-out")
    return tuple()
