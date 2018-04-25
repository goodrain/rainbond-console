# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
from console.repositories.plugin import config_group_repo, config_item_repo
from django.forms import model_to_dict
from console.constants import PluginMetaType
from www.models import PluginConfigItems, PluginConfigGroup


class PluginConfigService(object):
    def get_config_details(self, plugin_id, build_version):
        config_groups = config_group_repo.get_config_group_by_id_and_version(plugin_id, build_version)
        config_group = []
        for conf in config_groups:
            config_dict = model_to_dict(conf)
            items = config_item_repo.get_config_items_by_unique_key(conf.plugin_id, conf.build_version,
                                                                    conf.service_meta_type)
            options = [model_to_dict(item) for item in items]
            config_dict["options"] = options
            config_group.append(config_dict)
        return config_group

    def get_config_group(self, plugin_id, build_version):
        return config_group_repo.get_config_group_by_id_and_version(plugin_id, build_version)

    def check_group_config(self, service_meta_type, injection, config_groups):
        if injection == "env":
            if service_meta_type == PluginMetaType.UPSTREAM_PORT or service_meta_type == PluginMetaType.DOWNSTREAM_PORT:
                return False, u"基于上游端口或下游端口的配置只能使用主动发现"
        for config_group in config_groups:
            if config_group.service_meta_type == service_meta_type:
                return False, u"配置组配置类型不能重复"
        return True, u"检测成功"

    def get_config_group_by_pk(self, config_group_pk):
        return config_group_repo.get_config_group_by_pk(config_group_pk)

    def update_config_group_by_pk(self, config_group_pk, config_name, service_meta_type, injection):
        pcg = self.get_config_group_by_pk(config_group_pk)
        if not pcg:
            return 404, "配置不存在"
        pcg.service_meta_type = service_meta_type
        pcg.injection = injection
        pcg.config_name = config_name
        pcg.save()
        return 404, pcg

    def delet_config_items(self, plugin_id, build_version, service_meta_type):
        config_item_repo.delete_config_items(plugin_id, build_version, service_meta_type)

    def create_config_items(self, plugin_id, build_version, service_meta_type, *options):
        config_items_list = []
        for option in options:
            config_item = PluginConfigItems(
                plugin_id=plugin_id,
                build_version=build_version,
                service_meta_type=service_meta_type,
                attr_name=option["attr_name"],
                attr_alt_value=option["attr_alt_value"],
                attr_type=option.get("attr_type", "string"),
                attr_default_value=option.get("attr_default_value", None),
                is_change=option.get("is_change", False),
                attr_info=option.get("attr_info", ""),
                protocol=option.get("protocol", "")
            )
            config_items_list.append(config_item)

        config_item_repo.bulk_create_items(config_items_list)

    def create_config_groups(self, plugin_id, build_version, config_group):
        plugin_config_meta_list = []
        config_items_list = []
        if config_group:
            for config in config_group:
                options = config["options"]
                plugin_config_meta = PluginConfigGroup(
                    plugin_id=plugin_id,
                    build_version=build_version,
                    config_name=config["config_name"],
                    service_meta_type=config["service_meta_type"],
                    injection=config["injection"]
                )
                plugin_config_meta_list.append(plugin_config_meta)

                for option in options:
                    config_item = PluginConfigItems(
                        plugin_id=plugin_id,
                        build_version=build_version,
                        service_meta_type=config["service_meta_type"],
                        attr_name=option["attr_name"],
                        attr_alt_value=option["attr_alt_value"],
                        attr_type=option.get("attr_type", "string"),
                        attr_default_value=option.get("attr_default_value", None),
                        is_change=option.get("is_change", False),
                        attr_info=option.get("attr_info", ""),
                        protocol=option.get("protocol", "")
                    )
                    config_items_list.append(config_item)

        config_group_repo.bulk_create_plugin_config_group(plugin_config_meta_list)
        config_item_repo.bulk_create_items(config_items_list)

    def delete_config_group_by_meta_type(self, plugin_id, build_version, service_meta_type):
        config_group_repo.delete_config_group_by_meta_type(plugin_id, build_version, service_meta_type)
        config_item_repo.delete_config_items(plugin_id, build_version, service_meta_type)

    def get_config_items(self, plugin_id, build_version, service_meta_type):
        return config_item_repo.get_config_items_by_unique_key(plugin_id, build_version, service_meta_type)

    def delete_plugin_version_config(self, plugin_id, build_version):
        """删除插件某个版本的配置"""
        config_item_repo.delete_config_items_by_id_and_version(plugin_id, build_version)
        config_group_repo.delete_config_group_by_id_and_version(plugin_id, build_version)

    def copy_config_group(self,plugin_id, old_version, new_version):
        config_groups = config_group_repo.get_config_group_by_id_and_version(plugin_id, old_version)
        config_group_copy = []
        for config in config_groups:
            config_dict = model_to_dict(config)
            config_dict["build_version"] = new_version
            # 剔除主键
            config_dict.pop("ID")
            config_group_copy.append(PluginConfigGroup(**config_dict))
        config_group_repo.bulk_create_plugin_config_group(config_group_copy)

    def copy_group_items(self,plugin_id, old_version, new_version):
        config_items = config_item_repo.get_config_items_by_id_and_version(plugin_id,old_version)
        config_items_copy = []
        for item in config_items:
            item_dict = model_to_dict(item)
            # 剔除主键
            item_dict.pop("ID")
            item_dict["build_version"] = new_version
            config_items_copy.append(PluginConfigItems(**item_dict))
        config_item_repo.bulk_create_items(config_items_copy)