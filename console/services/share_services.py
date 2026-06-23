# -*- coding: utf-8 -*-
import copy
import datetime
import hashlib
import json
import logging
import os
import re
import time
import requests
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import QuerySet
from console.appstore.appstore import app_store
from console.enum.app import GovernanceModeEnum
from console.enum.component_enum import is_singleton, is_kubeblocks
from console.exception.main import (AbortRequest, RbdAppNotFound, ServiceHandleException)
from console.models.main import (PluginShareRecordEvent, RainbondCenterApp, RainbondCenterAppVersion,
                                 RegionConfig, ServiceShareRecordEvent, ServiceSourceInfo)
from console.repositories.app import app_tag_repo
from console.repositories.app_config import mnt_repo, volume_repo
from console.repositories.app_config_group import (app_config_group_item_repo, app_config_group_repo,
                                                   app_config_group_service_repo)
from console.repositories.component_graph import component_graph_repo
from console.repositories.market_app_repo import (app_export_record_repo, rainbond_app_repo)
from console.repositories.plugin import (app_plugin_relation_repo, plugin_repo, service_plugin_config_repo)
from console.repositories.share_repo import share_repo
from console.repositories.team_repo import team_repo
from console.repositories.app_config import domain_repo, configuration_repo, port_repo
from console.repositories.label_repo import service_label_repo
from console.repositories.label_repo import label_repo
from console.repositories.k8s_attribute import k8s_attribute_repo
from console.repositories.k8s_resources import k8s_resources_repo
from console.services.app import app_market_service
from console.services.app_config import component_service_monitor
from console.services.group_service import group_service
from console.services.plugin import plugin_config_service, plugin_service
from console.services.service_services import base_service
from django.db import transaction
from www.apiclient.baseclient import HttpClient
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceEvent, TenantServiceInfo, make_uuid

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class ShareService(object):
    SNAPSHOT_TEMPLATE_TYPE = "application_version"
    PLATFORM_PLUGIN_NO_INJECT = "NoInject"
    VM_PUBLISH_CLOSED_STATUSES = ("closed", "stopped", "undeploy")

    @classmethod
    def is_snapshot_publish_version(cls, version_obj: Any) -> bool:
        return bool(version_obj and getattr(version_obj, "template_type", None) == cls.SNAPSHOT_TEMPLATE_TYPE)

    def get_snapshot_publish_version(self, share_record: Any) -> Optional[RainbondCenterAppVersion]:
        if not share_record or not share_record.app_id or not share_record.share_version:
            return None
        version = rainbond_app_repo.get_app_version(share_record.app_id, share_record.share_version)
        if not self.is_snapshot_publish_version(version):
            return None
        return version

    def is_snapshot_publish_record(self, share_record: Any) -> bool:
        return bool(self.get_snapshot_publish_version(share_record))

    @staticmethod
    def _is_vm_runtime_service(service: Any) -> bool:
        return getattr(service, "extend_method", "") == "vm" or getattr(service, "service_source", "") == "vm_run"

    def check_service_source(self, team: Any, team_name: str, group_id: str, region_name: str) -> dict:
        service_list = share_repo.get_service_list_by_group_id(team=team, group_id=group_id)
        # 过滤掉 kubeblocks 类型的组件
        service_list = [s for s in service_list if not is_kubeblocks(s.extend_method)]
        k8s_resources_list = k8s_resources_repo.list_by_app_id(group_id)
        data = {"code": 400, "success": False, "msg_show": "当前应用内无组件和k8s资源", "list": list(), "bean": dict()}
        if k8s_resources_list:
            data = {"code": 200, "success": True, "msg_show": "应用可以发布。", "list": list(), "bean": dict()}
        if service_list:
            vm_services = [service for service in service_list if self._is_vm_runtime_service(service)]
            if not vm_services:
                return {"code": 200, "success": True, "msg_show": "应用可以发布。", "list": list(), "bean": dict()}
            # VM publish still requires an explicit shutdown state before exporting the root disk.
            service_ids = [service.service_id for service in vm_services]
            status_list = base_service.status_multi_service(
                region=region_name, tenant_name=team_name, service_ids=service_ids, enterprise_id=team.enterprise_id)
            status_map = {status.get("service_id"): status.get("status") for status in status_list}
            for vm_service in vm_services:
                if status_map.get(vm_service.service_id, "") not in self.VM_PUBLISH_CLOSED_STATUSES:
                    return {
                        "code": 400,
                        "success": False,
                        "msg_show": "虚拟机发布前必须关机，请先关闭虚拟机组件后再发布。",
                        "list": list(),
                        "bean": dict()
                    }
            data = {"code": 200, "success": True, "msg_show": "应用可以发布。", "list": list(), "bean": dict()}
        return data

    def get_service_ports_by_ids(self, service_ids: list) -> dict:
        """
        根据多个组件ID查询组件的端口信息
        :param service_ids: 组件ID列表
        :return: {"service_id":TenantServicesPort[object]}
        """
        port_list = share_repo.get_port_list_by_service_ids(service_ids=service_ids)
        if port_list:
            service_port_map: Dict[Any, list] = {}
            for port in port_list:
                service_id = port.service_id
                tmp_list: list = []
                if service_id in list(service_port_map.keys()):
                    tmp_list = service_port_map[service_id]
                tmp_list.append(port)
                service_port_map[service_id] = tmp_list
            return service_port_map
        else:
            return {}

    def get_service_dependencys_by_ids(self, service_ids: list) -> dict:
        """
        根据多个组件ID查询组件的依赖组件信息
        :param service_ids:组件ID列表
        :return: {"service_id":TenantServiceInfo[object]}
        """
        relation_list = share_repo.get_relation_list_by_service_ids(service_ids=service_ids)
        if relation_list:
            relation_list_service_ids = relation_list.values_list("service_id", flat=True)
            dep_service_map: Dict[Any, list] = {service_id: [] for service_id in relation_list_service_ids}
            for dep_service in relation_list:
                dep_service_info = TenantServiceInfo.objects.filter(
                    service_id=dep_service.dep_service_id, tenant_id=dep_service.tenant_id).first()
                if dep_service_info is None:
                    continue
                dep_service_map[dep_service.service_id].append(dep_service_info)
            return dep_service_map
        else:
            return {}

    @staticmethod
    def list_service_monitors(tenant_id: str, service_ids: list) -> dict:
        monitors = component_service_monitor.list_by_service_ids(tenant_id, service_ids)
        result: Dict[Any, Any] = {}
        for monitor in monitors:
            if not result.get(monitor.service_id):
                result[monitor.service_id] = []
            m = monitor.to_dict()
            del m["ID"]
            result[monitor.service_id].append(m)
        return result

    @staticmethod
    def list_component_graphs(component_ids: list) -> dict:
        graphs = component_graph_repo.list_by_component_ids(component_ids)
        result: Dict[Any, Any] = {}
        for graph in graphs:
            if not result.get(graph.component_id):
                result[graph.component_id] = []
            g = graph.to_dict()
            del g["ID"]
            result[graph.component_id].append(g)
        return result

    @staticmethod
    def list_component_labels(component_ids: list) -> dict:
        component_labels = service_label_repo.list_by_component_ids(component_ids)
        labels = label_repo.list_by_label_ids([label.label_id for label in component_labels])
        labels = {label.label_id: label for label in labels}

        res: Dict[Any, Any] = {}
        for component_label in component_labels:
            clabels = res.get(component_label.service_id, {})
            label = labels.get(component_label.label_id)
            if not label:
                logger.warning("component id: {}; label id: {}; label not found".format(component_label.service_id,
                                                                                        component_label.label_id))
                continue
            clabels[label.label_name] = label.label_alias
            res[component_label.service_id] = clabels
        return res

    def get_dep_mnts_by_ids(self, tenant_id: str, service_ids: list) -> dict:
        mnt_relations = mnt_repo.list_mnt_relations_by_service_ids(tenant_id, service_ids)
        if not mnt_relations:
            return {}
        result: Dict[Any, list] = {}
        for mnt_relation in mnt_relations:
            service_id = mnt_relation.service_id
            if service_id in list(result.keys()):
                values = result[service_id]
            else:
                values = []
                result[service_id] = values
            values.append(mnt_relation)

        return result

    def get_service_env_by_ids(self, service_ids: list) -> dict:
        """
        获取组件env
        :param service_ids: 组件ID列表
        # :return: 可修改的环境变量service_env_change_map，不可修改的环境变量service_env_nochange_map
        :return: 环境变量service_env_map
        """
        env_list = share_repo.get_env_list_by_service_ids(service_ids=service_ids)
        if env_list:
            service_env_map: Dict[Any, list] = {}
            for env in env_list:
                if env.scope == "build":
                    continue
                service_id = env.service_id
                tmp_list: list = []
                if service_id in list(service_env_map.keys()):
                    tmp_list = service_env_map[service_id]
                tmp_list.append(env)
                service_env_map[service_id] = tmp_list
            return service_env_map
        else:
            return {}

    def get_service_volume_by_ids(self, service_ids: list) -> dict:
        """
        获取组件持久化目录
        """
        volume_list = share_repo.get_volume_list_by_service_ids(service_ids=service_ids)
        if volume_list:
            service_volume_map: Dict[Any, list] = {}
            for volume in volume_list:
                service_id = volume.service_id
                tmp_list: list = []
                if service_id in list(service_volume_map.keys()):
                    tmp_list = service_volume_map[service_id]
                tmp_list.append(volume)
                service_volume_map[service_id] = tmp_list
            return service_volume_map
        else:
            return {}

    def get_service_probes(self, service_ids: list) -> dict:
        """
        获取组件健康检测探针
        """
        probe_list = share_repo.get_probe_list_by_service_ids(service_ids=service_ids)
        if probe_list:
            service_probe_map: Dict[Any, list] = {}
            for probe in probe_list:
                service_id = probe.service_id
                tmp_list: list = []
                if service_id in list(service_probe_map.keys()):
                    tmp_list = service_probe_map[service_id]
                tmp_list.append(probe)
                service_probe_map[service_id] = tmp_list
            return service_probe_map
        else:
            return {}

    def get_team_service_deploy_version(self, region: str, team: Any, service_ids: list) -> Optional[dict]:
        try:
            res, body = region_api.get_team_services_deploy_version(region, team.tenant_name, {"service_ids": service_ids})
            if res.status == 200:
                service_versions: Dict[Any, Any] = {}
                # NOTE: region body is Optional[Dict]; index guarded by the surrounding try/except.
                for version in body["list"]:  # type: ignore[index]
                    if version and "service_id" in version and "build_version" in version:
                        service_versions[version["service_id"]] = version["build_version"]
                return service_versions
        except Exception as e:
            logger.exception(e)
        logger.debug("======>get services deploy version failure")
        return None

    def query_share_service_info(self, team: Any, group_id: Any, scope: Optional[str] = None) -> list:
        service_list = share_repo.get_service_list_by_group_id(team=team, group_id=group_id)
        # 过滤掉 kubeblocks 类型的组件
        service_list = [s for s in service_list if not is_kubeblocks(s.extend_method)]
        if service_list:
            array_ids = [x.service_id for x in service_list]
            deploy_versions = self.get_team_service_deploy_version(service_list[0].service_region, team, array_ids)
            array_keys = []
            for x in service_list:
                if x.service_key == "application" or x.service_key == "0000" or x.service_key == "":
                    array_keys.append(x.service_key)
            # 查询组件端口信息
            service_port_map = self.get_service_ports_by_ids(array_ids)
            # 查询组件依赖
            dep_service_map = self.get_service_dependencys_by_ids(array_ids)
            service_env_map = self.get_service_env_by_ids(array_ids)
            # 查询组件持久化信息
            service_volume_map = self.get_service_volume_by_ids(array_ids)
            # dependent volume
            dep_mnt_map = self.get_dep_mnts_by_ids(team.tenant_id, array_ids)
            # 获取组件的健康检测设置
            probe_map = self.get_service_probes(array_ids)

            # service monitor
            sid_2_monitors = self.list_service_monitors(team.tenant_id, array_ids)
            # component graphs
            sid_2_graphs = self.list_component_graphs(array_ids)
            # component k8s attributes
            sid_2_k8s_attrs = self.list_component_k8s_attributes(array_ids)

            all_data_map = dict()

            labels = self.list_component_labels(array_ids)

            for service in service_list:
                if not deploy_versions or not deploy_versions.get(service.service_id):
                    continue
                data = dict()
                data['service_id'] = service.service_id
                data['tenant_id'] = service.tenant_id
                data['service_cname'] = service.service_cname
                # The component is redistributed without the key from the installation source, which would cause duplication.
                # service_id  can be thought of as following a component lifecycle.
                data['service_key'] = service.service_id
                # service_share_uuid The build policy cannot be changed
                data["service_share_uuid"] = "{0}+{1}".format(data['service_key'], data['service_id'])
                data['need_share'] = True
                data['category'] = service.category
                data['language'] = service.language
                data['extend_method'] = service.extend_method
                data['version'] = service.version
                data['memory'] = service.min_memory - service.min_memory % 32
                data['service_type'] = service.service_type
                data['service_source'] = service.service_source
                data['k8s_component_name'] = service.k8s_component_name
                data['deploy_version'] = deploy_versions[data['service_id']] if deploy_versions else service.deploy_version
                data['image'] = service.image
                data['git_url'] = service.git_url
                data['arch'] = service.arch
                data['service_alias'] = service.service_alias
                data['service_name'] = service.service_name
                data['service_region'] = service.service_region
                data['creater'] = service.creater
                data["cmd"] = service.cmd
                data['probes'] = [probe.to_dict() for probe in probe_map.get(service.service_id, [])]
                e_m = dict()
                e_m['min_memory'] = 0 if service.min_memory == 0 else 64
                e_m['init_memory'] = service.min_memory
                e_m['max_memory'] = 65536
                e_m['step_memory'] = 64
                e_m['is_restart'] = 0
                e_m['container_cpu'] = service.min_cpu
                e_m['step_node'] = 1
                e_m['min_node'] = service.min_node
                if is_singleton(service.extend_method):
                    e_m['max_node'] = 1
                else:
                    e_m['max_node'] = 64
                data['extend_method_map'] = e_m
                data['port_map_list'] = list()
                if service_port_map.get(service.service_id):
                    for port in service_port_map.get(service.service_id) or []:
                        p = dict()
                        # 写需要返回的port数据
                        p['protocol'] = port.protocol
                        p['tenant_id'] = port.tenant_id
                        p['port_alias'] = port.port_alias
                        p['container_port'] = port.container_port
                        p['is_inner_service'] = port.is_inner_service
                        p['is_outer_service'] = port.is_outer_service
                        p['k8s_service_name'] = port.k8s_service_name
                        p['name'] = port.name
                        data['port_map_list'].append(p)

                data['service_volume_map_list'] = list()
                if service_volume_map.get(service.service_id):
                    for volume in service_volume_map.get(service.service_id) or []:
                        s_v = dict()
                        s_v['file_content'] = ''
                        if volume.volume_type == "config-file":
                            config_file = volume_repo.get_service_config_file(volume)
                            if config_file:
                                s_v['file_content'] = config_file.file_content
                        s_v['category'] = volume.category
                        s_v['volume_capacity'] = volume.volume_capacity
                        s_v['volume_provider_name'] = volume.volume_provider_name
                        s_v['volume_type'] = volume.volume_type
                        s_v['volume_path'] = volume.volume_path
                        s_v['volume_name'] = volume.volume_name
                        s_v['access_mode'] = volume.access_mode
                        s_v['share_policy'] = volume.share_policy
                        s_v['backup_policy'] = volume.backup_policy
                        s_v['mode'] = volume.mode
                        data['service_volume_map_list'].append(s_v)

                data['service_env_map_list'] = list()
                data['service_connect_info_map_list'] = list()
                if service_env_map.get(service.service_id):
                    for env_change in service_env_map.get(service.service_id) or []:
                        e_c = dict()
                        e_c['name'] = env_change.name
                        e_c['attr_name'] = env_change.attr_name
                        e_c['attr_value'] = env_change.attr_value
                        e_c['is_change'] = env_change.is_change
                        if env_change.scope == "outer":
                            data['service_connect_info_map_list'].append(e_c)
                            e_c['container_port'] = env_change.container_port
                        else:
                            data['service_env_map_list'].append(e_c)

                data['service_related_plugin_config'] = list()
                plugins_relation_list = share_repo.get_plugins_relation_by_service_ids(service_ids=[service.service_id])
                for spr in plugins_relation_list:
                    service_plugin_config_var = service_plugin_config_repo.get_service_plugin_config_var(
                        spr.service_id, spr.plugin_id, spr.build_version)
                    plugin_data = spr.to_dict()
                    plugin_data["attr"] = [var.to_dict() for var in service_plugin_config_var]
                    data['service_related_plugin_config'].append(plugin_data)
                # component monitor
                data["component_monitors"] = sid_2_monitors.get(service.service_id, None)
                data["component_graphs"] = sid_2_graphs.get(service.service_id, None)
                data["labels"] = labels.get(service.component_id, {})
                data["component_k8s_attributes"] = sid_2_k8s_attrs.get(service.service_id, None)
                vm_publish_metadata = self._build_vm_publish_metadata(data)
                if vm_publish_metadata:
                    data["service_type"] = "vm"
                    data["vm"] = vm_publish_metadata
                elif data.get("service_type") == "vm":
                    data["service_type"] = "application"

                all_data_map[service.service_id] = data

            all_data = list()
            for service_id in all_data_map:
                service = all_data_map[service_id]
                service['dep_service_map_list'] = list()
                if dep_service_map.get(service['service_id']):
                    for dep in dep_service_map[service['service_id']]:
                        d = dict()
                        if all_data_map.get(dep.service_id):
                            # 通过service_key和service_id来判断依赖关系
                            d['dep_service_key'] = all_data_map[dep.service_id]["service_share_uuid"]
                            service['dep_service_map_list'].append(d)

                service["mnt_relation_list"] = list()

                if dep_mnt_map.get(service_id):
                    for dep_mnt in dep_mnt_map.get(service_id) or []:
                        if not all_data_map.get(dep_mnt.dep_service_id):
                            continue
                        service["mnt_relation_list"].append({
                            "service_share_uuid":
                            all_data_map[dep_mnt.dep_service_id]["service_share_uuid"],
                            "mnt_name":
                            dep_mnt.mnt_name,
                            "mnt_dir":
                            dep_mnt.mnt_dir
                        })
                all_data.append(service)
            return all_data
        else:
            return []

    def service_last_share_cache(self, service_info: Any, last_share_info: Any) -> Any:
        if service_info:
            if isinstance(service_info, dict):
                service_info.update(last_share_info)
            elif isinstance(service_info, list):
                for i in range(len(service_info)):
                    for last_info in last_share_info:
                        if not service_info[i].get("attr_name"):
                            service_info[i].update(last_info)
                            continue
                        if service_info[i].get("attr_name") and service_info[i]["attr_name"] == last_info["attr_name"]:
                            service_info[i] = last_info
                            continue
        return service_info

    # 查询应用内使用的插件列表
    def query_group_service_plugin_list(self, team: Any, group_id: str) -> list:
        service_list = share_repo.get_service_list_by_group_id(team=team, group_id=group_id)
        # 过滤掉 kubeblocks 类型的组件
        service_list = [s for s in service_list if not is_kubeblocks(s.extend_method)]
        if service_list:
            service_ids = [x.service_id for x in service_list]
            plugins = plugin_service.get_plugins_by_service_ids(service_ids)
            # 默认插件分享
            for p in plugins:
                p["is_share"] = True
            return plugins
        else:
            return []

    def get_group_services_used_plugins(self, group_id: Any) -> list:
        service_list = group_service.get_group_services(group_id)
        if not service_list:
            return []
        service_ids = [x.service_id for x in service_list]
        sprs = app_plugin_relation_repo.get_service_plugin_relations_by_service_ids(service_ids)
        plugin_list = []
        temp_plugin_ids = []
        for spr in sprs:
            if spr.plugin_id in temp_plugin_ids:
                continue
            tenant_plugin = plugin_repo.get_plugin_by_plugin_ids([spr.plugin_id])[0]
            plugin_dict = tenant_plugin.to_dict()

            plugin_dict["build_version"] = spr.build_version
            plugin_list.append(plugin_dict)
            temp_plugin_ids.append(spr.plugin_id)
        return plugin_list

    def get_k8s_resources(self, app_id: Any) -> Any:
        return k8s_resources_repo.list_available_resources(app_id).values()

    def wrapper_service_plugin_config(self, service_related_plugin_config: list, shared_plugin_info: Any) -> list:
        """添加plugin key信息"""
        id_key_map = {}
        if shared_plugin_info:
            id_key_map = {i["plugin_id"]: i["plugin_key"] for i in shared_plugin_info}

        service_plugin_config_list = []
        for config in service_related_plugin_config:
            config["plugin_key"] = id_key_map.get(config["plugin_id"])
            service_plugin_config_list.append(config)
        return service_plugin_config_list

    def create_basic_app_info(self, **kwargs: Any) -> RainbondCenterApp:
        return rainbond_app_repo.add_basic_app_info(**kwargs)

    def create_publish_event(self, record_event: Any, user_name: str, event_type: str) -> ServiceEvent:
        import datetime
        event = ServiceEvent(
            event_id=make_uuid(),
            service_id=record_event.service_id,
            tenant_id=record_event.team_id,
            type=event_type,
            user_name=user_name,
            start_time=datetime.datetime.now())
        event.save()
        return event

    @staticmethod
    def normalize_platform_plugin_positions(positions: Any) -> list:
        normalized_positions = []
        for position in positions or []:
            if not position:
                continue
            if position == ShareService.PLATFORM_PLUGIN_NO_INJECT:
                return []
            if position not in normalized_positions:
                normalized_positions.append(position)
        return normalized_positions

    @staticmethod
    def _build_platform_plugin_config(share_version_info: dict) -> Optional[dict]:
        if not share_version_info.get("is_platform_plugin", False):
            return None
        return {
            "is_platform_plugin": True,
            "plugin_id": share_version_info.get("plugin_id", ""),
            "plugin_name": share_version_info.get("plugin_name", ""),
            "plugin_type": share_version_info.get("plugin_type", ""),
            "frontend_component": share_version_info.get("frontend_component", ""),
            "entry_path": share_version_info.get("entry_path", ""),
            "inject_position": ShareService.normalize_platform_plugin_positions(
                share_version_info.get("inject_position", [])
            ),
            "menu_title": share_version_info.get("menu_title", ""),
            "route_path": share_version_info.get("route_path", ""),
        }

    def _build_publish_template_from_snapshot(self, snapshot_template: dict, app_model_id: str, app_model_name: str,
                                              version: str, governance_mode: str,
                                              share_version_info: dict) -> dict:
        app_template = copy.deepcopy(snapshot_template)
        app_template["template_version"] = self._resolve_publish_template_version(app_template.get("apps", []))
        app_template["group_key"] = app_model_id
        app_template["group_name"] = app_model_name
        app_template["group_version"] = version
        app_template["group_dev_status"] = ""
        app_template["governance_mode"] = governance_mode
        app_template["k8s_resources"] = copy.deepcopy(snapshot_template.get("k8s_resources", []))
        app_template["app_config_groups"] = copy.deepcopy(snapshot_template.get("app_config_groups", []))
        app_template["ingress_http_routes"] = copy.deepcopy(snapshot_template.get("ingress_http_routes", []))
        app_template["plugins"] = copy.deepcopy(snapshot_template.get("plugins", []))
        app_template["apps"] = copy.deepcopy(snapshot_template.get("apps", []))

        platform_plugin = self._build_platform_plugin_config(share_version_info)
        if platform_plugin:
            app_template["platform_plugin"] = platform_plugin
        else:
            app_template.pop("platform_plugin", None)
        return app_template

    @staticmethod
    def _apply_image_delivery(service: dict, image_info: Any) -> None:
        service["service_image"] = image_info
        service["share_type"] = "image"
        service.pop("service_slug", None)
        service.pop("share_slug_path", None)

    @staticmethod
    def _load_json_value(value: Any, default: Any) -> Any:
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return default

    @classmethod
    def _extract_vm_attr_value(cls, service: dict, attr_name: str, default: Any = None) -> Any:
        attrs = service.get("component_k8s_attributes") or []
        for attr in attrs:
            if attr.get("name") != attr_name:
                continue
            value = attr.get("attribute_value")
            if attr.get("save_type") == "json":
                return cls._load_json_value(value, default if default is not None else {})
            return value if value not in (None, "") else default
        return default

    @classmethod
    def _build_vm_publish_metadata(cls, service: dict) -> Optional[dict]:
        if service.get("extend_method") != "vm":
            return None
        boot_mode = cls._extract_vm_attr_value(service, "vm_boot_mode", "") or ""
        boot_source_format = cls._extract_vm_attr_value(service, "vm_boot_source_format", "") or ""
        disk_layout = cls._extract_vm_attr_value(service, "vm_disk_layout", []) or []
        if not isinstance(disk_layout, list):
            disk_layout = []
        root_image = service.get("share_image") or service.get("image") or ""
        fallback_root_source = service.get("git_url", "") or ""
        volume_capacity_map = {}
        for volume in service.get("service_volume_map_list", []) or []:
            if not isinstance(volume, dict):
                continue
            volume_name = volume.get("volume_name")
            if not volume_name:
                continue
            volume_capacity_map[str(volume_name)] = volume.get("volume_capacity")
        normalized_layout = []
        for index, disk in enumerate(disk_layout):
            if not isinstance(disk, dict):
                continue
            item = dict(disk)
            if item.get("disk_role") == "root":
                item["image"] = item.get("image") or root_image
                item["source_uri"] = item.get("source_uri") or fallback_root_source
                item["source_type"] = "http-artifact"
                item["format"] = item.get("format") or boot_source_format
            volume_name = str(item.get("volume_name") or item.get("disk_key") or "")
            if not item.get("request_size") and volume_capacity_map.get(volume_name):
                item["request_size"] = "{}Gi".format(volume_capacity_map[volume_name])
            item["order_index"] = item.get("order_index", index)
            normalized_layout.append(item)
        if not normalized_layout:
            root_capacity = volume_capacity_map.get("disk")
            normalized_layout = [{
                "disk_key": "disk",
                "disk_name": "system-disk",
                "disk_role": "root",
                "device_type": "disk",
                "order_index": 0,
                "volume_name": "disk",
                "request_size": "{}Gi".format(root_capacity) if root_capacity else "",
                "format": boot_source_format,
                "source_type": "http-artifact",
                "image": root_image,
                "source_uri": fallback_root_source,
                "checksum": "",
            }]
        return {
            "boot_mode": boot_mode,
            "machine_type": "",
            "boot_source_format": boot_source_format,
            "disk_layout": normalized_layout,
        }

    @classmethod
    def _sync_vm_root_disk_image(cls, service: dict, image_name: str) -> None:
        vm = service.get("vm")
        if not isinstance(vm, dict):
            return
        disk_layout = vm.get("disk_layout") or []
        for disk in disk_layout:
            if not isinstance(disk, dict):
                continue
            if str(disk.get("disk_role", "")).lower() == "root":
                disk["image"] = image_name
                disk["source_type"] = "http-artifact"
                return

    @staticmethod
    def _extract_vm_root_source_uri(service: dict) -> str:
        vm = service.get("vm")
        if not isinstance(vm, dict):
            return service.get("git_url", "") or ""
        for disk in vm.get("disk_layout") or []:
            if not isinstance(disk, dict):
                continue
            if str(disk.get("disk_role", "")).lower() == "root":
                return disk.get("source_uri") or service.get("git_url", "") or ""
        return service.get("git_url", "") or ""

    @staticmethod
    def _is_vm_publish_component(service: Any) -> bool:
        return bool(
            isinstance(service, dict) and (
                service.get("vm")
                or service.get("extend_method") == "vm"
                or service.get("service_source") == "vm_run"
            )
        )

    @staticmethod
    def _is_existing_vm_export_source(source_uri: Any) -> bool:
        source_uri = str(source_uri or "").strip().lower()
        return source_uri.startswith(("http://", "https://")) and "/volumes/" in source_uri and "disk.img" in source_uri

    @staticmethod
    def _sync_vm_root_disk_source_uri(service: dict, source_uri: str) -> None:
        vm = service.get("vm")
        if not isinstance(vm, dict):
            return
        for disk in vm.get("disk_layout") or []:
            if not isinstance(disk, dict):
                continue
            if str(disk.get("disk_role", "")).lower() == "root":
                disk["source_uri"] = source_uri
                disk["source_type"] = disk.get("source_type") or "registry"
                return

    @staticmethod
    def _normalize_vm_export_name(value: Any) -> str:
        export_name = re.sub(r"[^a-z0-9-]+", "-", str(value or "").lower()).strip("-")
        if not export_name:
            export_name = "vm-root-export"
        if len(export_name) > 48:
            export_name = export_name[:48].strip("-")
        return export_name or "vm-root-export"

    def _prepare_vm_publish_image_source(self, region_name: str, tenant_name: str, service: dict, record_event: Any,
                                         wait_seconds: int = 60, interval_seconds: int = 2,
                                         force_export: bool = False) -> Tuple[str, str]:
        source_uri = self._extract_vm_root_source_uri(service)
        if not self._is_vm_publish_component(service):
            return source_uri, ""
        logger.info(
            "[vm-publish] prepare vm image source: record_id=%s service_id=%s service_key=%s service_alias=%s "
            "source_uri_present=%s force_export=%s",
            getattr(record_event, "record_id", None),
            getattr(record_event, "service_id", None) or service.get("service_id"),
            getattr(record_event, "service_key", None) or service.get("service_key"),
            getattr(record_event, "service_alias", None) or service.get("service_alias"),
            bool(source_uri),
            force_export,
        )
        if self._is_existing_vm_export_source(source_uri) and not force_export:
            logger.info(
                "[vm-publish] reuse existing vm export source: record_id=%s service_alias=%s",
                getattr(record_event, "record_id", None),
                getattr(record_event, "service_alias", None) or service.get("service_alias"),
            )
            return source_uri, ""

        service_alias = getattr(record_event, "service_alias", None) or service.get("service_alias")
        if not service_alias:
            raise ServiceHandleException(msg="vm export failed", msg_show="虚拟机组件缺少服务别名，无法导出系统盘", status_code=500)
        export_seed = getattr(record_event, "service_id", None) or service.get("service_id") or service_alias
        export_name = self._normalize_vm_export_name("vm-root-{}".format(export_seed))

        logger.info(
            "[vm-publish] create vm export request: record_id=%s region=%s tenant=%s service_alias=%s export_name=%s",
            getattr(record_event, "record_id", None),
            region_name,
            tenant_name,
            service_alias,
            export_name,
        )
        _, body = region_api.create_vm_export(region_name, tenant_name, service_alias, {
            "name": export_name,
            "description": "publish vm root disk",
        })
        bean = body.get("bean", {}) if isinstance(body, dict) else {}
        download_url = bean.get("download_url") or bean.get("downloadUrl") or ""
        download_token = bean.get("download_token") or bean.get("downloadToken") or ""
        logger.info(
            "[vm-publish] create vm export response: record_id=%s service_alias=%s export_name=%s phase=%s "
            "has_download_url=%s",
            getattr(record_event, "record_id", None),
            service_alias,
            export_name,
            bean.get("phase", ""),
            bool(download_url),
        )
        if download_url:
            self._sync_vm_root_disk_source_uri(service, download_url)
            return download_url, download_token

        logger.info(
            "[vm-publish] wait vm export ready: record_id=%s service_alias=%s export_name=%s wait_seconds=%s "
            "interval_seconds=%s",
            getattr(record_event, "record_id", None),
            service_alias,
            export_name,
            wait_seconds,
            interval_seconds,
        )
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            time.sleep(interval_seconds)
            _, body = region_api.get_vm_export(region_name, tenant_name, service_alias, export_name)
            bean = body.get("bean", {}) if isinstance(body, dict) else {}
            download_url = bean.get("download_url") or bean.get("downloadUrl") or ""
            download_token = bean.get("download_token") or bean.get("downloadToken") or ""
            logger.info(
                "[vm-publish] poll vm export: record_id=%s service_alias=%s export_name=%s phase=%s "
                "has_download_url=%s",
                getattr(record_event, "record_id", None),
                service_alias,
                export_name,
                bean.get("phase", ""),
                bool(download_url),
            )
            if download_url:
                logger.info(
                    "[vm-publish] vm export ready: record_id=%s service_alias=%s export_name=%s",
                    getattr(record_event, "record_id", None),
                    service_alias,
                    export_name,
                )
                self._sync_vm_root_disk_source_uri(service, download_url)
                return download_url, download_token

        logger.warning(
            "[vm-publish] vm export wait timeout: record_id=%s service_alias=%s export_name=%s wait_seconds=%s",
            getattr(record_event, "record_id", None),
            service_alias,
            export_name,
            wait_seconds,
        )
        raise ServiceHandleException(msg="vm export not ready", msg_show="虚拟机系统盘导出未就绪，请稍后重试", status_code=500)

    @staticmethod
    def _resolve_publish_template_version(services: Any) -> str:
        for service in services or []:
            if not isinstance(service, dict):
                continue
            if service.get("vm") or service.get("extend_method") == "vm" or service.get("service_source") == "vm_run":
                return "v3"
        return "v2"

    @staticmethod
    def _apply_slug_delivery(service: dict, slug_info: Any) -> None:
        service["service_slug"] = slug_info
        service["share_type"] = "slug"
        service.pop("service_image", None)
        service.pop("share_image", None)

    @transaction.atomic
    def sync_event(self, user: Any, region_name: str, tenant_name: str, record_event: Any) -> Any:
        app_version = rainbond_app_repo.get_rainbond_app_version_by_record_id(record_event.record_id)
        if not app_version:
            raise RbdAppNotFound("分享的应用不存在")
        event_type = "share-yb"
        # NOTE: scope is an Optional[str] model field; .startswith assumes it is set.
        if app_version.scope.startswith("goodrain"):  # type: ignore[union-attr]
            event_type = "share-ys"
        event = self.create_publish_event(record_event, user.nick_name, event_type)
        record_event.event_id = event.event_id
        app_templetes = json.loads(app_version.app_template)
        force_vm_export = not self.is_snapshot_publish_version(app_version)
        apps = app_templetes.get("apps", None)
        if not apps:
            raise ServiceHandleException(msg="get share app info failed", msg_show="分享的应用信息获取失败", status_code=500)
        logger.info(
            "[vm-publish] sync share event start: record_id=%s local_event_id=%s service_id=%s service_key=%s "
            "service_alias=%s app_version=%s scope=%s force_vm_export=%s",
            record_event.record_id,
            record_event.ID,
            record_event.service_id,
            record_event.service_key,
            record_event.service_alias,
            app_version.version,
            app_version.scope,
            force_vm_export,
        )
        new_apps = list()
        sid = transaction.savepoint()
        try:
            for app in apps:
                # 处理事件的应用
                if app["service_key"] == record_event.service_key:
                    image_info = copy.deepcopy(app.get("service_image", None))
                    if isinstance(image_info, dict) and self._is_vm_publish_component(app):
                        logger.info(
                            "[vm-publish] detected vm publish component: record_id=%s service_id=%s "
                            "service_key=%s service_alias=%s",
                            record_event.record_id,
                            app.get("service_id"),
                            app.get("service_key"),
                            app.get("service_alias"),
                        )
                        vm_image_source, vm_image_token = self._prepare_vm_publish_image_source(
                            region_name, tenant_name, app, record_event, force_export=force_vm_export)
                        if vm_image_source:
                            image_info["vm_image_source"] = vm_image_source
                        if vm_image_token:
                            image_info["vm_image_token"] = vm_image_token
                    body = {
                        "service_key": app["service_key"],
                        "app_version": app_version.version,
                        "deploy_version": app.get("deploy_version", ""),
                        "arch": app.get("arch", "amd64"),
                        "event_id": event.event_id,
                        "share_user": user.nick_name,
                        "share_scope": app_version.scope,
                        "image_info": image_info,
                        "slug_info": app.get("service_slug", None)
                    }
                    re_body = None
                    try:
                        logger.info(
                            "[vm-publish] call region share_service: record_id=%s service_alias=%s "
                            "is_vm=%s has_image_info=%s has_vm_image_source=%s has_slug_info=%s",
                            record_event.record_id,
                            record_event.service_alias,
                            self._is_vm_publish_component(app),
                            bool(image_info),
                            isinstance(image_info, dict) and bool(image_info.get("vm_image_source")),
                            bool(body.get("slug_info")),
                        )
                        res, re_body = region_api.share_service(region_name, tenant_name, record_event.service_alias, body)
                        # NOTE: region body is Optional[Dict]; unguarded .get is a potential latent
                        # None-bug, though wrapped by the surrounding try/except.
                        bean = re_body.get("bean")  # type: ignore[union-attr]
                        if bean:
                            record_event.region_share_id = bean.get("share_id", None)
                            record_event.event_id = bean.get("event_id", None)
                            record_event.event_status = "start"
                            record_event.update_time = datetime.datetime.now()
                            record_event.save()
                            image_name = bean.get("image_name", None)
                            logger.info(
                                "[vm-publish] region share_service accepted: record_id=%s service_alias=%s "
                                "region_share_id=%s region_event_id=%s status=%s has_image_name=%s has_slug_path=%s",
                                record_event.record_id,
                                record_event.service_alias,
                                record_event.region_share_id,
                                record_event.event_id,
                                record_event.event_status,
                                bool(image_name),
                                bool(bean.get("slug_path", None)),
                            )
                            if image_name:
                                app["share_image"] = image_name
                                self._sync_vm_root_disk_image(app, image_name)
                                app.pop("share_slug_path", None)
                            slug_path = bean.get("slug_path", None)
                            if slug_path:
                                app["share_slug_path"] = slug_path
                                app.pop("share_image", None)
                            new_apps.append(app)
                        else:
                            transaction.savepoint_rollback(sid)
                            raise ServiceHandleException(msg="share failed", msg_show="数据中心分享错误")
                    except region_api.CallApiFrequentError as e:
                        logger.exception(e)
                        transaction.savepoint_rollback(sid)
                        raise ServiceHandleException(msg="wait a moment please", msg_show="操作过于频繁，请稍后再试", status_code=409)
                    except Exception as e:
                        logger.exception(e)
                        transaction.savepoint_rollback(sid)
                        if re_body:
                            logger.error(re_body)
                        raise ServiceHandleException(msg="share failed", msg_show="数据中心分享错误", status_code=500)
                else:
                    new_apps.append(app)
            app_templetes["apps"] = new_apps
            app_version.app_template = json.dumps(app_templetes)
            app_version.update_time = datetime.datetime.now()
            app_version.save()
            transaction.savepoint_commit(sid)
            return record_event
        except ServiceHandleException as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            raise e
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            raise ServiceHandleException(msg="share failed", msg_show="应用分享介质同步发生错误", status_code=500)

    @transaction.atomic
    def sync_service_plugin_event(self, user: Any, region_name: str, tenant_name: str, record_id: str,
                                  record_event: Any) -> Any:
        apps_version = rainbond_app_repo.get_rainbond_app_version_by_record_id(record_event.record_id)
        if not apps_version:
            raise RbdAppNotFound("分享的应用不存在")
        app_template = json.loads(apps_version.app_template)
        if "plugins" not in app_template:
            return
        plugins_info = app_template["plugins"]
        plugin_list = []
        for plugin in plugins_info:
            if record_event.plugin_id == plugin["plugin_id"]:
                event_id = make_uuid()
                body = {
                    "plugin_id": plugin["plugin_id"],
                    "plugin_version": plugin["build_version"],
                    "plugin_key": plugin["plugin_key"],
                    "event_id": event_id,
                    "share_user": user.nick_name,
                    "share_scope": apps_version.scope,
                    "image_info": plugin.get("plugin_image") if plugin.get("plugin_image") else {},
                }
                sid = transaction.savepoint()
                try:
                    res, re_body = region_api.share_plugin(region_name, tenant_name, plugin["plugin_id"], body)
                    # NOTE: region body is Optional[Dict]; unguarded .get is a potential latent
                    # None-bug, though wrapped by the surrounding try/except.
                    data = re_body.get("bean")  # type: ignore[union-attr]
                    if not data:
                        transaction.savepoint_rollback(sid)
                        raise ServiceHandleException(msg="share failed", msg_show="数据中心分享错误")

                    record_event.region_share_id = data.get("share_id", None)
                    record_event.event_id = data.get("event_id", None)
                    record_event.event_status = "start"
                    record_event.update_time = datetime.datetime.now()
                    record_event.save()
                    image_name = data.get("image_name", None)
                    if image_name:
                        plugin["share_image"] = image_name

                    transaction.savepoint_commit(sid)
                except Exception as e:
                    logger.exception(e)
                    if sid:
                        transaction.savepoint_rollback(sid)
                    raise ServiceHandleException(msg="share failed", msg_show="插件分享事件同步发生错误", status_code=500)

            plugin_list.append(plugin)
        app_template["plugins"] = plugin_list
        apps_version.app_template = json.dumps(app_template)
        apps_version.save()
        return record_event

    def get_sync_plugin_events(self, region_name: str, tenant_name: str, record_event: Any) -> Any:
        res, body = region_api.share_plugin_result(region_name, tenant_name, record_event.plugin_id,
                                                   record_event.region_share_id)
        # NOTE: region_api.share_plugin_result body is Optional[Dict]; unguarded .get is a
        # potential latent None-bug if the region call returns no body.
        ret = body.get('bean')  # type: ignore[union-attr]
        if ret and ret.get('status'):
            record_event.event_status = ret.get("status")
            record_event.save()
        return record_event

    def get_sync_event_result(self, region_name: str, tenant_name: str, record_event: Any) -> Any:
        res, re_body = region_api.share_service_result(region_name, tenant_name, record_event.service_alias,
                                                       record_event.region_share_id)
        # NOTE: region_api.share_service_result body is Optional[Dict]; unguarded .get is a
        # potential latent None-bug if the region call returns no body.
        bean = re_body.get("bean")  # type: ignore[union-attr]
        logger.info(
            "[vm-publish] poll region share result: record_id=%s service_alias=%s region_share_id=%s "
            "current_status=%s remote_status=%s",
            record_event.record_id,
            record_event.service_alias,
            record_event.region_share_id,
            record_event.event_status,
            bean.get("status", None) if isinstance(bean, dict) else None,
        )
        if bean and bean.get("status", None):
            record_event.event_status = bean.get("status", None)
            record_event.save()
        return record_event

    @staticmethod
    def get_app_by_app_id(app_id: str) -> Optional[RainbondCenterApp]:
        return rainbond_app_repo.get_rainbond_app_by_app_id(app_id=app_id)

    def get_app_version_by_app_id(self, app_id: str, is_complete: bool) -> QuerySet:
        return rainbond_app_repo.get_app_versions_by_app_id(app_id, is_complete)

    def get_app_by_key(self, key: str) -> Optional[RainbondCenterApp]:
        return rainbond_app_repo.get_rainbond_app_by_app_id(key)

    def delete_app(self, app: Any) -> None:
        app.delete()

    def delete_record(self, record: Any) -> None:
        record.delete()

    def create_tenant_service(self, **kwargs: Any) -> Any:
        return share_repo.create_tenant_service(**kwargs)

    def create_tenant_service_port(self, **kwargs: Any) -> Any:
        return share_repo.create_tenant_service_port(**kwargs)

    def create_tenant_service_env_var(self, **kwargs: Any) -> Any:
        return share_repo.create_tenant_service_env_var(**kwargs)

    def create_tenant_service_volume(self, **kwargs: Any) -> Any:
        return share_repo.create_tenant_service_volume(**kwargs)

    def create_tenant_service_relation(self, **kwargs: Any) -> Any:
        return share_repo.create_tenant_service_relation(**kwargs)

    def create_tenant_service_plugin(self, **kwargs: Any) -> Any:
        return share_repo.create_tenant_service_plugin(**kwargs)

    def create_tenant_service_plugin_relation(self, **kwargs: Any) -> Any:
        return share_repo.create_tenant_service_plugin_relation(**kwargs)

    def create_service_share_record(self, **kwargs: Any) -> Any:
        return share_repo.create_service_share_record(**kwargs)

    def get_service_share_record(self, group_share_id: str) -> Any:
        return share_repo.get_service_share_record(group_share_id=group_share_id)

    def get_service_share_record_by_ID(self, ID: str, team_name: str) -> Any:
        # NOTE: ID is the int AutoField PK used as a str identifier by callers (view path
        # params); the repo declares it int, hence the arg-type suppression.
        return share_repo.get_service_share_record_by_ID(ID=ID, team_name=team_name)  # type: ignore[arg-type]

    def get_service_share_record_by_group_id(self, group_id: str) -> Any:
        return share_repo.get_service_share_record_by_groupid(group_id=group_id)

    def get_plugins_group_items(self, plugins: list) -> list:
        rt_list = []
        for p in plugins:
            config_group_list = plugin_config_service.get_config_details(p["plugin_id"], p["build_version"])
            p["config_groups"] = config_group_list
            if p["origin_share_id"] == "new_create":
                p["plugin_key"] = p["plugin_id"]
            else:
                p["plugin_key"] = p["origin_share_id"]
            rt_list.append(p)
        return rt_list

    # 创建应用分享记录
    # 创建应用记录
    # 创建介质同步记录
    @transaction.atomic
    def create_share_info(self, tenant: Any, region_name: str, share_record: Any, share_team: Any, share_user: Any,
                          share_info: dict, use_force: bool, user_id: str) -> Tuple[int, str, Optional[dict]]:
        # 开启事务
        sid = transaction.savepoint()
        try:
            share_version_info = share_info["app_version_info"]
            app_model_id = share_version_info.get("app_model_id")
            version = share_version_info.get("version")
            target = share_version_info.get("scope_target")
            version_alias = share_version_info.get("version_alias", "")
            template_type = share_version_info.get("template_type", "")
            version_describe = share_version_info.get("describe", "this is a default describe.")
            share_k8s_resources = share_info.get("share_k8s_resources")
            market_id = None
            market = None
            app_model_name = None
            share_store_name = ''
            if target:
                market_id = target.get("store_id")
            if not market_id:
                market_id = share_record.share_app_market_name
            if market_id:
                scope = "goodrain"
                market = app_market_service.get_app_market_by_name(
                    share_team.enterprise_id, market_id, user_id=user_id, raise_exception=True)
                cloud_app = app_market_service.get_market_app_model(market, app_model_id, True)
                if cloud_app:
                    app_model_name = cloud_app.app_name
                    share_store_name = cloud_app.market_name
            else:
                local_app_version = RainbondCenterApp.objects.filter(app_id=app_model_id).first()
                if not local_app_version:
                    return 400, "本地应用模型不存在", None
                scope = local_app_version.scope
                app_model_name = local_app_version.app_name
            if scope is None or app_model_name is None:
                return 400, "参数错误", None

            # 删除历史数据
            ServiceShareRecordEvent.objects.filter(record_id=share_record.ID).delete()

            app = group_service.get_app_by_id(share_team, region_name, share_record.group_id)
            # NOTE: get_app_by_id returns Optional[ServiceGroup]; unguarded .governance_mode is a
            # potential latent None-bug if the app is not found.
            governance_mode = (
                app.governance_mode  # type: ignore[union-attr]
                if app.governance_mode  # type: ignore[union-attr]
                else GovernanceModeEnum.BUILD_IN_SERVICE_MESH.name)
            snapshot_publish_version = self.get_snapshot_publish_version(share_record)
            snapshot_template = None
            if snapshot_publish_version:
                snapshot_template = json.loads(snapshot_publish_version.app_template)

            app_template = {}
            # 处理基本信息
            try:
                if snapshot_template:
                    app_template = self._build_publish_template_from_snapshot(
                        snapshot_template, app_model_id, app_model_name, version, governance_mode, share_version_info
                    )
                else:
                    app_template["template_version"] = self._resolve_publish_template_version(
                        share_info.get("share_service_list", []))
                    app_template["group_key"] = app_model_id
                    app_template["group_name"] = app_model_name
                    app_template["group_version"] = version
                    app_template["group_dev_status"] = ""
                    app_template["governance_mode"] = governance_mode
                    app_template["k8s_resources"] = share_k8s_resources
                    platform_plugin = self._build_platform_plugin_config(share_version_info)
                    if platform_plugin:
                        app_template["platform_plugin"] = platform_plugin
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                raise ServiceHandleException(msg="Basic information processing error", msg_show="基本信息处理错误")

            # group config
            if not snapshot_template:
                service_ids_keys_map = {svc["service_id"]: svc['service_key'] for svc in share_info["share_service_list"]}
                app_template["app_config_groups"] = self.config_groups(region_name, service_ids_keys_map)

                # ingress
                ingress_http_routes = self._list_http_ingresses(tenant, service_ids_keys_map)
                app_template["ingress_http_routes"] = ingress_http_routes

            # plugins
            try:
                plugins = copy.deepcopy(
                    app_template.get("plugins", []) if snapshot_template else share_info.get("share_plugin_list", None)
                )
                shared_plugin_info = None
                if plugins:
                    for plugin_info in plugins:
                        # one account for one plugin
                        share_image_info = app_store.get_app_hub_info(market, app_model_id, share_team.enterprise_id)
                        plugin_info["plugin_image"] = share_image_info
                        event = PluginShareRecordEvent(
                            record_id=share_record.ID,
                            team_name=share_team.tenant_name,
                            team_id=share_team.tenant_id,
                            plugin_id=plugin_info['plugin_id'],
                            plugin_name=plugin_info['plugin_alias'],
                            event_status='not_start')
                        event.save()

                    shared_plugin_info = plugins if snapshot_template else self.get_plugins_group_items(plugins)
                    app_template["plugins"] = shared_plugin_info
            except ServiceHandleException as e:
                raise e
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                return 500, "插件处理发生错误", None

            # 处理组件相关
            app_arch = dict()
            try:
                services = copy.deepcopy(app_template.get("apps", []) if snapshot_template else share_info["share_service_list"])
                if services:
                    new_services = list()
                    service_ids = [s["service_id"] for s in services]
                    delivered_type_map = {}
                    if service_ids and services[0].get("service_region"):
                        version_list = base_service.get_apps_deploy_versions(
                            services[0]["service_region"], share_team.tenant_name, service_ids
                        ) or []
                        delivered_type_map = {v["service_id"]: v["delivered_type"] for v in version_list}

                    # For platform plugin publish, generate stable service_share_uuid
                    # so that the same plugin produces identical UUIDs across publishes.
                    # Priority: 1) original UUID from ServiceSourceInfo (installed from template)
                    #           2) hash(plugin_id + service_cname) for first-time publish
                    is_platform_plugin = share_version_info.get("is_platform_plugin", False)
                    platform_plugin_id = share_version_info.get("plugin_id", "")
                    if is_platform_plugin and platform_plugin_id:
                        # Batch-load service source info for all components
                        source_uuid_map = {}
                        sources = ServiceSourceInfo.objects.filter(
                            service_id__in=service_ids
                        ).values_list("service_id", "service_share_uuid")
                        for svc_id, suuid in sources:
                            if suuid:
                                source_uuid_map[svc_id] = suuid

                        uuid_remap = {}
                        for service in services:
                            old_uuid = service["service_share_uuid"]
                            # Use original UUID from installation source if available
                            original = source_uuid_map.get(service["service_id"])
                            if original:
                                new_uuid = original
                            else:
                                # First publish: deterministic hash from plugin_id + service_cname
                                stable_key = hashlib.md5(
                                    (platform_plugin_id + ":" + service["service_cname"]).encode()
                                ).hexdigest()
                                new_uuid = "{0}+{1}".format(stable_key, stable_key)
                            uuid_remap[old_uuid] = new_uuid
                            service["service_share_uuid"] = new_uuid
                        # Update dependency references
                        for service in services:
                            for dep in service.get("dep_service_map_list", []):
                                old_key = dep.get("dep_service_key", "")
                                if old_key in uuid_remap:
                                    dep["dep_service_key"] = uuid_remap[old_key]

                    dep_service_keys = {service['service_share_uuid'] for service in services}

                    for service in services:
                        app_arch[service.get("arch", "amd64")] = 1
                        service["service_related_plugin_config"] = service.get("service_related_plugin_config", [])
                        delivered_type = delivered_type_map.get(service['service_id'], None)
                        if not delivered_type and not snapshot_template:
                            continue
                        if delivered_type == "slug":
                            slug_info = app_store.get_slug_hub_info(market, app_model_id, share_team.enterprise_id)
                            self._apply_slug_delivery(service, slug_info)
                            if not service['service_slug']:
                                if sid:
                                    transaction.savepoint_rollback(sid)
                                return 400, "获取源码包上传地址错误", None
                        else:
                            image_info = app_store.get_app_hub_info(market, app_model_id, share_team.enterprise_id)
                            self._apply_image_delivery(service, image_info)
                            if not service["service_image"]:
                                if sid:
                                    transaction.savepoint_rollback(sid)
                                return 400, "获取镜像上传地址错误", None

                        # 处理依赖关系
                        self._handle_dependencies(service, dep_service_keys, use_force)

                        if not snapshot_template:
                            service["service_related_plugin_config"] = self.wrapper_service_plugin_config(
                                service["service_related_plugin_config"], shared_plugin_info)

                        if service.get("need_share", None):
                            ssre = ServiceShareRecordEvent(
                                team_id=share_team.tenant_id,
                                service_key=service["service_key"],
                                service_id=service["service_id"],
                                service_name=service["service_cname"],
                                service_alias=service["service_alias"],
                                record_id=share_record.ID,
                                team_name=share_team.tenant_name,
                                event_status="not_start")
                            ssre.save()
                        new_services.append(service)
                    app_template["apps"] = new_services
            except ServiceHandleException as e:
                raise e
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                return 500, "组件信息处理发生错误", None
            share_record.scope = scope
            app_arch = app_arch if app_arch else {app_template.get("arch", "amd64"): 1}
            app_template["arch"] = "&".join(app_arch.keys())
            app_version = RainbondCenterAppVersion(
                app_id=app_model_id,
                version=version,
                app_version_info=version_describe,
                version_alias=version_alias,
                template_type=template_type,
                record_id=share_record.ID,
                share_user=share_user.user_id,
                share_team=share_team.tenant_name,
                group_id=share_record.group_id,
                source="local",
                scope=scope,
                app_template=json.dumps(app_template),
                template_version="v2",
                enterprise_id=share_team.enterprise_id,
                # NOTE: model field upgrade_time is declared str/int but a float (time.time())
                # is passed; pre-existing wrong-arg-type, not changing behavior.
                upgrade_time=time.time(),  # type: ignore[misc]
                arch=app_template["arch"],
            )
            if app_store.is_no_multiple_region_hub(enterprise_id=share_team.enterprise_id):
                app_version.region_name = region_name
            app_version.save()
            if not market_id:
                # NOTE: invariant — when market_id is falsy, local_app_version was assigned in the
                # `else` branch above (with an early return if None), so it is guaranteed non-None here.
                if local_app_version.arch:  # type: ignore[union-attr]
                    arch = list(local_app_version.arch.split(","))  # type: ignore[union-attr]
                    if app_version.arch not in arch:
                        arch.append(app_version.arch)
                    local_app_version.arch = ",".join(arch)  # type: ignore[union-attr]
                else:
                    local_app_version.arch = app_version.arch  # type: ignore[union-attr]
                local_app_version.save()  # type: ignore[union-attr]
            share_record.step = 2
            share_record.scope = scope
            share_record.app_id = app_model_id
            share_record.share_version = version
            share_record.share_version_alias = version_alias
            share_record.share_app_market_name = market_id
            share_record.share_app_model_name = app_model_name
            share_record.share_store_name = share_store_name
            share_record.update_time = datetime.datetime.now()
            share_record.share_app_version_info = version_describe
            share_record.save()
            # 提交事务
            if sid:
                transaction.savepoint_commit(sid)
            return 200, "分享信息处理成功", share_record.to_dict()
        except ServiceHandleException as e:
            raise e
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            return 500, "应用分享处理发生错误", None

    def _list_http_ingresses(self, tenant: Any, component_keys: dict) -> list:
        service_domains = domain_repo.list_by_component_ids(component_keys.keys())
        if not service_domains:
            return []
        configs = configuration_repo.list_by_rule_ids([sd.http_rule_id for sd in service_domains])
        configs = {cfg.rule_id: json.loads(cfg.value) for cfg in configs}

        ports = port_repo.list_by_service_ids(tenant.tenant_id, component_keys.keys())
        ports = {port.container_port: port for port in ports}

        ingress_http_routes = []
        for sd in service_domains:
            # only work for outer port
            port = ports.get(sd.container_port)
            if not port or not port.is_outer_service:
                continue

            config = configs.get(sd.http_rule_id, {})
            rewrites = sd.rewrites if sd.rewrites else '[]'
            if isinstance(rewrites, str):
                rewrites = eval(rewrites)
            ingress_http_route = {
                "default_domain": sd.type == 0,
                "location": sd.domain_path,
                "cookies": self._parse_cookie_or_header(sd.domain_cookie),
                "headers": self._parse_cookie_or_header(sd.domain_heander),
                "path_rewrite": sd.path_rewrite,
                "rewrites": rewrites,
                "ssl": sd.auto_ssl,
                "load_balancing": sd.load_balancing,
                "connection_timeout": config.get("proxy_connect_timeout"),
                "request_timeout": config.get("proxy_send_timeout"),
                "response_timeout": config.get("proxy_read_timeout"),
                "request_body_size_limit": config.get("proxy_body_size"),
                "proxy_buffer_numbers": config.get("proxy_buffer_numbers"),
                "proxy_buffer_size": config.get("proxy_buffer_size"),
                "websocket": config.get("WebSocket"),
                "component_key": component_keys.get(sd.service_id),
                "port": sd.container_port,
                "proxy_header": config.get("set_headers"),
            }
            ingress_http_routes.append(ingress_http_route)
        return ingress_http_routes

    @staticmethod
    def _parse_cookie_or_header(cookies: str) -> dict:
        # example: foo=bar;apple=pie
        cookies = cookies.replace(" ", "")
        result = {}
        for cookie in cookies.split(";"):
            kvs = cookie.split("=")
            if len(kvs) != 2 or kvs[0] == "" or kvs[1] == "":
                continue
            result[kvs[0]] = kvs[1]
        return result

    def config_groups(self, region_name: str, service_ids_keys_map: dict) -> list:
        groups = app_config_group_repo.list_by_service_ids(region_name, list(service_ids_keys_map.keys()))
        cgs = []
        for group in groups:
            # list related items
            cg = {
                "name":
                group.config_group_name,
                "injection_type":
                group.deploy_type,
                "enable":
                group.enable,
                "config_items":
                {item.item_key: item.item_value
                 for item in app_config_group_item_repo.list(group.config_group_id)},
                "component_keys": [
                    service_ids_keys_map.get(service.service_id)
                    for service in app_config_group_service_repo.list(group.config_group_id)
                ]
            }
            cgs.append(cg)

        return cgs

    @staticmethod
    def _handle_dependencies(service: dict, dev_service_set: set, use_force: bool) -> None:
        """检查组件依赖信息，如果依赖不完整则中断请求， 如果强制执行则删除依赖"""

        def filter_dep(dev_service: dict) -> bool:
            """过滤依赖关系"""
            dep_service_key = dev_service['dep_service_key']
            if dep_service_key not in dev_service_set:
                return False
            elif dep_service_key not in dev_service_set and not use_force:
                raise AbortRequest(
                    error_code=10501,
                    msg="{} service is missing dependencies".format(service['service_cname']),
                    msg_show="{}组件缺少依赖组件，请添加依赖组件，或强制执行".format(service['service_cname']))
            else:
                return True

        if service.get('dep_service_map_list'):
            service['dep_service_map_list'] = list(filter(filter_dep, service['dep_service_map_list']))

    def complete(self, tenant: Any, user: Any, share_record: Any, is_plugin: bool, user_id: str,
                 region_name: Optional[str] = None) -> Optional[str]:
        app_version = rainbond_app_repo.get_rainbond_app_version_by_record_id(share_record.ID)
        # NOTE: potential latent None-bug — app_version may be None (record not found), yet .app_id
        # is dereferenced here before the `if app_version:` guard below.
        app = rainbond_app_repo.get_rainbond_app_by_app_id(app_version.app_id)  # type: ignore[union-attr]
        app_market_url = None
        if app_version:
            # 分享到云市
            # NOTE: scope is an Optional[str] model field; .startswith assumes it is set.
            if app_version.scope.startswith("goodrain"):  # type: ignore[union-attr]
                share_type = "private"
                info = app_version.scope.split(":")  # type: ignore[union-attr]
                if len(info) > 1:
                    share_type = info[1]
                # NOTE: publish_app_to_public_market never returns a value (only None / raises),
                # so app_market_url is always None here — pre-existing dead assignment.
                app_market_url = self.publish_app_to_public_market(  # type: ignore[func-returns-value]
                    tenant, share_record, user.nick_name, app_version, is_plugin, user_id, share_type)

            # 检测企业级别发布中的流水线插件
            if app_version.scope == "enterprise" and region_name:
                self._handle_pipeline_plugin_for_enterprise(tenant, app_version, share_record, user_id, region_name)

            app_version.is_complete = True
            app_version.update_time = datetime.datetime.now()
            app_version.is_plugin = is_plugin
            app_version.save()
            if app:
                app.is_version = True
                app.update_time = datetime.datetime.now()
                app.save()
            RainbondCenterAppVersion.objects.filter(
                app_id=app_version.app_id, source="local", scope="goodrain", is_complete=True).delete()
            share_record.is_success = True
            share_record.step = 3
            share_record.status = 1
            share_record.update_time = datetime.datetime.now()
            share_record.save()
        # 应用有更新，删除导出记录
        # NOTE: potential latent None-bug — app_version may be None and is dereferenced here
        # outside the `if app_version:` block above.
        app_export_record_repo.delete_by_key_and_version(app_version.app_id, app_version.version)  # type: ignore[union-attr]
        return app_market_url

    def publish_app_to_public_market(self, tenant: Any, share_record: Any, user_name: str, app: Any, is_plugin: bool,
                                     user_id: str, share_type: str = "private") -> None:
        try:
            data = dict()
            data["description"] = app.app_version_info
            data["rainbond_version"] = os.getenv("RELEASE_DESC", "public-cloud")
            data["template"] = json.loads(app.app_template)
            data["template_type"] = app.template_type
            data["version"] = app.version
            data["version_alias"] = app.version_alias
            data['is_plugin'] = is_plugin
            data['arch'] = app.arch
            # TODO 修改传入数据, 修改返回数据
            ingress_http_routes = data["template"]["ingress_http_routes"] if data["template"].get("ingress_http_routes") else []
            for http_rule in ingress_http_routes:
                new_proxy_headers = dict()
                proxy_headers = http_rule["proxy_header"] if http_rule.get("proxy_header") else []
                for headers in proxy_headers:
                    if not headers.get("item_key") and not headers.get("item_value"):
                        continue
                    new_proxy_headers[headers["item_key"]] = headers["item_value"]
                http_rule["proxy_header"] = new_proxy_headers
            apps = data["template"].get("apps", [])
            new_apps = []
            for ap in apps:
                ap["cpu"] = ap.get("extend_method_map", {}).get("container_cpu", 0)
                new_apps.append(ap)
            data["template"]["apps"] = new_apps
            market = app_market_service.get_app_market_by_name(
                tenant.enterprise_id, share_record.share_app_market_name, user_id=user_id, raise_exception=True)
            app_market_service.create_market_app_model_version(market, app.app_id, data)
            # 云市url
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                raise ServiceHandleException("no cloud permission", msg_show="云市授权不通过", status_code=403, error_code=10407)
            else:
                raise ServiceHandleException("call cloud api failure", msg_show="云市请求错误", status_code=500, error_code=500)

    def _handle_pipeline_plugin_for_enterprise(self, tenant: Any, app_version: Any, share_record: Any, user_id: str,
                                               region_name: str) -> None:
        """
        处理企业级别发布中的流水线插件
        通过region API获取插件列表，检测是否存在流水线插件，如果存在则调用相应接口
        注意：只在模板已存在（非首次发布）时才调用接口
        """
        try:
            # 检查是否是第一次发布该模板
            # 查询是否存在该 app_id 的其他已完成版本（排除当前版本）
            existing_versions = RainbondCenterAppVersion.objects.filter(
                app_id=app_version.app_id,
                scope="enterprise",
                is_complete=True,
                enterprise_id=tenant.enterprise_id
            ).exclude(ID=app_version.ID).count()

            if existing_versions == 0:
                # 第一次发布该模板，不需要调用接口
                logger.info("First version of template published, skip pipeline trigger: app_id={}, version={}".format(
                    app_version.app_id, app_version.version))
                return

            logger.info(
                "Not first version of template, checking pipeline plugin: app_id={}, version={}, existing_versions={}".format(
                    app_version.app_id, app_version.version, existing_versions))

            # 先通过 rbd_plugin_service 获取插件列表（包含 URLs）
            from console.services.plugin_service import rbd_plugin_service
            plugins, _ = rbd_plugin_service.list_plugins(tenant.enterprise_id, region_name, official=False)

            logger.info("Retrieved {} plugins from region: enterprise_id={}, region_name={}".format(
                len(plugins) if plugins else 0, tenant.enterprise_id, region_name))

            # 打印所有插件的详细信息
            if plugins:
                for idx, plugin in enumerate(plugins):
                    logger.info("Plugin {}: name={}, category={}, urls={}".format(
                        idx + 1,
                        plugin.get("name", "unknown"),
                        plugin.get("category", "unknown"),
                        plugin.get("urls", [])))

            # 检测是否存在流水线插件
            # 注意：Region API 返回的插件没有 category 字段，应该用 name 字段判断
            has_pipeline_plugin = False
            pipeline_plugin_info = None
            for plugin in plugins:
                plugin_name = plugin.get("name", "")
                logger.info("Checking plugin: name={}, backend={}, urls={}".format(
                    plugin_name, plugin.get("backend"), plugin.get("urls", [])))

                # 使用 name 字段判断（而不是 category）
                if plugin_name == "rainbond-enterprise-pipeline":
                    has_pipeline_plugin = True
                    pipeline_plugin_info = plugin
                    logger.info("Detected pipeline plugin in enterprise scope: name={}, backend={}, urls={}".format(
                        plugin.get("name", "unknown"), plugin.get("backend"), plugin.get("urls", [])))
                    break

            # 如果存在流水线插件，调用接口
            if has_pipeline_plugin:
                # NOTE: invariant — pipeline_plugin_info is a dict whenever has_pipeline_plugin is
                # True (set together in the loop above); mypy cannot link the two flags.
                self._call_pipeline_plugin_api(
                    tenant, app_version, share_record, user_id, region_name,
                    pipeline_plugin_info)  # type: ignore[arg-type]
            else:
                logger.info("No pipeline plugin found, skip trigger: app_id={}, version={}".format(
                    app_version.app_id, app_version.version))
                logger.info("Expected category: 'rainbond-enterprise-pipeline', but none of {} plugins matched".format(
                    len(plugins) if plugins else 0))

        except Exception as e:
            logger.exception("Error handling pipeline plugin for enterprise: {}".format(e))
            # 这里不抛出异常，避免影响主流程

    def _call_pipeline_plugin_api(self, tenant: Any, app_version: Any, share_record: Any, user_id: str,
                                  region_name: str, pipeline_plugin_info: dict) -> None:
        """
        调用流水线插件模板版本触发接口
        在模板发布成功后，调用此接口触发相关工作流
        """
        try:
            # 优先使用 backend 字段，如果没有再尝试 urls
            backend_url = pipeline_plugin_info.get("backend")
            plugin_urls = pipeline_plugin_info.get("urls", [])

            base_url = None
            if backend_url:
                # 使用 backend 字段
                base_url = backend_url.rstrip('/')
                logger.info("Using plugin backend URL: {}".format(base_url))
            elif plugin_urls:
                # 使用 urls 字段的第一个 URL
                base_url = plugin_urls[0].rstrip('/')
                logger.info("Using plugin urls[0]: {}".format(base_url))
            else:
                logger.warning("Pipeline plugin has no backend or access URLs, skip trigger. plugin: {}".format(
                    pipeline_plugin_info.get("name", "unknown")))
                return

            # 构造完整的 API 路径
            # POST /api/v1/workflows/templates/{uuid}/trigger-by-template-version
            template_uuid = app_version.app_id
            api_path = "/api/v1/workflows/templates/{}/trigger-by-template-version".format(template_uuid)
            api_url = "{}{}".format(base_url, api_path)

            logger.info("Triggering pipeline workflow for template: uuid={}, version={}, url={}".format(
                template_uuid, app_version.version, api_url))

            # 发送 POST 请求（无需 body）
            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                timeout=10  # 10秒超时
            )

            # 解析响应
            if response.status_code == 200:
                result = response.json()
                code = result.get("code", -1)
                message = result.get("message", "")
                data = result.get("data", {})

                if code == 0:
                    triggered = data.get("triggered", False)
                    if triggered:
                        execution_id = data.get("executionId", "")
                        workflow_cr_name = data.get("workflowCrName", "")
                        logger.info(
                            "Pipeline workflow triggered: template=%s, version=%s, executionId=%s, workflowCrName=%s",
                            template_uuid, app_version.version, execution_id, workflow_cr_name)
                    else:
                        # triggered=false 是正常情况（未配置触发器或触发器未启用）
                        logger.info("Pipeline workflow not triggered: template={}, version={}, reason={}".format(
                            template_uuid, app_version.version, data.get("message", "No trigger configured")))
                else:
                    # code != 0 表示错误
                    logger.error("Pipeline workflow trigger failed: template={}, version={}, code={}, message={}".format(
                        template_uuid, app_version.version, code, message))
            else:
                # HTTP 状态码非 200
                logger.error("Pipeline workflow trigger HTTP error: template={}, version={}, status_code={}, response={}".format(
                    template_uuid, app_version.version, response.status_code, response.text))

        except requests.exceptions.Timeout:
            logger.error("Pipeline workflow trigger timeout: template={}, version={}".format(
                app_version.app_id, app_version.version))
        except requests.exceptions.RequestException as e:
            logger.error("Pipeline workflow trigger request failed: template={}, version={}, error={}".format(
                app_version.app_id, app_version.version, str(e)))
        except Exception as e:
            logger.exception("Pipeline workflow trigger unexpected error: template={}, version={}, error={}".format(
                app_version.app_id, app_version.version, str(e)))

        # 注意：所有异常都被捕获，不会影响主流程

    @staticmethod
    def get_shared_services_list(service: dict) -> dict:
        data = {
            "group_name": service["group_name"],
            "group_key": service["group_key"],
        }
        return data

    @staticmethod
    def get_shared_services_versions_list(service: Any) -> dict:
        data = {
            "group_name": service.group_name,
            "group_key": service.group_key,
            "version": service.version,
        }
        return data

    @staticmethod
    def get_shared_services_records_list(service: Any) -> dict:
        data = {
            "group_name": service.group_name,
            "group_key": service.group_key,
            "version": service.version,
            "create_time": service.create_time,
            "update_time": service.update_time,
            "scope": service.scope,
            "upgrade_time": service.upgrade_time,
        }
        return data

    def get_team_local_apps_versions(self, enterprise_id: str, team_name: str, preferred_app_id: Optional[str] = None,
                                     template_scope: Optional[str] = None) -> list:
        app_list = []
        visible_team_names = None
        if template_scope == "enterprise":
            tenants = team_repo.get_teams_by_enterprise_id(enterprise_id)
            visible_team_names = [tenant.tenant_name for tenant in tenants]
        apps = list(
            rainbond_app_repo.get_enterprise_team_apps(
                enterprise_id,
                team_name,
                scope=template_scope,
                visible_team_names=visible_team_names,
            )
        )
        if preferred_app_id:
            preferred_app = rainbond_app_repo.get_rainbond_app_by_app_id(preferred_app_id)
            if preferred_app and template_scope and preferred_app.scope != template_scope:
                preferred_app = None
            if preferred_app and all(app.app_id != preferred_app.app_id for app in apps if app):
                apps.insert(0, preferred_app)
        if apps:
            for app in apps:
                if not app:
                    continue
                app_versions = list(share_repo.get_last_app_versions_by_app_id(app.app_id))
                app_list.append({
                    "app_name":
                    app.app_name,
                    "app_id":
                    app.app_id,
                    "pic":
                    app.pic,
                    "app_describe":
                    app.describe,
                    "dev_status":
                    app.dev_status,
                    "versions":
                    sorted(
                        app_versions,
                        key=lambda x: [int(str(y)) if str.isdigit(str(y)) else -1 for y in x["version"].split(".")],
                        reverse=True),
                    "scope":
                    app.scope,
                })
        return app_list

    def get_last_shared_app_and_app_list(self, enterprise_id: str, tenant: Any, group_id: str, scope: str,
                                         market_name: str, user_id: str, preferred_app_id: Optional[str] = None,
                                         preferred_version: Optional[str] = None) -> dict:
        last_shared = share_repo.get_last_shared_app_version_by_group_id(group_id, tenant.tenant_name, scope)
        snapshot_publish = False
        if preferred_app_id and preferred_version:
            preferred_app_version = rainbond_app_repo.get_app_version(preferred_app_id, preferred_version)
            snapshot_publish = self.is_snapshot_publish_version(preferred_app_version)
        local_preferred_app_id = None if snapshot_publish else preferred_app_id
        local_template_scope = "enterprise" if snapshot_publish else None
        dt: Dict[str, Any] = {}
        dt["app_model_list"] = []
        dt["last_shared_app"] = {}
        dt["scope"] = scope
        if scope == "goodrain":
            market = app_market_service.get_app_market_by_name(enterprise_id, market_name, user_id=user_id, raise_exception=True)
            apps_versions, _, _, _ = app_market_service.get_market_app_models(market, page_size=-1, query=None, query_all=True)
            if apps_versions:
                for app in apps_versions:
                    versions = []
                    app_versions = app.versions
                    if app_versions:
                        for version in app_versions:
                            versions.append({
                                "version": version.app_version,
                                "describe": version.desc,
                                "version_alias": version.app_version_alias,
                            })
                    dt["app_model_list"].append({
                        "app_name":
                        app.app_name,
                        "app_id":
                        app.app_id,
                        "versions":
                        sorted(
                            versions,
                            key=lambda x: [int(str(y)) if str.isdigit(str(y)) else -1 for y in x["version"].split(".")],
                            reverse=True),
                        "pic":
                        app.logo,
                        "app_describe":
                        app.describe,
                        "dev_status":
                        app.dev_status,
                        "scope": ("goodrain:" + app.publish_type).strip(":")
                    })
                    if last_shared and app.app_key_id == last_shared.app_id:
                        dt["last_shared_app"] = {
                            "app_name": app.app_name,
                            "app_id": app.app_id,
                            "version": last_shared.share_version,
                            "pic": app.pic,
                            "describe": app.desc,
                            "dev_status": app.dev_status,
                            "scope": ("goodrain:" + app.publish_type).strip(":")
                        }
        else:
            if last_shared:
                # NOTE: last_shared.app_id is an Optional model field; callee expects str.
                last_shared_app_info = rainbond_app_repo.get_rainbond_app_by_app_id(last_shared.app_id)  # type: ignore[arg-type]
                if last_shared_app_info:
                    self._patch_rainbond_app_tag(last_shared_app_info)
                    if not snapshot_publish or last_shared_app_info.scope == "enterprise":
                        dt["last_shared_app"] = {
                            "app_name": last_shared_app_info.app_name,
                            "app_id": last_shared.app_id,
                            "version": last_shared.share_version,
                            "pic": last_shared_app_info.pic,
                            "app_describe": last_shared_app_info.describe,
                            "dev_status": last_shared_app_info.dev_status,
                            "scope": last_shared_app_info.scope,
                            # NOTE: .tags is set dynamically by _patch_rainbond_app_tag above; it is
                            # not a declared model field, hence the attr-defined suppression.
                            "tags": last_shared_app_info.tags  # type: ignore[attr-defined]
                        }
            app_list = self.get_team_local_apps_versions(
                enterprise_id,
                tenant.tenant_name,
                local_preferred_app_id,
                template_scope=local_template_scope,
            )
            self._patch_rainbond_apps_tag(enterprise_id, app_list)
            dt["app_model_list"] = app_list
            if local_preferred_app_id:
                preferred_app = next((item for item in app_list if item.get("app_id") == local_preferred_app_id), None)
                if preferred_app:
                    preferred_versions = preferred_app.get("versions") or []
                    default_version = ((preferred_versions[0] if preferred_versions else {}) or {}).get("version")
                    dt["last_shared_app"] = {
                        "app_name": preferred_app.get("app_name"),
                        "app_id": preferred_app.get("app_id"),
                        "version": preferred_version or default_version,
                        "pic": preferred_app.get("pic"),
                        "app_describe": preferred_app.get("app_describe"),
                        "dev_status": preferred_app.get("dev_status"),
                        "scope": preferred_app.get("scope"),
                        "tags": preferred_app.get("tags", [])
                    }
        return dt

    # patch rainbond app tag
    def _patch_rainbond_app_tag(self, app: Any) -> None:
        tags = app_tag_repo.get_app_with_tags(app.enterprise_id, app.app_id)
        app.tags = []
        if not tags:
            return
        for tag in tags:
            app.tags.append({"tag_id": tag.ID, "name": tag.name})

    # patch rainbond app tag
    def _patch_rainbond_apps_tag(self, eid: str, apps: list) -> None:
        app_ids = [app["app_id"] for app in apps]
        tags = app_tag_repo.get_multi_apps_tags(eid, app_ids)
        if not tags:
            return
        app_with_tags: Dict[Any, Any] = dict()
        for tag in tags:
            if not app_with_tags.get(tag.app_id):
                app_with_tags[tag.app_id] = []
            app_with_tags[tag.app_id].append({"tag_id": tag.ID, "name": tag.name})

        for app in apps:
            app["tags"] = app_with_tags.get(app["app_id"])

    def get_last_shared_app_version(self, tenant: Any, group_id: str,
                                    scope: Optional[str] = None) -> Tuple[Any, Any]:
        last_shared = share_repo.get_last_shared_app_version_by_group_id(group_id, tenant.tenant_name, scope)
        if not last_shared:
            return None, None
        if last_shared.scope == "goodrain":
            try:
                # NOTE: last_shared.share_app_market_name/app_id/share_version are Optional model
                # fields; callees expect str.
                market = app_market_service.get_app_market_by_name(
                    tenant.enterprise_id, last_shared.share_app_market_name,  # type: ignore[arg-type]
                    raise_exception=True)
                app_version = app_market_service.get_market_app_model_version(
                    market, last_shared.app_id, last_shared.share_version,  # type: ignore[arg-type]
                    get_template=True)
            except ServiceHandleException as e:
                logger.debug(e)
                return None, None
            dt = (json.loads(app_version.template), app_version.app_version_info)
        else:
            # NOTE: last_shared.app_id/share_version are Optional model fields; callee expects str.
            app_version = rainbond_app_repo.get_app_version(
                last_shared.app_id, last_shared.share_version)  # type: ignore[arg-type]
            if not app_version:
                return None, None
            dt = (json.loads(app_version.app_template), app_version.app_version_info)
        return dt

    def create_cloud_app(self, tenant: Any, market_name: str, data: dict) -> Any:
        body = {
            "group_key": data.get("app_id"),
            "update_note": data["describe"],
            "group_share_alias": data["name"],
            "logo": data["pic"],
            "details": data["details"],
            "share_type": "private"
        }
        market = app_market_service.get_app_market_by_name(tenant.enterprise_id, market_name, raise_exception=True)
        return app_market_service.create_market_app_model(market, body)

    @staticmethod
    def list_component_k8s_attributes(component_ids: list) -> dict:
        attrs = k8s_attribute_repo.list_by_component_ids(component_ids)
        result: Dict[Any, Any] = {}
        for attr in attrs:
            if not result.get(attr.component_id):
                result[attr.component_id] = []
            a = attr.to_dict()
            del a["ID"]
            result[attr.component_id].append(a)
        return result

    def update_or_create_rainbond_center_app_version(self, tenant: Any, region: RegionConfig, user: Any, app_id: str,
                                                     version: str, app_template: dict) -> None:
        try:
            obj = RainbondCenterAppVersion.objects.get(app_id=app_id, version=version)
            obj.app_template = json.dumps(app_template)
            obj.save()
        except RainbondCenterAppVersion.DoesNotExist:
            RainbondCenterAppVersion.objects.create(
                app_id=app_id,
                version=app_template["group_version"],
                app_version_info="",
                version_alias="",
                template_type="",
                record_id=0,
                share_user=user.user_id,
                share_team=tenant.tenant_name,
                # group_id=share_record.group_id,
                source="local",
                scope="enterprise",
                app_template=json.dumps(app_template),
                template_version="v2",
                enterprise_id=tenant.enterprise_id,
                region_name=region.region_name,
                arch=app_template["arch"],
                is_complete=True,
                # NOTE: model field upgrade_time is declared str/int but a float (time.time())
                # is passed; pre-existing wrong-arg-type, not changing behavior.
                upgrade_time=time.time())  # type: ignore[misc]


share_service = ShareService()
