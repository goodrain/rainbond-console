# -*- coding: utf8 -*-
"""
  Created on 18/3/4.
"""
from www.models import PluginConfigGroup, PluginConfigItems


class PluginConfigGroupRepository(object):
    def get_config_group_by_id_and_version(self, plugin_id, build_version):
        return PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version)

    def get_config_group_by_pk(self, pk):
        pcg = PluginConfigGroup.objects.filter(ID=pk)
        if pcg:
            return pcg[0]
        return None

    def bulk_create_plugin_config_group(self, plugin_config_meta_list):
        """批量创建插件配置组信息"""
        PluginConfigGroup.objects.bulk_create(plugin_config_meta_list)

    def delete_config_group_by_meta_type(self, plugin_id, build_version, service_meta_type):
        PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version,
                                         service_meta_type=service_meta_type).delete()

    def delete_config_group_by_id_and_version(self, plugin_id, build_version):
        PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()

    def create_plugin_config_group(self, **params):
        return PluginConfigGroup.objects.create(**params)

    def delete_config_group_by_plugin_id(self, plugin_id):
        PluginConfigGroup.objects.filter(plugin_id=plugin_id).delete()


class PluginConfigItemsRepository(object):
    def get_config_items_by_unique_key(self, plugin_id, build_version, service_meta_type):
        return PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version,
                                                service_meta_type=service_meta_type)

    def delete_config_items(self, plugin_id, build_version, service_meta_type):
        PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version,
                                         service_meta_type=service_meta_type).delete()

    def bulk_create_items(self, config_items_list):
        PluginConfigItems.objects.bulk_create(config_items_list)

    def delete_config_items_by_id_and_version(self, plugin_id, build_version):
        PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()

    def get_config_items_by_id_and_version(self, plugin_id, build_version):
        return PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version)

    def create_plugin_config_items(self, **params):
        return PluginConfigItems.objects.create(**params)

    def delete_config_items_by_plugin_id(self, plugin_id):
        PluginConfigItems.objects.filter(plugin_id=plugin_id).delete()
