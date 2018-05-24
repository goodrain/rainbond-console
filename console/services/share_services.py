# -*- coding: utf-8 -*-
import logging

from console.models.main import RainbondCenterApp, ServiceShareRecordEvent
from console.appstore.appstore import app_store
from console.services.service_services import base_service
from www.apiclient.marketclient import MarketOpenAPI
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.share_repo import share_repo
from console.repositories.plugin import plugin_repo
from www.models import TenantServiceInfo, ServiceEvent, make_uuid
from www.services import tenant_svc
from console.services.plugin import plugin_service
from www.utils.json_tool import json_dump
from django.db import transaction
from console.constants import AppConstants
import json
import datetime
from console.repositories.market_app_repo import rainbond_app_repo

logger = logging.getLogger("default")

region_api = RegionInvokeApi()


class ShareService(object):
    def check_service_source(self, team, team_name, group_id, region_name):
        service_list = share_repo.get_service_list_by_group_id(team=team, group_id=group_id)
        if service_list:
            can_publish_list = [
                service for service in service_list if service.service_source != "market"
            ]
            if not can_publish_list:
                data = {"code": 400, "success": False, "msg_show": "此组中的应用全部来源于云市,无法发布",
                        "list": list(), "bean": dict()}
                return data
            else:
                # 批量查询应用状态
                service_ids = [service.service_id for service in service_list]
                status_list = base_service.status_multi_service(region=region_name, tenant_name=team_name,
                                                                service_ids=service_ids, enterprise_id=team.enterprise_id)
                for status in status_list:
                    if status["status"] != "running":
                        data = {"code": 400, "success": False, "msg_show": "您有应用未在运行状态不能发布。",
                                "list": list(), "bean": dict()}
                        return data
                    else:
                        data = {"code": 200, "success": True, "msg_show": "您的应用都在运行中可以发布。",
                                "list": list(), "bean": dict()}
                        return data
        else:
            data = {"code": 400, "success": False, "msg_show": "当前组内无应用", "list": list(), "bean": dict()}
            return data

    def check_whether_have_share_history(self, group_id):
        return share_repo.get_rainbond_cent_app_by_tenant_service_group_id(group_id=group_id)

    def get_service_ports_by_ids(self, service_ids):
        """
        根据多个服务ID查询服务的端口信息
        :param service_ids: 应用ID列表
        :return: {"service_id":TenantServicesPort[object]}
        """
        port_list = share_repo.get_port_list_by_service_ids(service_ids=service_ids)
        if port_list:
            service_port_map = {}
            for port in port_list:
                service_id = port.service_id
                tmp_list = []
                if service_id in service_port_map.keys():
                    tmp_list = service_port_map.get(service_id)
                tmp_list.append(port)
                service_port_map[service_id] = tmp_list
            return service_port_map
        else:
            return {}

    def get_service_dependencys_by_ids(self, service_ids):
        """
        根据多个服务ID查询服务的依赖服务信息
        :param service_ids:应用ID列表
        :return: {"service_id":TenantServiceInfo[object]}
        """
        relation_list = share_repo.get_relation_list_by_service_ids(service_ids=service_ids)
        if relation_list:
            dep_service_map = {}
            for dep_service in relation_list:
                service_id = dep_service.service_id
                tmp_list = []
                if service_id in dep_service_map.keys():
                    tmp_list = dep_service_map.get(service_id)
                dep_service_info = TenantServiceInfo.objects.filter(service_id=dep_service.dep_service_id)[0]
                tmp_list.append(dep_service_info)
                dep_service_map[service_id] = tmp_list
            return dep_service_map
        else:
            return {}

    def get_service_env_by_ids(self, service_ids):
        """
        获取应用env
        :param service_ids: 应用ID列表
        # :return: 可修改的环境变量service_env_change_map，不可修改的环境变量service_env_nochange_map
        :return: 环境变量service_env_map
        """
        env_list = share_repo.get_env_list_by_service_ids(service_ids=service_ids)
        if env_list:
            service_env_map = {}
            for env in env_list:
                service_id = env.service_id
                tmp_list = []
                if service_id in service_env_map.keys():
                    tmp_list = service_env_map.get(service_id)
                tmp_list.append(env)
                service_env_map[service_id] = tmp_list
            return service_env_map
        else:
            return {}

    def get_service_volume_by_ids(self, service_ids):
        """
        获取应用持久化目录
        """
        volume_list = share_repo.get_volume_list_by_service_ids(service_ids=service_ids)
        if volume_list:
            service_volume_map = {}
            for volume in volume_list:
                service_id = volume.service_id
                tmp_list = []
                if service_id in service_volume_map.keys():
                    tmp_list = service_volume_map.get(service_id)
                tmp_list.append(volume)
                service_volume_map[service_id] = tmp_list
            return service_volume_map
        else:
            return {}

    def get_service_extend_method_by_keys(self, service_keys):
        """
        获取应用伸缩状态
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
        获取应用健康检测探针
        """
        probe_list = share_repo.get_probe_list_by_service_ids(service_ids=service_ids)
        if probe_list:
            service_probe_map = {}
            for probe in probe_list:
                service_id = probe.service_id
                tmp_list = []
                if service_id in service_probe_map.keys():
                    tmp_list = service_probe_map.get(service_id)
                tmp_list.append(probe)
                service_probe_map[service_id] = tmp_list
            return service_probe_map
        else:
            return {}

    def query_share_service_info(self, team, group_id):
        service_list = share_repo.get_service_list_by_group_id(team=team, group_id=group_id)
        if service_list:
            array_ids = [x.service_id for x in service_list]
            array_keys = []
            for x in service_list:
                if x.service_key == "application" or x.service_key == "0000" or x.service_key == "":
                    array_keys.append(x.service_key)
            # 查询服务端口信息
            service_port_map = self.get_service_ports_by_ids(array_ids)
            # 查询服务依赖
            dep_service_map = self.get_service_dependencys_by_ids(array_ids)
            # 查询服务可变参数和不可变参数
            # service_env_change_map, service_env_nochange_map = self.get_service_env_by_ids(array_ids)
            service_env_map = self.get_service_env_by_ids(array_ids)
            # 查询服务持久化信息
            service_volume_map = self.get_service_volume_by_ids(array_ids)
            # 查询服务伸缩方式信息
            extend_method_map = self.get_service_extend_method_by_keys(array_keys)
            # 获取应用的健康检测设置
            probe_map = self.get_service_probes(array_ids)

            all_data_map = {}
            for service in service_list:
                data = dict()
                data['service_id'] = service.service_id
                data['tenant_id'] = service.tenant_id
                data['service_cname'] = service.service_cname
                data['service_key'] = service.service_key
                if service.service_source != AppConstants.MARKET:
                    data['service_key'] = make_uuid()
                #     data['need_share'] = True
                # else:
                #     data['need_share'] = False
                data['need_share'] = True
                data['category'] = service.category
                data['language'] = service.language
                data['extend_method'] = service.extend_method
                data['version'] = service.version
                data['memory'] = service.min_memory
                data['service_type'] = service.service_type
                data['service_source'] = service.service_source
                data['deploy_version'] = service.deploy_version
                data['image'] = service.image
                data['service_alias'] = service.service_alias
                data['service_region'] = service.service_region
                data['creater'] = service.creater
                data["cmd"] = service.cmd
                data['probes'] = [probe.to_dict() for probe in probe_map.get(service.service_id, [])]
                extend_method = extend_method_map.get(service.service_key)
                if extend_method:
                    e_m = dict()
                    e_m['min_node'] = extend_method.min_node
                    e_m['max_node'] = extend_method.max_node
                    e_m['step_node'] = extend_method.step_node
                    e_m['min_memory'] = extend_method.min_memory
                    e_m['max_memory'] = extend_method.max_memory
                    e_m['step_memory'] = extend_method.step_memory
                    e_m['is_restart'] = extend_method.is_restart
                    data['extend_method_map'] = e_m
                else:
                    data['extend_method_map'] = {
                        "min_node": 1,
                        "max_node": 20,
                        "step_node": 1,
                        "min_memory": 128,
                        "max_memory": 65536,
                        "step_memory": 128,
                        "is_restart": 0
                    }
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
                        data['port_map_list'].append(p)

                data['service_volume_map_list'] = list()
                if service_volume_map.get(service.service_id):
                    for volume in service_volume_map.get(service.service_id):
                        s_v = dict()
                        s_v['category'] = volume.category
                        s_v['volume_type'] = volume.volume_type
                        s_v['volume_path'] = volume.volume_path
                        s_v['volume_name'] = volume.volume_name
                        data['service_volume_map_list'].append(s_v)

                data['service_env_map_list'] = list()
                data['service_connect_info_map_list'] = list()
                if service_env_map.get(service.service_id):
                    for env_change in service_env_map.get(service.service_id):
                        if env_change.container_port == 0:
                            e_c = dict()
                            e_c['name'] = env_change.name
                            e_c['attr_name'] = env_change.attr_name
                            e_c['attr_value'] = env_change.attr_value
                            e_c['is_change'] = env_change.is_change
                            if env_change.scope == "outer":
                                e_c['container_port'] = env_change.container_port
                                data['service_connect_info_map_list'].append(e_c)
                            else:
                                data['service_env_map_list'].append(e_c)
                service_ids = [x.service_id for x in service_list]
                plugins_attr_list = share_repo.get_plugins_attr_by_service_ids(service_ids=service_ids)
                plugins_relation_list = share_repo.get_plugins_relation_by_service_ids(service_ids=service_ids)
                data['plugin_map_list'] = list()
                for p_relation in plugins_relation_list:
                    plugin_data = dict()
                    if service.service_id == p_relation.service_id:
                        plugin_data['plugin_id'] = p_relation.plugin_id
                        plugin_data['build_version'] = p_relation.build_version
                        plugin_data['service_meta_type'] = p_relation.service_meta_type
                        plugin_data['plugin_status'] = p_relation.plugin_status
                        plugin_data['create_time'] = p_relation.create_time
                        plugin_data["attr"] = list()
                        for p_attr in plugins_attr_list:
                            if p_relation.service_id == p_attr.service_id:
                                attr_data = {}
                                attr_data['dest_service_id'] = p_attr.dest_service_id
                                attr_data['dest_service_alias'] = p_attr.dest_service_alias
                                attr_data['container_port'] = p_attr.container_port
                                attr_data['attr_name'] = p_attr.attr_name
                                attr_data['attr_value'] = p_attr.attr_value
                                attr_data['attr_alt_value'] = p_attr.attr_alt_value
                                attr_data['attr_type'] = p_attr.attr_type
                                attr_data['attr_default_value'] = p_attr.attr_default_value
                                attr_data['protocol'] = p_attr.protocol
                                attr_data['attr_info'] = p_attr.attr_info
                                plugin_data["attr"].append(attr_data)
                    data['plugin_map_list'].append(plugin_data)
                all_data_map[service.service_id] = data

            all_data = list()
            for service_id in all_data_map:
                service = all_data_map[service_id]
                service['dep_service_map_list'] = list()
                if dep_service_map.get(service['service_id']):
                    for dep in dep_service_map.get(service['service_id']):
                        d = dict()
                        if all_data_map.get(dep.service_id):
                            d['dep_service_key'] = all_data_map[dep.service_id]['service_key']
                            service['dep_service_map_list'].append(d)
                all_data.append(service)
            return all_data
        else:
            return []

    # 查询应用组内使用的插件列表
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
        rc_apps = RainbondCenterApp.objects.filter(record_id=record_event.record_id)
        if not rc_apps:
            return 404, "分享的应用不存在", None
        rc_app = rc_apps[0]
        event_type = "share-yb"
        if rc_app.scope == "goodrain":
            event_type = "share-ys"
        event = self.create_publish_event(record_event, user.nick_name, event_type)
        record_event.event_id = event.event_id
        app_templetes = json.loads(rc_app.app_template)
        apps = app_templetes.get("apps", None)
        if not apps:
            return 500, "分享的应用信息获取失败", None
        new_apps = list()
        sid = transaction.savepoint()
        try:
            for app in apps:
                # 处理事件的应用
                if app["service_key"] == record_event.service_key:
                    body = {
                        "service_key": app["service_key"],
                        "app_version": rc_app.version,
                        "event_id": event.event_id,
                        "share_user": user.nick_name,
                        "share_scope": rc_app.scope,
                        "image_info": app.get("service_image", None),
                        "slug_info": app.get("service_slug", None)
                    }
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
                            return 400, "数据中心分享错误", None
                    except Exception as e:
                        logger.exception(e)
                        transaction.savepoint_rollback(sid)
                        if re_body:
                            logger.error(re_body)
                        return 500, "数据中心分享错误", None
                else:
                    new_apps.append(app)  
            app_templetes["apps"] = new_apps
            rc_app.app_template = json.dumps(app_templetes)
            rc_app.update_time = datetime.datetime.now()
            rc_app.save()
            transaction.savepoint_commit(sid)
            return 200, "数据中心分享开始", record_event
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            return 500, "应用分享介质同步发生错误", None

    def get_sync_event_result(self, region_name, tenant_name, record_event):
        res, re_body = region_api.share_service_result(region_name, tenant_name, record_event.service_alias, record_event.region_share_id)
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

    def upate_app_complete_by_app_id(self, app_id, data):
        app = share_repo.get_app_by_app_id(app_id=app_id)
        is_complete = False
        if app.scope == 'goodrain':
            app.scope = data["GRYS"]
            is_complete = True
        elif app.scope == 'team' or app.scope == 'enterprise':
            app.scope = data["GRYB"]
            is_complete = True
        app.is_complete = is_complete
        app.save()

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

    # 创建应用分享记录
    # 创建应用记录
    # 创建介质同步记录
    @transaction.atomic
    def create_share_info(self, share_record, share_team, share_user, share_info):
        # 开启事务
        sid = transaction.savepoint()
        try:
            # 删除历史数据
            ServiceShareRecordEvent.objects.filter(record_id=share_record.ID).delete()
            RainbondCenterApp.objects.filter(record_id=share_record.ID).delete()
            app_templete = {}
            # 处理基本信息
            try:
                app_templete["template_version"] = "v2"
                group_info = share_info["share_group_info"]
                app_templete["group_key"] = group_info["group_key"]
                app_templete["group_name"] = group_info["group_name"]
                app_templete["group_version"] = group_info["version"]
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                return 500, "基本信息处理错误", None
            # 处理插件相关,v3.5暂时不实现
            try:
                # 确定分享的插件ID
                share_plugin_ids = {}
                plugins = share_info.get("share_plugin_list", None)
                if plugins:
                    share_plugins = list()
                    for plugin in plugins:
                        version = plugin.get("build_version", "")
                        plugin_id = plugin.get("plugin_id", "")
                        if version and plugin_id:
                            # 只有自己创建的插件需要分享出去
                            if plugin["origin"] == "source_code" and plugin["is_share"]:
                                plugin_version = plugin_repo.get_plugin_buildversion(
                                    plugin_id, version)
                                if plugin_version and plugin_version.plugin_version_status != "fixed":
                                    plugin_version.plugin_version_status = "fixed"
                                    plugin_version.save()
                                plugin["config_groups"] = [
                                    group.to_dict()
                                    for group in plugin_repo.get_plugin_config_groups(
                                        plugin_id, version)
                                ]
                                plugin["config_items"] = [
                                    item.to_dict()
                                    for item in plugin_repo.get_plugin_config_items(
                                        plugin_id, version)
                                ]
                                plugin["version"] = plugin_version.to_dict()
                                # TODO: 插件应该单独分享，此处暂时不处理，分享到应用内部
                                share_plugin_ids[plugin_id] = True
                                share_plugins.append(plugin)
                    app_templete["plugins"] = share_plugins
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                return 500, "插件处理发生错误", None
            # 处理应用相关
            try:
                services = share_info["share_service_list"]
                if services:
                    new_services = list()
                    for service in services:
                        image = service["image"]
                        # 源码应用
                        if image.startswith("goodrain.me/runner") and service["language"] != "dockerfile":
                            service['service_slug'] = app_store.get_slug_connection_info(group_info["scope"], share_team.tenant_name)
                            if not service['service_slug']:
                                if sid:
                                    transaction.savepoint_rollback(sid)
                                return 400, "获取源码包上传地址错误", None
                        else:
                            service["service_image"] = app_store.get_image_connection_info(group_info["scope"], share_team.tenant_name)
                            if not service["service_image"]:
                                if sid:
                                    transaction.savepoint_rollback(sid)
                                return 400, "获取镜像上传地址错误", None
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
                        # TODO:处理应用继承关系RainbondCenterAppInherit
                    app_templete["apps"] = new_services
                else:
                    if sid:
                        transaction.savepoint_rollback(sid)
                    return 400, "分享的应用信息不能为空", None
            except Exception as e:
                if sid:
                    transaction.savepoint_rollback(sid)
                logger.exception(e)
                return 500, "应用信息处理发生错误", None
            # 删除同个应用组分享的相同版本
            RainbondCenterApp.objects.filter(version=group_info["version"], tenant_service_group_id=share_record.group_id).delete()
            # 新增加
            app = RainbondCenterApp(
                group_key=app_templete["group_key"],
                group_name=app_templete["group_name"],
                share_user=share_user.user_id,
                share_team=share_team.tenant_name,
                tenant_service_group_id=share_record.group_id,
                pic=group_info.get("pic",""),
                source="local",
                record_id=share_record.ID,
                version=group_info["version"],
                scope=group_info["scope"],
                describe=group_info["describe"],
                app_template=json.dumps(app_templete))
            app.save()
            share_record.step = 2
            share_record.update_time = datetime.datetime.now()
            share_record.save()
            # 提交事务
            if sid:
                transaction.savepoint_commit(sid)
            return 200, "分享信息处理成功", share_record.to_dict()
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            return 500, "应用分享处理发生错误", None

    def complete(self, tenant, user, share_record):
        app = rainbond_app_repo.get_rainbond_app_by_record_id(share_record.ID)
        app_market_url = None
        if app:
            # 分享到云市
            if app.scope == "goodrain":
                app_market_url = self.publish_app_to_public_market(tenant, user.nick_name, app)
            app.is_complete = True
            app.update_time = datetime.datetime.now()
            app.save()
            share_record.is_success = True
            share_record.step = 3
            share_record.update_time = datetime.datetime.now()
            share_record.save()
        return app_market_url

    def publish_app_to_public_market(self, tenant, user_name, app):
        market_api = MarketOpenAPI()
        data = dict()
        data["tenant_id"] = tenant.tenant_id
        data["group_key"] = app.group_key
        data["group_version"] = app.version
        data["template_version"] = app.template_version
        data["publish_user"] = user_name
        data["publish_team"] = tenant.tenant_alias
        data["update_note"] = app.describe
        data["group_template"] = app.app_template
        data["group_share_alias"] = app.group_name
        data["logo"] = app.pic
        result = market_api.publish_v2_template_group_data(tenant.tenant_id, data)
        # 云市url
        app_url = result["app_url"]
        return app_url


share_service = ShareService()
