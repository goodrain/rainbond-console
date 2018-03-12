# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
from www.models import TenantServicePluginRelation


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
        return TenantServicePluginRelation.objects.filter(plugin_id=plugin_id, plugin_status=True)

    def create_service_plugin_relation(self, **params):
        """创建服务插件关系"""
        TenantServicePluginRelation.objects.create(**params)

    def update_service_plugin_status(self, id):
        tspr = TenantServicePluginRelation.objects.filter(ID=id)
        if tspr:
            return tspr[0]
        return None

    def get_relation_by_service_and_plugin(self,service_id,plugin_id):
        return TenantServicePluginRelation.objects.filter(service_id=service_id,plugin_id=plugin_id)


class ServicePluginAttrRepository(object):
    pass