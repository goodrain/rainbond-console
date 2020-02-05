# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import json
import logging
import re

from django.db import transaction

from console.repositories.app import service_repo
from console.repositories.app import service_source_repo
from console.repositories.backup_repo import backup_record_repo
from console.repositories.group import group_repo
from console.repositories.group import group_service_relation_repo
from console.repositories.upgrade_repo import upgrade_repo
from console.utils.shortcuts import get_object_or_404
from www.models.main import ServiceGroup
from console.repositories.migration_repo import migrate_repo
from console.utils.etcdutil import del_etcd

logger = logging.getLogger("default")


class GroupService(object):
    def get_tenant_groups_by_region(self, tenant, region_name):
        return group_repo.list_tenant_group_on_region(tenant, region_name)

    def check_group_name(self, group_name):
        if len(group_name) > 15:
            return False, u"应用名称最多支持15个字符"
        r = re.compile(u'^[a-zA-Z0-9_\\.\\-\u4e00-\u9fa5]+$')
        if not r.match(group_name.decode("utf-8")):
            return False, u"应用名称只支持中英文, 数字, 下划线, 中划线和点"
        return True, u"success"

    def add_group(self, tenant, region_name, group_name):
        if not group_name:
            return 400, u"应用名称不能为空", None
        is_pass, msg = self.check_group_name(group_name)
        if not is_pass:
            return 400, msg, None
        new_group = group_repo.add_group(tenant.tenant_id, region_name, group_name)
        return 200, u"添加成功", new_group

    def update_group(self, tenant, region_name, group_id, group_name):
        if not group_id or group_id < 0:
            return 400, u"应用ID不合法", None
        if not group_name:
            return 400, u"应用名不能为空", None
        is_pass, msg = self.check_group_name(group_name)
        if not is_pass:
            return 400, msg, None
        group = group_repo.get_group_by_unique_key(tenant.tenant_id, region_name, group_name)
        if group:
            return 403, u"应用名{0}已存在".format(group_name), None
        group_repo.update_group_name(group_id, group_name)
        return 200, u"修改成功", group_name

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
            return 404, u"应用不存在", None
        rt_bean = {"group_id": group.ID, "group_name": group.group_name}
        return 200, u"success", rt_bean

    def get_app_by_id(self, app_id):
        return group_repo.get_app_by_pk(app_id)

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
            msg_show=u"应用不存在",
            tenant_id=tenant.tenant_id,
            region_name=response_region,
            pk=group_id)

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
        return 200, "success"

    def get_groups_and_services(self, tenant, region):
        groups = group_repo.get_tenant_region_groups(tenant.tenant_id, region)
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
        # # 未分应用应用
        # uncategory_services = []
        # for k, v in service_id_map.iteritems():
        #     uncategory_services.append(v)

        result = []
        for g in groups:
            bean = dict()
            bean["group_id"] = g.ID
            bean["group_name"] = g.group_name
            bean["service_list"] = group_services_map.get(g.ID)
            result.insert(0, bean)
        # result.append({
        #     "group_id": -1,
        #     "group_name": "未分应用",
        #     "service_list": uncategory_services
        # })

        return result

    def get_group_services(self, group_id):
        """查询某一应用下的组件"""
        gsr = group_service_relation_repo.get_services_by_group(group_id)
        service_ids = [gs.service_id for gs in gsr]
        services = service_repo.get_services_by_service_ids(service_ids)
        return services

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

    def get_service_group_memory(self, app_template_raw):
        """获取一应用组件内存"""
        try:
            app_template = json.loads(app_template_raw)
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

    def delete_group_etcd_data(self, group):
        migrate_record = migrate_repo.get_by_original_group_id(group)
        if not migrate_record:
            logger.debug("do not found migrate data by group id={0}".format(group))
            return
        keys = []
        region = migrate_record[0].migrate_region
        team = migrate_record[0].migrate_team
        for record in migrate_record:
            keys.append("/rainbond/backup_restore/{0}".format(record.restore_id))
        del_etcd(region, team, keys)


group_service = GroupService()
