# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""

from typing import Any, List, Tuple

from console.repositories.base import BaseConnection
import logging

logger = logging.getLogger("default")


class AppPluginService(object):
    # 获取指定组件可用插件列表
    # 返回数据包含是否已安装信息
    def get_plugins_by_service_id(
        self, region: str, tenant_id: str, service_id: str, category: str
    ) -> Tuple[List[Any], List[Any]]:

        query_installed_plugin = """
        SELECT tp.plugin_id as plugin_id,tp.desc as "desc",tp.plugin_alias as plugin_alias,
        tp.category as category,pbv.build_version as build_version,tsp.plugin_status as plugin_status
                           FROM tenant_service_plugin_relation tsp
                              LEFT JOIN plugin_build_version pbv ON tsp.plugin_id=pbv.plugin_id AND
                              tsp.build_version=pbv.build_version
                                  JOIN tenant_plugin tp ON tp.plugin_id=tsp.plugin_id
                                      WHERE tsp.service_id=%s AND tp.region=%s AND tp.tenant_id=%s """
        installed_args = [service_id, region, tenant_id]

        query_uninstalled_plugin = """
            SELECT tp.plugin_id as plugin_id,tp.desc as "desc",tp.plugin_alias as plugin_alias,
            tp.category as category,pbv.build_version as build_version
                FROM tenant_plugin AS tp
                    JOIN plugin_build_version AS pbv ON (tp.plugin_id=pbv.plugin_id)
                        WHERE pbv.plugin_id NOT IN (
                            SELECT plugin_id FROM tenant_service_plugin_relation
                                WHERE service_id=%s) AND
                                tp.tenant_id=%s AND
                                tp.region=%s AND
                                pbv.build_status=%s """
        uninstalled_args = [service_id, tenant_id, region, "build_success"]

        if category == "analysis":
            query_installed_plugin += " AND tp.category=%s"
            query_uninstalled_plugin += " AND tp.category=%s"
            installed_args.append("analyst-plugin:perf")
            uninstalled_args.append("analyst-plugin:perf")

        elif category == "net_manage":
            category_args = ["net-plugin:down", "net-plugin:up", "net-plugin:in-and-out"]
            query_installed_plugin += " AND tp.category in (%s, %s, %s)"
            query_uninstalled_plugin += " AND tp.category in (%s, %s, %s)"
            installed_args.extend(category_args)
            uninstalled_args.extend(category_args)

        dsn = BaseConnection()
        logger.debug("\n query_installed_plugin --- {0} \n query_uninstalled_plugin --- {1}".format(
            query_installed_plugin, query_uninstalled_plugin))
        installed_plugins = dsn.query(query_installed_plugin, installed_args)
        uninstalled_plugins = dsn.query(query_uninstalled_plugin, uninstalled_args)
        return installed_plugins, uninstalled_plugins

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
