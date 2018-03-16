# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""

from console.repositories.base import BaseConnection
from www.models.plugin import TenantPlugin
from console.repositories.plugin import service_plugin_repo
import logging

logger = logging.getLogger("default")


class AppPluginService(object):
    # 获取指定应用可用插件列表
    # 返回数据包含是否已安装信息
    def get_plugins_by_service_id(self, region, tenant_id, service_id, category):

        QUERY_INSTALLED_SQL = """SELECT tp.plugin_id as plugin_id,tp.desc as "desc",tp.plugin_alias as plugin_alias,tp.category as category,pbv.build_version as build_version,tsp.plugin_status as plugin_status
                           FROM tenant_service_plugin_relation tsp
                              LEFT JOIN plugin_build_version pbv ON tsp.plugin_id=pbv.plugin_id AND tsp.build_version=pbv.build_version
                                  JOIN tenant_plugin tp ON tp.plugin_id=tsp.plugin_id
                                      WHERE tsp.service_id="{0}" AND tp.region="{1}" AND tp.tenant_id="{2}" """.format(
            service_id,
            region,
            tenant_id)

        QUERI_UNINSTALLED_SQL = """
            SELECT tp.plugin_id as plugin_id,tp.desc as "desc",tp.plugin_alias as plugin_alias,tp.category as category,pbv.build_version as build_version
                FROM tenant_plugin AS tp
                    JOIN plugin_build_version AS pbv ON (tp.plugin_id=pbv.plugin_id)
                        WHERE pbv.plugin_id NOT IN (
                            SELECT plugin_id FROM tenant_service_plugin_relation
                                WHERE service_id="{0}") AND tp.tenant_id="{1}" AND tp.region="{2}" AND pbv.build_status="{3}" """.format(service_id,tenant_id,region,"build_success")

        if category == "analysis":
            query_installed_plugin = """{0} AND tp.category="{1}" """.format(QUERY_INSTALLED_SQL, "analyst-plugin:perf")


            query_uninstalled_plugin = """{0} AND tp.category="{1}" """.format(QUERI_UNINSTALLED_SQL,"analyst-plugin:perf")

        elif category == "net_manage":
            query_installed_plugin = """{0} AND tp.category in {1} """.format(QUERY_INSTALLED_SQL,
                                                                                '("net-plugin:down","net-plugin:up")')
            query_uninstalled_plugin = """ {0} AND tp.category in {1} """.format(QUERI_UNINSTALLED_SQL,'("net-plugin:down","net-plugin:up")')
        else:
            query_installed_plugin = QUERY_INSTALLED_SQL
            query_uninstalled_plugin = QUERI_UNINSTALLED_SQL

        dsn = BaseConnection()
        logger.debug("\n query_installed_plugin --- {0} \n query_uninstalled_plugin --- {1}".format(query_installed_plugin,query_uninstalled_plugin))
        installed_plugins = dsn.query(query_installed_plugin)
        uninstalled_plugins = dsn.query(query_uninstalled_plugin)
        return installed_plugins, uninstalled_plugins

    # 安装指定插件，如果指定版本，根据版本安装，未指定版本，安装最新版本
    def install_plugin(self, service_id, plugin_id, version):
        pass

    # 卸载插件
    def uninstall_plugin(self, service_id, plugin_id):
        pass

    def open_plugin(self, service_id, plugin_id):
        pass

    def close_plugin(self, service_id, plugin_id):
        pass

    def get_app_plugin_configs(self, service_id, plugin_id):
        pass

    def put_app_plugin_configs(self, service_id, plugin_id):
        pass


app_plugin_service = AppPluginService()
