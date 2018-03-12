# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
from .app_plugin import AppPluginService
from .app_plugin import PluginService
from .plugin_version import PluginBuildVersionService
from .plugin_config_service import PluginConfigService

app_plugin_service = AppPluginService()
plugin_service = PluginService()
plugin_version_service = PluginBuildVersionService()
plugin_config_service = PluginConfigService()
