# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
from www.models import TenantServicePluginRelation, TenantServicePluginAttr, ServicePluginConfigVar
from www.db import BaseConnection



class AppPluginRelationRepo(object):
    def get_service_plugin_relation_by_service_id(self, service_id):
        return TenantServicePluginRelation.objects.filter(service_id=service_id)

    def get_service_plugin_relation_by_plugin_unique_key(self, plugin_id, build_version):
        tsprs = TenantServicePluginRelation.objects.filter(plugin_id=plugin_id, build_version=build_version)
        if tsprs:
            return tsprs
        return None

    def get_used_plugin_services(self, plugin_id):
        """获取使用了某个插件的服务"""
        return TenantServicePluginRelation.objects.filter(plugin_id=plugin_id)

    def create_service_plugin_relation(self, **params):
        """创建服务插件关系"""
        TenantServicePluginRelation.objects.create(**params)

    def update_service_plugin_status(self, service_id, plugin_id, is_active):
        TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_id=plugin_id).update(
            plugin_status=is_active)

    def get_relation_by_service_and_plugin(self, service_id, plugin_id):
        return TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_id=plugin_id)

    def get_service_plugin_relation_by_plugin_id(self, plugin_id):
        return TenantServicePluginRelation.objects.filter(plugin_id=plugin_id)

    def delete_service_plugin_relation_by_plugin_id(self, plugin_id):
        TenantServicePluginRelation.objects.filter(plugin_id=plugin_id).delete()

    def delete_service_plugin(self, service_id, plugin_id):
        TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_id=plugin_id).delete()

    def get_service_plugin_relations_by_service_ids(self, service_ids):
        return TenantServicePluginRelation.objects.filter(service_id__in=service_ids)

    def check_plugins_by_eid(self, eid):
        """
        check if an app has been shared
        """
        conn = BaseConnection()
        sql = """
            SELECT
                a.plugin_id 
            FROM
                tenant_service_plugin_relation a,
                tenant_service c,
                tenant_info b 
            WHERE
                c.tenant_id = b.tenant_id 
                AND a.service_id = c.service_id 
                AND b.enterprise_id = "{eid}" 
                LIMIT 1""".format(eid=eid)
        result = conn.query(sql)
        return True if len(result) > 0 else False


class ServicePluginAttrRepository(object):
    def delete_attr_by_plugin_id(self, plugin_id):
        TenantServicePluginAttr.objects.filter(plugin_id=plugin_id).delete()


class ServicePluginConfigVarRepository(object):
    def get_service_plugin_config_var(self, service_id, plugin_id, build_version):
        return ServicePluginConfigVar.objects.filter(service_id=service_id, plugin_id=plugin_id,
                                                     build_version=build_version)

    def delete_service_plugin_config_var(self, service_id, plugin_id):
        ServicePluginConfigVar.objects.filter(service_id=service_id, plugin_id=plugin_id).delete()

    def get_service_plugin_all_config(self, service_id):
        return ServicePluginConfigVar.objects.filter(service_id=service_id)