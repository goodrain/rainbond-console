# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
from .service_plugin_repo import AppPluginRelationRepo,ServicePluginAttrRepository,ServicePluginConfigVarRepository
from .plugin import TenantPluginRepository
from .plugin_version import PluginVersionRepository
from .plugin_config import PluginConfigGroupRepository, PluginConfigItemsRepository

app_plugin_relation_repo = AppPluginRelationRepo()
plugin_repo = TenantPluginRepository()
plugin_version_repo = PluginVersionRepository()
config_group_repo = PluginConfigGroupRepository()
config_item_repo = PluginConfigItemsRepository()
app_plugin_attr_repo = ServicePluginAttrRepository()
service_plugin_config_repo = ServicePluginConfigVarRepository()
