# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import logging
import re

from django.db import transaction

from console.exception.main import ServiceHandleException
from console.repositories.app import service_repo, service_source_repo
from console.repositories.backup_repo import backup_record_repo
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.share_repo import share_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.services.service_services import base_service
from console.utils.shortcuts import get_object_or_404
from www.models.main import ServiceGroup, ServiceGroupRelation

logger = logging.getLogger("default")


class GroupService(object):
    def get_tenant_groups_by_region(self, tenant, region_name):
        return group_repo.list_tenant_group_on_region(tenant, region_name)

    def check_group_name(self, tenant, region_name, group_name):
        if not group_name:
            raise ServiceHandleException(msg="app name required", msg_show="应用名不能为空")
        if len(group_name) > 128:
            raise ServiceHandleException(msg="app_name illegal", msg_show="应用名称最多支持128个字符")
        r = re.compile(u'^[a-zA-Z0-9_\\.\\-\u4e00-\u9fa5]+$')
        if not r.match(group_name.decode("utf-8")):
            raise ServiceHandleException(msg="app_name illegal", msg_show="应用名称只支持中英文, 数字, 下划线, 中划线和点")

    def add_group(self, tenant, region_name, group_name, group_note=""):
        self.check_group_name(tenant, region_name, group_name)
        return group_repo.add_group(tenant.tenant_id, region_name, group_name, group_note)

    def update_group(self, tenant, region_name, group_id, group_name, group_note=""):
        if not group_id or group_id < 0:
            raise ServiceHandleException(msg="app id illegal", msg_show="应用ID不合法")
        self.check_group_name(tenant, region_name, group_name)
        group = group_repo.get_group_by_unique_key(tenant.tenant_id, region_name, group_name)
        if group and group.ID != group_id:
            raise ServiceHandleException(msg="app already exists", msg_show="应用名{0}已存在".format(group_name))
        group_repo.update_group_name(group_id, group_name, group_note)

    def delete_group(self, group_id, default_group_id):
        if not group_id or group_id < 0:
            return 400, u"需要删除的应用不合法", None
        backups = backup_record_repo.get_record_by_group_id(group_id)
        if backups:
            return 409, u"当前应用有备份记录，暂无法删除", None
        # 删除应用
        group_repo.delete_group_by_pk(group_id)
        # 删除应用与应用的关系
        group_service_relation_repo.update_service_relation(group_id, default_group_id)
        return 200, u"删除成功", group_id

    def add_service_to_group(self, tenant, region_name, group_id, service_id):

        if group_id:
            group_id = int(group_id)
            if group_id > 0:
                group = group_repo.get_group_by_pk(tenant.tenant_id, region_name, group_id)
                if not group:
                    return 404, u"应用不存在"
                group_service_relation_repo.add_service_group_relation(group_id, service_id, tenant.tenant_id, region_name)
        return 200, u"success"

    def get_group_by_id(self, tenant, region, group_id):
        group = group_repo.get_group_by_pk(tenant.tenant_id, region, group_id)
        if not group:
            raise ServiceHandleException(status_code=404, msg="app not found", msg_show="目标应用不存在")
        return {"group_id": group.ID, "group_name": group.group_name, "group_note": group.note}

    def get_app_by_id(self, tenant, region, app_id):
        return group_repo.get_group_by_pk(tenant.tenant_id, region, app_id)

    def get_group_or_404(self, tenant, response_region, group_id):
        """
        :param tenant:
        :param response_region:
        :param group_id:
        :rtype: ServiceGroup
        """
        return get_object_or_404(ServiceGroup,
                                 msg="Group does not exist",
                                 msg_show=u"应用不存在",
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
        for k, v in service_group_map.iteritems():
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
            service.status = service_status[service.service_id]["status"]
            service.used_mem = service_status[service.service_id]["used_mem"]

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
        if not group_id or group_id < 0:
            return 400, u"需要删除的应用不合法", None
        # backups = backup_record_repo.get_record_by_group_id(group_id)
        # if backups:
        #     return 409, u"当前应用有备份记录，暂无法删除", None
        # 删除应用
        group_repo.delete_group_by_pk(group_id)
        # 删除升级记录
        upgrade_repo.delete_app_record_by_group_id(group_id)

        return 200, u"删除成功", group_id

    def get_service_group_memory(self, app_template):
        """获取一应用组件内存"""
        try:
            apps = app_template["apps"]
            total_memory = 0
            for app in apps:
                extend_method_map = app.get("extend_method_map", None)
                if extend_method_map:
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

    def set_app_update_time_by_service(self, service):
        sg = self.get_service_group_info(service.service_id)
        if sg and sg.ID:
            group_repo.update_group_time(sg.ID)


group_service = GroupService()
