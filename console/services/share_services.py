# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import time

from console.appstore.appstore import app_store
from console.enum.app import GovernanceModeEnum
from console.enum.component_enum import is_singleton
from console.exception.main import (AbortRequest, RbdAppNotFound, ServiceHandleException)
from console.models.main import (PluginShareRecordEvent, RainbondCenterApp, RainbondCenterAppVersion, ServiceShareRecordEvent)
from console.repositories.app import app_tag_repo
from console.repositories.app_config import mnt_repo, volume_repo
from console.repositories.app_config_group import (app_config_group_item_repo, app_config_group_repo,
                                                   app_config_group_service_repo)
from console.repositories.component_graph import component_graph_repo
from console.repositories.market_app_repo import (app_export_record_repo, rainbond_app_repo)
from console.repositories.plugin import (app_plugin_relation_repo, plugin_repo, service_plugin_config_repo)
from console.repositories.share_repo import share_repo
from console.repositories.app_config import domain_repo, configuration_repo, port_repo
from console.repositories.label_repo import service_label_repo
from console.repositories.label_repo import label_repo
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
    def check_service_source(self, team, team_name, group_id, region_name):
        service_list = share_repo.get_service_list_by_group_id(team=team, group_id=group_id)
        if service_list:
            # 批量查询组件状态
            service_ids = [service.service_id for service in service_list]
            status_list = base_service.status_multi_service(
                region=region_name, tenant_name=team_name, service_ids=service_ids, enterprise_id=team.enterprise_id)
            for status in status_list:
                if status["status"] == "running":
                    data = {"code": 200, "success": True, "msg_show": "应用的组件有在运行中可以发布。", "list": list(), "bean": dict()}
                    return data
            data = {"code": 400, "success": False, "msg_show": "应用下所有组件都在未运行状态，不能发布。", "list": list(), "bean": dict()}
            return data
        else:
            data = {"code": 400, "success": False, "msg_show": "当前应用内无组件", "list": list(), "bean": dict()}
            return data

    def check_whether_have_share_history(self, group_id):
        return share_repo.get_rainbond_cent_app_by_tenant_service_group_id(group_id=group_id)

    def get_service_ports_by_ids(self, service_ids):
        """
        根据多个组件ID查询组件的端口信息
        :param service_ids: 组件ID列表
        :return: {"service_id":TenantServicesPort[object]}
        """
        port_list = share_repo.get_port_list_by_service_ids(service_ids=service_ids)
        if port_list:
            service_port_map = {}
            for port in port_list:
                service_id = port.service_id
                tmp_list = []
                if service_id in list(service_port_map.keys()):
                    tmp_list = service_port_map.get(service_id)
                tmp_list.append(port)
                service_port_map[service_id] = tmp_list
            return service_port_map
        else:
            return {}

    def get_service_dependencys_by_ids(self, service_ids):
        """
        根据多个组件ID查询组件的依赖组件信息
        :param service_ids:组件ID列表
        :return: {"service_id":TenantServiceInfo[object]}
        """
        relation_list = share_repo.get_relation_list_by_service_ids(service_ids=service_ids)
        if relation_list:
            relation_list_service_ids = relation_list.values_list("service_id", flat=True)
            dep_service_map = {service_id: [] for service_id in relation_list_service_ids}
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
    def list_service_monitors(tenant_id, service_ids):
        monitors = component_service_monitor.list_by_service_ids(tenant_id, service_ids)
        result = {}
        for monitor in monitors:
            if not result.get(monitor.service_id):
                result[monitor.service_id] = []
            m = monitor.to_dict()
            del m["ID"]
            result[monitor.service_id].append(m)
        return result

    @staticmethod
    def list_component_graphs(component_ids):
        graphs = component_graph_repo.list_by_component_ids(component_ids)
        result = {}
        for graph in graphs:
            if not result.get(graph.component_id):
                result[graph.component_id] = []
            g = graph.to_dict()
            del g["ID"]
            result[graph.component_id].append(g)
        return result

    @staticmethod
    def list_component_labels(component_ids):
        component_labels = service_label_repo.list_by_component_ids(component_ids)
        labels = label_repo.list_by_label_ids([label.label_id for label in component_labels])
        labels = {label.label_id: label for label in labels}

        res = {}
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

    def get_dep_mnts_by_ids(self, tenant_id, service_ids):
        mnt_relations = mnt_repo.list_mnt_relations_by_service_ids(tenant_id, service_ids)
        if not mnt_relations:
            return {}
        result = {}
        for mnt_relation in mnt_relations:
            service_id = mnt_relation.service_id
            if service_id in list(result.keys()):
                values = result.get(service_id)
            else:
                values = []
                result[service_id] = values
            values.append(mnt_relation)

        return result

    def get_service_env_by_ids(self, service_ids):
        """
        获取组件env
        :param service_ids: 组件ID列表
        # :return: 可修改的环境变量service_env_change_map，不可修改的环境变量service_env_nochange_map
        :return: 环境变量service_env_map
        """
        env_list = share_repo.get_env_list_by_service_ids(service_ids=service_ids)
        if env_list:
            service_env_map = {}
            for env in env_list:
                if env.scope == "build":
                    continue
                service_id = env.service_id
                tmp_list = []
                if service_id in list(service_env_map.keys()):
                    tmp_list = service_env_map.get(service_id)
                tmp_list.append(env)
                service_env_map[service_id] = tmp_list
            return service_env_map
        else:
            return {}

    def get_service_volume_by_ids(self, service_ids):
        """
        获取组件持久化目录
        """
        volume_list = share_repo.get_volume_list_by_service_ids(service_ids=service_ids)
        if volume_list:
            service_volume_map = {}
            for volume in volume_list:
                service_id = volume.service_id
                tmp_list = []
                if service_id in list(service_volume_map.keys()):
                    tmp_list = service_volume_map.get(service_id)
                tmp_list.append(volume)
                service_volume_map[service_id] = tmp_list
            return service_volume_map
        else:
            return {}

    def get_service_extend_method_by_keys(self, service_keys):
        """
        获取组件伸缩状态
        """
        extend_method_list = share_repo.get_service_extend_method_by_keys(service_keys=service_keys)
        if extend_method_list:
            extend_method_map = {}
            for extend_method in extend_method_list:
                service_key = extend_method.service_key
                tmp_list = []
                if service_key in extend_method_map.get(service_key):
                    tmp_list = extend_method_map.get(service_key)
                tmp_list.append(extend_method)
                extend_method_map[service_key] = tmp_list
            return extend_method_map
        else:
            return {}

    def get_service_probes(self, service_ids):
        """
        获取组件健康检测探针
        """
        probe_list = share_repo.get_probe_list_by_service_ids(service_ids=service_ids)
        if probe_list:
            service_probe_map = {}
            for probe in probe_list:
                service_id = probe.service_id
                tmp_list = []
                if service_id in list(service_probe_map.keys()):
                    tmp_list = service_probe_map.get(service_id)
                tmp_list.append(probe)
                service_probe_map[service_id] = tmp_list
            return service_probe_map
        else:
            return {}

    def get_team_service_deploy_version(self, region, team, service_ids):
        try:
            res, body = region_api.get_team_services_deploy_version(region, team.tenant_name, {"service_ids": service_ids})
            if res.status == 200:
                service_versions = {}
                for version in body["list"]:
                    if version and "service_id" in version and "build_version" in version:
                        service_versions[version["service_id"]] = version["build_version"]
                return service_versions
        except Exception as e:
            logger.exception(e)
        logger.debug("======>get services deploy version failure")
        return None

    def query_share_service_info(self, team, group_id, scope=None):
        service_list = share_repo.get_service_list_by_group_id(team=team, group_id=group_id)
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
                data['deploy_version'] = deploy_versions[data['service_id']] if deploy_versions else service.deploy_version
                data['image'] = service.image
                data['service_alias'] = service.service_alias
                data['service_name'] = service.service_name
                data['service_region'] = service.service_region
                data['creater'] = service.creater
                data["cmd"] = service.cmd
                data['probes'] = [probe.to_dict() for probe in probe_map.get(service.service_id, [])]
                e_m = dict()
                e_m['step_node'] = 1
                e_m['min_memory'] = 64
                e_m['init_memory'] = service.min_memory
                e_m['max_memory'] = 65536
                e_m['step_memory'] = 64
                e_m['is_restart'] = 0
                e_m['min_node'] = service.min_node
                e_m['container_cpu'] = service.min_cpu
                if is_singleton(service.extend_method):
                    e_m['max_node'] = 1
                else:
                    e_m['max_node'] = 64
                data['extend_method_map'] = e_m
                data['port_map_list'] = list()
                if service_port_map.get(service.service_id):
                    for port in service_port_map.get(service.service_id):
                        p = dict()
                        # 写需要返回的port数据
                        p['protocol'] = port.protocol
                        p['tenant_id'] = port.tenant_id
                        p['port_alias'] = port.port_alias
                        p['container_port'] = port.container_port
                        p['is_inner_service'] = port.is_inner_service
                        p['is_outer_service'] = port.is_outer_service
                        p['k8s_service_name'] = port.k8s_service_name
                        data['port_map_list'].append(p)

                data['service_volume_map_list'] = list()
                if service_volume_map.get(service.service_id):
                    for volume in service_volume_map.get(service.service_id):
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
                    for env_change in service_env_map.get(service.service_id):
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
                    for dep_mnt in dep_mnt_map.get(service_id):
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

    def service_last_share_cache(self, service_info, last_share_info):
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

    def query_service_last_share_info(self, group_id):
        service_share = share_repo.get_shared_app_versions_by_groupid(group_id).first()
        if service_share:
            return json.loads(service_share.app_template)["apps"]
        else:
            return None

    # 查询应用内使用的插件列表
    def query_group_service_plugin_list(self, team, group_id):
        service_list = share_repo.get_service_list_by_group_id(team=team, group_id=group_id)
        if service_list:
            service_ids = [x.service_id for x in service_list]
            plugins = plugin_service.get_plugins_by_service_ids(service_ids)
            # 默认插件分享
            for p in plugins:
                p["is_share"] = True
            return plugins
        else:
            return []

    def get_group_services_used_plugins(self, group_id):
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

    def wrapper_service_plugin_config(self, service_related_plugin_config, shared_plugin_info):
        """添加plugin key信息"""
        id_key_map = {}
        if shared_plugin_info:
            id_key_map = {i["plugin_id"]: i["plugin_key"] for i in shared_plugin_info}

        service_plugin_config_list = []
        for config in service_related_plugin_config:
            config["plugin_key"] = id_key_map.get(config["plugin_id"])
            service_plugin_config_list.append(config)
        return service_plugin_config_list

    def create_basic_app_info(self, **kwargs):
        return share_repo.add_basic_app_info(**kwargs)

    def create_publish_event(self, record_event, user_name, event_type):
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

    @transaction.atomic
    def sync_event(self, user, region_name, tenant_name, record_event):
        app_version = rainbond_app_repo.get_rainbond_app_version_by_record_id(record_event.record_id)
        if not app_version:
            raise RbdAppNotFound("分享的应用不存在")
        event_type = "share-yb"
        if app_version.scope.startswith("goodrain"):
            event_type = "share-ys"
        event = self.create_publish_event(record_event, user.nick_name, event_type)
        record_event.event_id = event.event_id
        app_templetes = json.loads(app_version.app_template)
        apps = app_templetes.get("apps", None)
        if not apps:
            raise ServiceHandleException(msg="get share app info failed", msg_show="分享的应用信息获取失败", status_code=500)
        new_apps = list()
        sid = transaction.savepoint()
        try:
            for app in apps:
                # 处理事件的应用
                if app["service_key"] == record_event.service_key:
                    body = {
                        "service_key": app["service_key"],
                        "app_version": app_version.version,
                        "event_id": event.event_id,
                        "share_user": user.nick_name,
                        "share_scope": app_version.scope,
                        "image_info": app.get("service_image", None),
                        "slug_info": app.get("service_slug", None)
                    }
                    re_body = None
                    try:
                        res, re_body = region_api.share_service(region_name, tenant_name, record_event.service_alias, body)
                        bean = re_body.get("bean")
                        if bean:
                            record_event.region_share_id = bean.get("share_id", None)
                            record_event.event_id = bean.get("event_id", None)
                            record_event.event_status = "start"
                            record_event.update_time = datetime.datetime.now()
                            record_event.save()
                            image_name = bean.get("image_name", None)
                            if image_name:
                                app["share_image"] = image_name
                            slug_path = bean.get("slug_path", None)
                            if slug_path:
                                app["share_slug_path"] = slug_path
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
    def sync_service_plugin_event(self, user, region_name, tenant_name, record_id, record_event):
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
                    res, body = region_api.share_plugin(region_name, tenant_name, plugin["plugin_id"], body)
                    data = body.get("bean")
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

    def get_sync_plugin_events(self, region_name, tenant_name, record_event):
        res, body = region_api.share_plugin_result(region_name, tenant_name, record_event.plugin_id,
                                                   record_event.region_share_id)
        ret = body.get('bean')
        if ret and ret.get('status'):
            record_event.event_status = ret.get("status")
            record_event.save()
        return record_event

    def get_sync_event_result(self, region_name, tenant_name, record_event):
        res, re_body = region_api.share_service_result(region_name, tenant_name, record_event.service_alias,
                                                       record_event.region_share_id)
        bean = re_body.get("bean")
        if bean and bean.get("status", None):
            record_event.event_status = bean.get("status", None)
            record_event.save()
        return record_event

    def get_app_by_app_id(self, app_id):
        app = share_repo.get_app_by_app_id(app_id=app_id)
        if app:
            return 200, "应用包获取成功", app[0]
        else:
            return 400, '应用包不存在', None

    def get_app_by_key(self, key):
        app = share_repo.get_app_by_key(key)
        if app:
            return app[0]
        else:
            return None

    def delete_app(self, app):
        app.delete()

    def delete_record(self, record):
        record.delete()

    def create_service(self, **kwargs):
        return share_repo.create_service(**kwargs)

    def create_tenant_service(self, **kwargs):
        return share_repo.create_tenant_service(**kwargs)

    def create_tenant_service_port(self, **kwargs):
        return share_repo.create_tenant_service_port(**kwargs)

    def create_tenant_service_env_var(self, **kwargs):
        return share_repo.create_tenant_service_env_var(**kwargs)

    def create_tenant_service_volume(self, **kwargs):
        return share_repo.create_tenant_service_volume(**kwargs)

    def create_tenant_service_relation(self, **kwargs):
        return share_repo.create_tenant_service_relation(**kwargs)

    def create_tenant_service_plugin(self, **kwargs):
        return share_repo.create_tenant_service_plugin(**kwargs)

    def create_tenant_service_plugin_relation(self, **kwargs):
        return share_repo.create_tenant_service_plugin_relation(**kwargs)

    def create_tenant_service_extend_method(self, **kwargs):
        return share_repo.create_tenant_service_extend_method(**kwargs)

    def create_service_share_record(self, **kwargs):
        return share_repo.create_service_share_record(**kwargs)

    def get_service_share_record(self, group_share_id):
        return share_repo.get_service_share_record(group_share_id=group_share_id)

    def get_service_share_record_by_ID(self, ID, team_name):
        return share_repo.get_service_share_record_by_ID(ID=ID, team_name=team_name)

    def get_service_share_record_by_group_id(self, group_id):
        return share_repo.get_service_share_record_by_groupid(group_id=group_id)

    def get_plugins_group_items(self, plugins):
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
    def create_share_info(self, tenant, region_name, share_record, share_team, share_user, share_info, use_force):
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
                market = app_market_service.get_app_market_by_name(share_team.enterprise_id, market_id, raise_exception=True)
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
            governance_mode = app.governance_mode if app.governance_mode else GovernanceModeEnum.BUILD_IN_SERVICE_MESH.name

            app_template = {}
            # 处理基本信息
            try:
                app_template["template_version"] = "v2"
                app_template["group_key"] = app_model_id
                app_template["group_name"] = app_model_name
                app_template["group_version"] = version
                app_template["group_dev_status"] = ""
                app_template["governance_mode"] = governance_mode
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                raise ServiceHandleException(msg="Basic information processing error", msg_show="基本信息处理错误")

            # group config
            service_ids_keys_map = {svc["service_id"]: svc['service_key'] for svc in share_info["share_service_list"]}
            app_template["app_config_groups"] = self.config_groups(region_name, service_ids_keys_map)

            # ingress
            ingress_http_routes = self._list_http_ingresses(tenant, service_ids_keys_map)
            app_template["ingress_http_routes"] = ingress_http_routes

            # plugins
            try:
                # 确定分享的插件ID
                plugins = share_info.get("share_plugin_list", None)
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

                    shared_plugin_info = self.get_plugins_group_items(plugins)
                    app_template["plugins"] = shared_plugin_info
            except ServiceHandleException as e:
                raise e
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                return 500, "插件处理发生错误", None

            # 处理组件相关
            try:
                services = share_info["share_service_list"]
                if services:
                    new_services = list()
                    service_ids = [s["service_id"] for s in services]
                    version_list = base_service.get_apps_deploy_versions(services[0]["service_region"], share_team.tenant_name,
                                                                         service_ids)
                    delivered_type_map = {v["service_id"]: v["delivered_type"] for v in version_list}

                    dep_service_keys = {service['service_share_uuid'] for service in services}

                    for service in services:
                        delivered_type = delivered_type_map.get(service['service_id'], None)
                        if not delivered_type:
                            continue
                        if delivered_type == "slug":
                            service['service_slug'] = app_store.get_slug_hub_info(market, app_model_id,
                                                                                  share_team.enterprise_id)
                            service["share_type"] = "slug"
                            if not service['service_slug']:
                                if sid:
                                    transaction.savepoint_rollback(sid)
                                return 400, "获取源码包上传地址错误", None
                        else:
                            service["service_image"] = app_store.get_app_hub_info(market, app_model_id,
                                                                                  share_team.enterprise_id)
                            service["share_type"] = "image"
                            if not service["service_image"]:
                                if sid:
                                    transaction.savepoint_rollback(sid)
                                return 400, "获取镜像上传地址错误", None

                        # 处理依赖关系
                        self._handle_dependencies(service, dep_service_keys, use_force)

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
                else:
                    if sid:
                        transaction.savepoint_rollback(sid)
                    return 400, "分享的组件信息不能为空", None
            except ServiceHandleException as e:
                raise e
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                return 500, "组件信息处理发生错误", None
            share_record.scope = scope
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
                upgrade_time=time.time(),
            )
            if app_store.is_no_multiple_region_hub(enterprise_id=share_team.enterprise_id):
                app_version.region_name = region_name
            app_version.save()
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

    def _list_http_ingresses(self, tenant, component_keys):
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
    def _parse_cookie_or_header(cookies: str):
        # example: foo=bar;apple=pie
        cookies = cookies.replace(" ", "")
        result = {}
        for cookie in cookies.split(";"):
            kvs = cookie.split("=")
            if len(kvs) != 2 or kvs[0] == "" or kvs[1] == "":
                continue
            result[kvs[0]] = kvs[1]
        return result

    def config_groups(self, region_name, service_ids_keys_map):
        groups = app_config_group_repo.list_by_service_ids(region_name, service_ids_keys_map.keys())
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
    def _handle_dependencies(service, dev_service_set, use_force):
        """检查组件依赖信息，如果依赖不完整则中断请求， 如果强制执行则删除依赖"""

        def filter_dep(dev_service):
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

    def complete(self, tenant, user, share_record, is_plugin):
        # app = rainbond_app_repo.get_app_version_by_record_id(share_record.ID)
        app = share_repo.get_app_version_by_record_id(share_record.ID)
        app_market_url = None
        if app:
            # 分享到云市
            if app.scope.startswith("goodrain"):
                share_type = "private"
                info = app.scope.split(":")
                if len(info) > 1:
                    share_type = info[1]
                app_market_url = self.publish_app_to_public_market(tenant, share_record, user.nick_name, app, is_plugin,
                                                                   share_type)
            app.is_complete = True
            app.update_time = datetime.datetime.now()
            app.is_plugin = is_plugin
            app.save()
            RainbondCenterAppVersion.objects.filter(
                app_id=app.app_id, source="local", scope="goodrain", is_complete=True).delete()
            share_record.is_success = True
            share_record.step = 3
            share_record.status = 1
            share_record.update_time = datetime.datetime.now()
            share_record.save()
        # 应用有更新，删除导出记录
        app_export_record_repo.delete_by_key_and_version(app.app_id, app.version)
        return app_market_url

    def publish_app_to_public_market(self, tenant, share_record, user_name, app, is_plugin, share_type="private"):
        try:
            data = dict()
            data["description"] = app.app_version_info
            data["rainbond_version"] = os.getenv("RELEASE_DESC", "public-cloud")
            data["template"] = json.loads(app.app_template)
            data["template_type"] = app.template_type
            data["version"] = app.version
            data["version_alias"] = app.version_alias
            data['is_plugin'] = is_plugin
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
            market = app_market_service.get_app_market_by_name(
                tenant.enterprise_id, share_record.share_app_market_name, raise_exception=True)
            app_market_service.create_market_app_model_version(market, app.app_id, data)
            # 云市url
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                raise ServiceHandleException("no cloud permission", msg_show="云市授权不通过", status_code=403, error_code=10407)
            else:
                raise ServiceHandleException("call cloud api failure", msg_show="云市请求错误", status_code=500, error_code=500)

    @staticmethod
    def get_shared_services_list(service):
        data = {
            "group_name": service["group_name"],
            "group_key": service["group_key"],
        }
        return data

    @staticmethod
    def get_shared_services_versions_list(service):
        data = {
            "group_name": service.group_name,
            "group_key": service.group_key,
            "version": service.version,
        }
        return data

    @staticmethod
    def get_shared_services_records_list(service):
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

    def get_local_apps_versions(self):
        app_list = []
        apps = share_repo.get_local_apps()
        if apps:
            for app in apps:
                app_versions = list(set(share_repo.get_app_versions_by_app_id(app.app_id).values_list("version", flat=True)))
                app_list.append({
                    "app_name": app.app_name,
                    "app_id": app.app_id,
                    "pic": app.pic,
                    "app_describe": app.describe,
                    "dev_status": app.dev_status,
                    "version": app_versions,
                    "scope": app.scope,
                })
        return app_list

    def get_team_local_apps_versions(self, enterprise_id, team_name):
        app_list = []
        apps = share_repo.get_enterprise_team_apps(enterprise_id, team_name)
        if apps:
            for app in apps:
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

    def get_last_shared_app_and_app_list(self, enterprise_id, tenant, group_id, scope, market_name):
        last_shared = share_repo.get_last_shared_app_version_by_group_id(group_id, tenant.tenant_name, scope)
        dt = {}
        dt["app_model_list"] = []
        dt["last_shared_app"] = {}
        dt["scope"] = scope
        if scope == "goodrain":
            market = app_market_service.get_app_market_by_name(enterprise_id, market_name, raise_exception=True)
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
                last_shared_app_info = share_repo.get_app_by_app_id(last_shared.app_id)
                if last_shared_app_info:
                    self._patch_rainbond_app_tag(last_shared_app_info)
                    dt["last_shared_app"] = {
                        "app_name": last_shared_app_info.app_name,
                        "app_id": last_shared.app_id,
                        "version": last_shared.share_version,
                        "pic": last_shared_app_info.pic,
                        "app_describe": last_shared_app_info.describe,
                        "dev_status": last_shared_app_info.dev_status,
                        "scope": last_shared_app_info.scope,
                        "tags": last_shared_app_info.tags
                    }
            app_list = self.get_team_local_apps_versions(enterprise_id, tenant.tenant_name)
            self._patch_rainbond_apps_tag(enterprise_id, app_list)
            dt["app_model_list"] = app_list
        return dt

    # patch rainbond app tag
    def _patch_rainbond_app_tag(self, app):
        tags = app_tag_repo.get_app_with_tags(app.enterprise_id, app.app_id)
        app.tags = []
        if not tags:
            return
        for tag in tags:
            app.tags.append({"tag_id": tag.ID, "name": tag.name})

    # patch rainbond app tag
    def _patch_rainbond_apps_tag(self, eid, apps):
        app_ids = [app["app_id"] for app in apps]
        tags = app_tag_repo.get_multi_apps_tags(eid, app_ids)
        if not tags:
            return
        app_with_tags = dict()
        for tag in tags:
            if not app_with_tags.get(tag.app_id):
                app_with_tags[tag.app_id] = []
            app_with_tags[tag.app_id].append({"tag_id": tag.ID, "name": tag.name})

        for app in apps:
            app["tags"] = app_with_tags.get(app["app_id"])

    def get_last_shared_app_version(self, tenant, group_id, scope=None):
        last_shared = share_repo.get_last_shared_app_version_by_group_id(group_id, tenant.tenant_name, scope)
        if not last_shared:
            return None, None
        if last_shared.scope == "goodrain":
            try:
                market = app_market_service.get_app_market_by_name(
                    tenant.enterprise_id, last_shared.share_app_market_name, raise_exception=True)
                app_version = app_market_service.get_market_app_model_version(
                    market, last_shared.app_id, last_shared.share_version, get_template=True)
            except ServiceHandleException as e:
                logger.debug(e)
                return None, None
            dt = (json.loads(app_version.template), app_version.app_version_info)
        else:
            app_version = share_repo.get_app_version(last_shared.app_id, last_shared.share_version)
            if not app_version:
                return None, None
            dt = (json.loads(app_version.app_template), app_version.app_version_info)
        return dt

    def create_cloud_app(self, tenant, market_name, data):
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


share_service = ShareService()
