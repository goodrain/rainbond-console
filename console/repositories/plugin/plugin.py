# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
from www.models import TenantPlugin, PluginBuildVersion, PluginConfigGroup, PluginConfigItems
from www.db import BaseConnection


class TenantPluginRepository(object):
    def get_plugin_by_plugin_id(self, tenant_id, plugin_id):
        """
        根据租户和插件id查询插件元信息
        :param tenant: 租户信息
        :param plugin_id: 插件ID列表
        :return: 插件信息
        """
        tenant_plugins = TenantPlugin.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id)
        if tenant_plugins:
            return tenant_plugins[0]
        else:
            return None

    def get_plugin_by_plugin_ids(self, plugin_ids):
        return TenantPlugin.objects.filter(plugin_id__in=plugin_ids)

    def get_plugin_buildversion(self, plugin_id, version):
        build_verison = PluginBuildVersion.objects.filter(
            plugin_id=plugin_id, build_version=version)
        if build_verison:
            return build_verison[0]
        return None

    def get_plugin_config_groups(self, plugin_id, version):
        config_groups = PluginConfigGroup.objects.filter(
            plugin_id=plugin_id, build_version=version)
        if config_groups:
            return config_groups
        return []

    def get_plugin_config_items(self, plugin_id, version):
        config_items = PluginConfigItems.objects.filter(
            plugin_id=plugin_id, build_version=version)
        if config_items:
            return config_items
        return []

    def get_plugins_by_service_ids(self, service_ids):
        if not service_ids:
            return []
        ids = ""
        for sid in service_ids:
            ids += "\"{0}\",".format(sid)
        if len(ids) > 1:
            ids = ids[:-1]
        dsn = BaseConnection()
        query_sql = '''
            select t.*,p.build_version from tenant_plugin t,plugin_build_version p,tenant_service_plugin_relation r where r.service_id in({service_ids}) and t.plugin_id=r.plugin_id and p.build_version=r.build_version
            '''.format(service_ids=ids)
        plugins = dsn.query(query_sql)
        return plugins

    def create_plugin(self, **plugin_args):
        return TenantPlugin.objects.create(**plugin_args)

    def delete_by_plugin_id(self, plugin_id):
        TenantPlugin.objects.filter(plugin_id=plugin_id).delete()

    def get_tenant_plugins(self, tenant_id, region):
        return TenantPlugin.objects.filter(tenant_id=tenant_id, region=region)
