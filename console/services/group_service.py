# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging
import re

from console.exception.bcode import ErrUserNotFound
from console.exception.main import AbortRequest, ServiceHandleException
from console.exception.bcode import ErrK8sServiceNameExists
from console.repositories.app import service_repo, service_source_repo
from console.repositories.app_config import (domain_repo, port_repo, tcp_domain)
from console.repositories.backup_repo import backup_record_repo
from console.repositories.compose_repo import compose_repo
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.region_app import region_app_repo
from console.repositories.region_repo import region_repo
from console.repositories.share_repo import share_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.repositories.user_repo import user_repo
from console.services.app_config_group import app_config_group_service
from console.services.service_services import base_service
from console.utils.shortcuts import get_object_or_404
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import RegionApp, ServiceGroup, ServiceGroupRelation

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class GroupService(object):
    def get_tenant_groups_by_region(self, tenant, region_name):
        return group_repo.list_tenant_group_on_region(tenant, region_name)

    @staticmethod
    def check_app_name(tenant, region_name, group_name):
        if not group_name:
            raise ServiceHandleException(msg="app name required", msg_show="应用名不能为空")
        if len(group_name) > 128:
            raise ServiceHandleException(msg="app_name illegal", msg_show="应用名称最多支持128个字符")
        r = re.compile('^[a-zA-Z0-9_\\.\\-\\u4e00-\\u9fa5]+$')
        if not r.match(group_name):
            raise ServiceHandleException(msg="app_name illegal", msg_show="应用名称只支持中英文, 数字, 下划线, 中划线和点")

    @transaction.atomic
    def create_app(self, tenant, region_name, app_name, note="", username="", re_model=False):
        app = self.__add_group(tenant, region_name, app_name, note, username)
        self.create_region_app(tenant, region_name, app)
        res = app.to_dict()
        # compatible with the old version
        res["group_id"] = app.ID
        res['app_id'] = app.ID
        res['app_name'] = app.group_name
        if re_model:
            return res, app
        return res

    def create_default_app(self, tenant, region_name):
        app = group_repo.get_or_create_default_group(tenant.tenant_id, region_name)
        self.create_region_app(tenant, region_name, app)
        return app.to_dict()

    def __add_group(self, tenant, region_name, app_name, note="", username=""):
        self.check_app_name(tenant, region_name, app_name)
        if group_repo.get_group_by_unique_key(tenant.tenant_id, region_name, app_name):
            raise ServiceHandleException(msg="app name exist", msg_show="应用名称已存在")
        return group_repo.add_group(tenant.tenant_id, region_name, app_name, group_note=note, username=username)

    def create_region_app(self, tenant, region_name, app):
        region_app = region_api.create_application(region_name, tenant.tenant_name, {
            "app_name": app.group_name,
        })

        # record the dependencies between region app and console app
        data = {
            "region_name": region_name,
            "region_app_id": region_app["app_id"],
            "app_id": app.ID,
        }
        region_app_repo.create(**data)

    def update_group(self, tenant, region_name, app_id, app_name, note="", username=None):
        # check app id
        if not app_id or not str.isdigit(app_id) or int(app_id) < 0:
            raise ServiceHandleException(msg="app id illegal", msg_show="应用ID不合法")
        # check username
        if username:
            try:
                data = {"username": username}
                user_repo.get_user_by_username(username)
                group_repo.update(app_id, **data)
                return
            except ErrUserNotFound:
                raise ServiceHandleException(msg="user not exists", msg_show="用户不存在,请选择其他应用负责人", status_code=404)
        # check app name
        self.check_app_name(tenant, region_name, app_name)
        group = group_repo.get_group_by_unique_key(tenant.tenant_id, region_name, app_name)
        if group and int(group.ID) != int(app_id):
            raise ServiceHandleException(msg="app already exists", msg_show="应用名{0}已存在".format(app_name))
        data = {
            "note": note,
        }
        if app_name:
            data["group_name"] = app_name
        group_repo.update(app_id, **data)

    def delete_group(self, group_id, default_group_id):
        if not group_id or not str.isdigit(group_id) or int(group_id) < 0:
            return 400, "需要删除的应用不合法", None
        backups = backup_record_repo.get_record_by_group_id(group_id)
        if backups:
            return 409, "当前应用有备份记录，暂无法删除", None
        # 删除应用
        group_repo.delete_group_by_pk(group_id)
        # 删除应用与应用的关系
        group_service_relation_repo.update_service_relation(group_id, default_group_id)
        return 200, "删除成功", group_id

    def add_service_to_group(self, tenant, region_name, group_id, service_id):
        if group_id:
            group_id = int(group_id)
            if group_id > 0:
                group = group_repo.get_group_by_pk(tenant.tenant_id, region_name, group_id)
                if not group:
                    return 404, "应用不存在"
                group_service_relation_repo.add_service_group_relation(group_id, service_id, tenant.tenant_id, region_name)
        return 200, "success"

    def sync_app_services(self, tenant, region_name, app_id):
        group_services = base_service.get_group_services_list(tenant.tenant_id, region_name, app_id)
        service_ids = []
        if group_services:
            for service in group_services:
                service_ids.append(service["service_id"])

        try:
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
            body = {"service_ids": service_ids}
            region_api.batch_update_service_app_id(region_name, tenant.tenant_name, region_app_id, body)
        except RegionApp.DoesNotExist:
            app = group_repo.get_group_by_id(app_id)
            create_body = {"app_name": app.group_name, "service_ids": service_ids}
            bean = region_api.create_application(region_name, tenant, create_body)
            req = {"region_name": region_name, "region_app_id": bean["app_id"], "app_id": app_id}
            region_app_repo.create(**req)

    def get_app_detail(self, tenant, region_name, app_id):
        # app metadata
        app = group_repo.get_group_by_pk(tenant.tenant_id, region_name, app_id)

        self.sync_app_services(tenant, region_name, app_id)

        res = app.to_dict()
        res['app_id'] = app.ID
        res['app_name'] = app.group_name
        res['service_num'] = group_service_relation_repo.count_service_by_app_id(app_id)
        res['backup_num'] = backup_record_repo.count_by_app_id(app_id)
        res['share_num'] = share_repo.count_by_app_id(app_id)
        res['ingress_num'] = self.count_ingress_by_app_id(tenant.tenant_id, region_name, app_id)
        res['config_group_num'] = app_config_group_service.count_by_app_id(region_name, app_id)

        try:
            principal = user_repo.get_user_by_username(app.username)
            res['principal'] = principal.get_name()
            res['email'] = principal.email
        except ErrUserNotFound:
            res['principal'] = app.username

        res["create_status"] = "complete"
        res["compose_id"] = None
        if app_id != -1:
            compose_group = compose_repo.get_group_compose_by_group_id(app_id)
            if compose_group:
                res["create_status"] = compose_group.create_status
                res["compose_id"] = compose_group.compose_id

        return res

    def get_group_by_id(self, tenant, region, group_id):
        principal_info = dict()
        principal_info["email"] = ""
        principal_info["is_delete"] = False
        group = group_repo.get_group_by_pk(tenant.tenant_id, region, group_id)
        if not group:
            raise ServiceHandleException(status_code=404, msg="app not found", msg_show="目标应用不存在")
        try:
            user = user_repo.get_user_by_username(group.username)
            principal_info["real_name"] = user.get_name()
            principal_info["username"] = user.nick_name
            principal_info["email"] = user.email
        except ErrUserNotFound:
            principal_info["is_delete"] = True
            principal_info["real_name"] = group.username
            principal_info["username"] = group.username
        return {"group_id": group.ID, "group_name": group.group_name, "group_note": group.note, "principal": principal_info}

    def get_app_by_id(self, tenant, region, app_id):
        return group_repo.get_group_by_pk(tenant.tenant_id, region, app_id)

    def get_group_or_404(self, tenant, response_region, group_id):
        """
        :param tenant:
        :param response_region:
        :param group_id:
        :rtype: ServiceGroup
        """
        return get_object_or_404(
            ServiceGroup,
            msg="Group does not exist",
            msg_show="应用不存在",
            tenant_id=tenant.tenant_id,
            region_name=response_region,
            pk=group_id)

    def get_service_group_info(self, service_id):
        return group_service_relation_repo.get_group_info_by_service_id(service_id)

    def get_services_group_name(self, service_ids):
        return group_service_relation_repo.get_group_by_service_ids(service_ids)

    def delete_service_group_relation_by_service_id(self, service_id):
        group_service_relation_repo.delete_relation_by_service_id(service_id)

    def update_or_create_service_group_relation(self, tenant, service, group_id):
        gsr = group_service_relation_repo.get_group_by_service_id(service.service_id)
        if gsr:
            gsr.group_id = group_id
            gsr.save()
        else:
            params = {
                "service_id": service.service_id,
                "group_id": group_id,
                "tenant_id": tenant.tenant_id,
                "region_name": service.service_region
            }
            group_service_relation_repo.create_service_group_relation(**params)

    def get_groups_and_services(self, tenant, region, query=""):
        groups = group_repo.get_tenant_region_groups(tenant.tenant_id, region, query)
        services = service_repo.get_tenant_region_services(region, tenant.tenant_id).values(
            "service_id", "service_cname", "service_alias")
        service_id_map = {s["service_id"]: s for s in services}
        service_group_relations = group_service_relation_repo.get_service_group_relation_by_groups([g.ID for g in groups])
        service_group_map = {sgr.service_id: sgr.group_id for sgr in service_group_relations}
        group_services_map = dict()
        for k, v in list(service_group_map.items()):
            service_list = group_services_map.get(v, None)
            service_info = service_id_map.get(k, None)
            if service_info:
                if not service_list:
                    group_services_map[v] = [service_info]
                else:
                    service_list.append(service_info)
                service_id_map.pop(k)

        result = []
        for g in groups:
            bean = dict()
            bean["group_id"] = g.ID
            bean["group_name"] = g.group_name
            bean["service_list"] = group_services_map.get(g.ID)
            result.insert(0, bean)

        return result

    def get_group_services(self, group_id):
        """查询某一应用下的组件"""
        gsr = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = [gs.service_id for gs in gsr]
        services = service_repo.get_services_by_service_ids(service_ids)
        return services

    def get_multi_apps_all_info(self, app_ids, region, tenant_name, enterprise_id):
        app_list = group_repo.get_multi_app_info(app_ids)
        service_list = service_repo.get_services_in_multi_apps_with_app_info(app_ids)
        # memory info
        service_ids = [service.service_id for service in service_list]
        status_list = base_service.status_multi_service(region, tenant_name, service_ids, enterprise_id)
        service_status = dict()
        if status_list is None:
            raise ServiceHandleException(msg="query status failure", msg_show="查询组件状态失败")
        for status in status_list:
            service_status[status["service_id"]] = status

        for service in service_list:
            svc_sas = service_status.get(service.service_id, {"status": "failure", "used_mem": 0})
            service.status = svc_sas["status"]
            service.used_mem = svc_sas["used_mem"]

        plugin_list = app_plugin_relation_repo.get_multi_service_plugin(service_ids)
        plugins = dict()
        for plugin in plugin_list:
            if not plugins.get(plugin.service_id):
                plugins[plugin.service_id] = 0
            if plugin.plugin_status:
                # if plugin is turn on means component is using this plugin
                plugins[plugin.service_id] += plugin.min_memory

        apps = dict()
        for app in app_list:
            apps[app.ID] = {
                "group_id": app.ID,
                "update_time": app.update_time,
                "create_time": app.create_time,
                "group_name": app.group_name,
                "group_note": app.note,
                "service_list": [],
            }
        for service in service_list:
            # memory used for plugin
            service.min_memory += plugins.get(service.service_id, 0)
            apps[service.group_id]["service_list"].append(service)

        share_list = share_repo.get_multi_app_share_records(app_ids)
        share_records = dict()
        for share_info in share_list:
            if not share_records.get(int(share_info.group_id)):
                share_records[int(share_info.group_id)] = {"share_app_num": 0}
            if share_info:
                share_records[int(share_info.group_id)]["share_app_num"] += 1

        backup_list = backup_record_repo.get_multi_apps_backup_records(app_ids)
        backup_records = dict()
        for backup_info in backup_list:
            if not backup_records.get(int(backup_info.group_id)):
                backup_records[int(backup_info.group_id)] = {"backup_record_num": 0}
            backup_records[int(backup_info.group_id)]["backup_record_num"] += 1

        re_app_list = []
        for a in app_list:
            group_id = a.ID
            app = apps.get(a.ID)
            app["share_record_num"] = share_records[group_id]["share_app_num"] if share_records.get(group_id) else 0
            app["backup_record_num"] = backup_records[group_id]["backup_record_num"] if backup_records.get(group_id) else 0
            app["services_num"] = len(app["service_list"])
            if not app.get("run_service_num"):
                app["run_service_num"] = 0
            if not app.get("used_mem"):
                app["used_mem"] = 0
            if not app.get("allocate_mem"):
                app["allocate_mem"] = 0
            for svc in app["service_list"]:
                app["allocate_mem"] += svc.min_memory
                if svc.status in ["running", "upgrade", "starting", "some_abnormal"]:
                    # if is running used_mem ++
                    app["used_mem"] += svc.min_memory
                    app["run_service_num"] += 1
            app.pop("service_list")
            re_app_list.append(app)
        return re_app_list

    def get_rainbond_services(self, group_id, group_key):
        """获取云市应用下的所有组件"""
        gsr = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = gsr.values_list('service_id', flat=True)
        return service_repo.get_services_by_service_ids_and_group_key(group_key, service_ids)

    def get_group_service_sources(self, group_id):
        """查询某一应用下的组件源信息"""
        gsr = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = gsr.values_list('service_id', flat=True)
        return service_source_repo.get_service_sources_by_service_ids(service_ids)

    def get_group_service_source(self, service_id):
        """ get only one service source"""
        return service_source_repo.get_service_sources_by_service_ids([service_id])

    def get_service_source_by_group_key(self, group_key):
        """ geet service source by group key"""
        return service_source_repo.get_service_sources_by_group_key(group_key)

    # 应用内没有组件情况下删除应用
    @transaction.atomic
    def delete_group_no_service(self, group_id):
        if not group_id or (type(group_id) == str and not str.isdigit(group_id)) or int(group_id) < 0:
            return 400, "需要删除的应用ID不合法", None
        # 删除应用
        group_repo.delete_group_by_pk(group_id)
        # 删除升级记录
        upgrade_repo.delete_app_record_by_group_id(group_id)

        return 200, "删除成功", group_id

    def get_service_group_memory(self, app_template):
        """获取一应用组件内存"""
        try:
            apps = app_template["apps"]
            total_memory = 0
            for app in apps:
                extend_method_map = app.get("extend_method_map", None)
                if extend_method_map and extend_method_map["init_memory"]:
                    total_memory += extend_method_map["min_node"] * extend_method_map["init_memory"]
                elif extend_method_map and extend_method_map["min_memory"]:
                    total_memory += extend_method_map["min_node"] * extend_method_map["min_memory"]
                else:
                    total_memory += 128
            return total_memory
        except Exception as e:
            logger.debug("==============================>{0}".format(e))
            return 0

    def get_apps_list(self, team_id=None, region_name=None, query=None):
        return group_repo.get_apps_list(team_id, region_name, query)

    # get apps by service ids
    # return app id and service id maps
    def get_app_id_by_service_ids(self, service_ids):
        sgr = ServiceGroupRelation.objects.filter(service_id__in=service_ids)
        return {s.service_id: s.group_id for s in sgr}

    def count_ingress_by_app_id(self, tenant_id, region_name, app_id):
        # list service_ids
        service_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant_id, region_name, app_id)
        if not service_ids:
            return 0

        region = region_repo.get_by_region_name(region_name)

        # count ingress
        return domain_repo.count_by_service_ids(region.region_id, service_ids) + tcp_domain.count_by_service_ids(
            region.region_id, service_ids)

    def set_app_update_time_by_service(self, service):
        sg = self.get_service_group_info(service.service_id)
        if sg and sg.ID:
            group_repo.update_group_time(sg.ID)

    @staticmethod
    @transaction.atomic
    def update_governance_mode(tenant, region_name, app_id, governance_mode):
        app = group_repo.get_group_by_id(app_id)
        service_ids = group_service_relation_repo.list_by_app_id(tenant.tenant_id, app_id).values_list("service_id", flat=True)
        ports = port_repo.list_by_service_ids(tenant.tenant_id, service_ids)
        # update the value of host env. eg. MYSQL_HOST
        from console.services.app_config import port_service
        port_service.create_ports_envs(tenant, region_name, app.ID, governance_mode, ports)

        group_repo.update_governance_mode(tenant.tenant_id, region_name, app_id, governance_mode)
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        region_api.update_app(region_name, tenant.tenant_name, region_app_id, {"governance_mode": governance_mode})

    @staticmethod
    def list_kubernetes_services(tenant_id, region_name, app_id):
        # list service_ids
        service_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant_id, region_name, app_id)
        if not service_ids:
            return []
        # service_id to service_alias
        services = service_repo.list_by_ids(service_ids)
        service_aliases = {service.service_id: service.service_alias for service in services}
        service_cnames = {service.service_id: service.service_cname for service in services}

        ports = port_repo.list_inner_ports_by_service_ids(tenant_id, service_ids)
        # build response
        k8s_services = []
        for port in ports:
            # set service_alias_container_port as default kubernetes service name
            k8s_service_name = port.k8s_service_name if port.k8s_service_name else service_aliases[port.service_id] + "-" + str(
                port.container_port)
            k8s_services.append({
                "service_id": port.service_id,
                "service_cname": service_cnames[port.service_id],
                "port": port.container_port,
                "port_alias": port.port_alias,
                "k8s_service_name": k8s_service_name,
            })

        return k8s_services

    @transaction.atomic()
    def update_kubernetes_services(self, tenant, region_name, app_id, k8s_services):
        from console.services.app_config import port_service
        service_ids = group_service_relation_repo.list_serivce_ids_by_app_id(tenant.tenant_id, region_name, app_id)

        self._check_k8s_service_names(tenant.tenant_id, k8s_services)

        ports = port_repo.list_by_service_ids(tenant.tenant_id, service_ids)
        # filter by k8s_services
        key_2_k8s_services = {k8s_service["service_id"] + str(k8s_service["port"]): k8s_service for k8s_service in k8s_services}

        # updates is the list of ports need to be updated
        updates = []
        for port in ports:
            key = port.service_id + str(port.container_port)
            k8s_service = key_2_k8s_services.get(key)
            if not k8s_service:
                continue
            port.port_alias = k8s_service.get("port_alias")
            port.port_alias = k8s_service.get("k8s_service_name")
            updates.append(port)

        port_service.update_ports(tenant, region_name, app_id, updates)

    @staticmethod
    def _check_k8s_service_names(tenant_id, k8s_services):
        # format verification
        for k8s_service in k8s_services:
            k8s_service_name = k8s_service.get("k8s_service_name")
            if len(k8s_service_name) > 63:
                raise AbortRequest("k8s_service_name must be no more than 63 characters")
            if not re.fullmatch("[a-z]([-a-z0-9]*[a-z0-9])?", k8s_service_name):
                raise AbortRequest("regex used for validation is '[a-z]([-a-z0-9]*[a-z0-9])?'", msg_show="内部域名格式不正确")

        # collision detection
        k8s_service_names = [k8s_service.get("k8s_service_name") for k8s_service in k8s_services]
        if len(k8s_service_names) != len(set(k8s_service_names)):
            raise AbortRequest("kubernetes service name duplicated", status_code=409, msg_show="内部域名不能重复")
        ports = port_repo.list_by_k8s_service_names(tenant_id, k8s_service_names)
        if not ports:
            return
        # make a map for k8s_services
        #  if port.service_id != component_id or port.container_port != container_port:
        k8s_services = {k8s_service.get("k8s_service_name"): k8s_service for k8s_service in k8s_services}
        for port in ports:
            k8s_service = k8s_services.get(port.k8s_service_name)
            if port.service_id != k8s_service.get("service_id") or port.container_port != k8s_service.get("port"):
                raise ErrK8sServiceNameExists

    @staticmethod
    def get_app_status(tenant, region_name, app_id):
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        status = region_api.get_app_status(region_name, tenant.tenant_name, region_app_id)
        if status.get("status") == "NIL":
            status["status"] = None
        return status


group_service = GroupService()
