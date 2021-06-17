# -*- coding: utf-8 -*-

from www.models.plugin import (PluginBuildVersion, TenantPlugin)


class Plugin(object):
    def __init__(self, plugin: TenantPlugin, build_version: PluginBuildVersion, config_groups, config_items):
        self.plugin = plugin
        self.build_version = build_version
        self.config_groups = config_groups
        self.config_items = config_items
