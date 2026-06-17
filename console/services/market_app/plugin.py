# -*- coding: utf-8 -*-
from typing import Any, List, Optional

from www.models.plugin import (PluginBuildVersion, TenantPlugin)


class Plugin(object):
    def __init__(self,
                 plugin: TenantPlugin,
                 build_version: PluginBuildVersion,
                 config_groups: Optional[List[Any]] = None,
                 config_items: Optional[List[Any]] = None,
                 plugin_image: Optional[Any] = None) -> None:
        self.plugin = plugin
        self.build_version = build_version
        self.config_groups = config_groups
        self.config_items = config_items
        self.plugin_image = plugin_image
