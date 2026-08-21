# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""

from typing import Any, List, Tuple

from console.repositories.plugin.listing import list_plugins_for_service


class AppPluginService(object):
    # 获取指定组件可用插件列表
    # 返回数据包含是否已安装信息
    def get_plugins_by_service_id(
        self, region: str, tenant_id: str, service_id: str, category: str
    ) -> Tuple[List[Any], List[Any]]:

        return list_plugins_for_service(region, tenant_id, service_id, category)

    # 安装指定插件，如果指定版本，根据版本安装，未指定版本，安装最新版本
    def install_plugin(self, service_id: str, plugin_id: str, version: str) -> None:
        pass

    # 卸载插件
    def uninstall_plugin(self, service_id: str, plugin_id: str) -> None:
        pass

    def open_plugin(self, service_id: str, plugin_id: str) -> None:
        pass

    def close_plugin(self, service_id: str, plugin_id: str) -> None:
        pass

    def get_app_plugin_configs(self, service_id: str, plugin_id: str) -> None:
        pass

    def put_app_plugin_configs(self, service_id: str, plugin_id: str) -> None:
        pass


app_plugin_service = AppPluginService()
