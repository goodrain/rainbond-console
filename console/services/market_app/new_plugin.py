# -*- coding: utf-8 -*-

from .plugin import Plugin
from console.repositories.plugin.plugin import plugin_repo
from console.repositories.plugin.plugin_version import build_version_repo
from www.models.plugin import (PluginBuildVersion, PluginConfigGroup, PluginConfigItems, TenantPlugin)
from www.utils.crypt import make_uuid


class NewPlugin(object):
    def __init__(self, tenant, region_name, user, plugin_templates):
        self.tenant = tenant
        self.region_name = region_name
        self.user = user

        self.plugin_templates = plugin_templates

        self.original_plugins = self._original_plugins()
        self.new_plugins = self._new_plugins()

    def save(self):
        plugins = []
        build_versions = []
        config_groups = []
        config_items = []
        for plugin in self.new_plugins:
            plugins.append(plugin.plugin)
            build_versions.append(plugin.build_version)
            config_groups.append(plugin.config_groups)
            config_items.append(plugin.config_items)

        plugin_repo.bulk_create(plugins)
        build_version_repo.bulk_create(build_versions)
        PluginConfigGroup.objects.bulk_create(config_groups)
        PluginConfigItems.objects.bulk_create(config_items)


    def _original_plugins(self):
        plugins = plugin_repo.list_by_tenant_id(self.tenant.tenant_id, self.region_name)
        return [plugin for plugin in plugins]

    def _new_plugins(self):
        original_plugins = {plugin.origin_share_id: plugin for plugin in self.original_plugins}
        plugins = []
        for plugin_tmpl in self.plugin_templates:
            original_plugin = original_plugins.get(plugin_tmpl.get("plugin_key"))
            if original_plugin:
                continue


            plugin = self._create_plugin(plugin_tmpl),
            build_version = self._create_build_version(plugin.plugin_id, plugin_tmpl)
            config_groups, config_items = self._create_config_groups(plugin.plugin_id, build_version, plugin_tmpl["config_groups"])
            config_groups = config_groups
            config_items = config_items
            plugins.append(Plugin(plugin, build_version, config_groups, config_items))

        return plugins

    def _create_plugin(self, plugin_tmpl):
        image = None
        if plugin_tmpl["share_image"]:
            image_and_tag = plugin_tmpl["share_image"].rsplit(":", 1)
            if len(image_and_tag) > 1:
                image = image_and_tag[0]
            else:
                image = image_and_tag[0]
        return TenantPlugin(
            tenant_id=self.tenant.tenant_id,
            region=self.region_name,
            plugin_id=make_uuid(),
            create_user=self.user.user_id,
            desc=plugin_tmpl["desc"],
            plugin_alias=plugin_tmpl["plugin_alias"],
            category=plugin_tmpl["category"],
            build_source="image",
            image=image,
            code_repo=plugin_tmpl["code_repo"],
            username=plugin_tmpl["plugin_image"]["hub_user"],
            password=plugin_tmpl["plugin_image"]["hub_password"],
            origin="local_market",
            origin_share_id=plugin_tmpl["plugin_key"]
        )

    def _create_build_version(self, plugin_id, plugin_tmpl):
        image_tag = None
        if plugin_tmpl["share_image"]:
            image_and_tag = plugin_tmpl["share_image"].rsplit(":", 1)
            if len(image_and_tag) > 1:
                image_tag = image_and_tag[1]
            else:
                image_tag = "latest"

        min_memory = plugin_tmpl.get('min_memory', 128)
        min_cpu = int(min_memory) / 128 * 20

        return PluginBuildVersion(
            plugin_id=plugin_id,
            tenant_id=self.tenant.tenant_id,
            region=self.region_name,
            user_id=self.user.user_id,
            build_version=plugin_tmpl.get('build_version'),
            build_status="unbuild",
            min_memory=min_memory,
            min_cpu=min_cpu,
            image_tag=image_tag,
        )

    @staticmethod
    def _create_config_groups(plugin_id, build_version, config_groups_tmpl):
        config_groups = []
        config_items = []
        for config in config_groups_tmpl:
            options = config["options"]
            plugin_config_meta = PluginConfigGroup(
                plugin_id=plugin_id,
                build_version=build_version,
                config_name=config["config_name"],
                service_meta_type=config["service_meta_type"],
                injection=config["injection"])
            config_groups.append(plugin_config_meta)

            for option in options:
                config_item = PluginConfigItems(
                    plugin_id=plugin_id,
                    build_version=build_version,
                    service_meta_type=config["service_meta_type"],
                    attr_name=option.get("attr_name", ""),
                    attr_alt_value=option.get("attr_alt_value", ""),
                    attr_type=option.get("attr_type", "string"),
                    attr_default_value=option.get("attr_default_value", None),
                    is_change=option.get("is_change", False),
                    attr_info=option.get("attr_info", ""),
                    protocol=option.get("protocol", ""))
                config_items.append(config_item)
        return config_groups, config_items
