# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.plugin import plugin_config_service
from console.views.plugin.base import PluginBaseView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.region_services import region_services
from console.constants import PluginMetaType

logger = logging.getLogger("default")


class ConfigPluginManageView(PluginBaseView):
    @never_cache
    @perm_required('view_plugin')
    def get(self, request, *args, **kwargs):
        """
        获取某个插件的配置信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 版本
              required: true
              type: string
              paramType: path
        """
        try:
            config_groups = plugin_config_service.get_config_details(self.plugin_version.plugin_id,
                                                                     self.plugin_version.build_version)
            data = self.plugin_version.to_dict()
            main_url = region_services.get_region_wsurl(self.response_region)
            data["web_socket_url"] = "{0}/event_log".format(main_url)

            result = general_message(200, "success", "查询成功", bean=data,list=config_groups)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_plugin')
    def put(self, request, *args, **kwargs):
        """
        修改插件配置信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 版本
              required: true
              type: string
              paramType: path
            - name: body
              description: 配置组内容
              required: true
              type: string
              paramType: body
        """
        try:
            config = request.data

            injection = config.get("injection")
            service_meta_type = config.get("service_meta_type")
            config_name = config.get("config_name")
            config_group_pk = config.get("ID")

            config_groups = plugin_config_service.get_config_group(self.plugin_version.plugin_id,
                                                                   self.plugin_version.build_version).exclude(
                pk=config_group_pk)
            is_pass, msg = plugin_config_service.check_group_config(service_meta_type, injection, config_groups)

            if not is_pass:
                return Response(general_message(400, "param error", msg), status=400)
            config_group = plugin_config_service.get_config_group_by_pk(config_group_pk)
            old_meta_type = config_group.service_meta_type
            plugin_config_service.update_config_group_by_pk(config_group_pk, config_name, service_meta_type, injection)

            # 删除原有配置项
            plugin_config_service.delet_config_items(self.plugin_version.plugin_id, self.plugin_version.build_version,
                                                     old_meta_type)
            options = config.get("options")
            plugin_config_service.create_config_items(self.plugin_version.plugin_id, self.plugin_version.build_version,
                                                      service_meta_type, *options)

            result = general_message(200, "success", "修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_plugin')
    def post(self, request, *args, **kwargs):
        """
        添加插件配置信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 版本
              required: true
              type: string
              paramType: path
            - name: body
              description: 配置组内容
              required: true
              type: string
              paramType: body
        """
        try:
            config = request.data

            injection = config.get("injection")
            service_meta_type = config.get("service_meta_type")
            config_groups = plugin_config_service.get_config_group(self.plugin_version.plugin_id,
                                                                   self.plugin_version.build_version)
            is_pass, msg = plugin_config_service.check_group_config(service_meta_type, injection, config_groups)

            if not is_pass:
                return Response(general_message(400, "param error", msg), status=400)
            create_data = [config]
            plugin_config_service.create_config_groups(self.plugin_version.plugin_id,
                                                       self.plugin_version.build_version, create_data)

            result = general_message(200, "success", "添加成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_plugin')
    def delete(self, request, *args, **kwargs):
        """
        删除插件配置信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 版本
              required: true
              type: string
              paramType: path
            - name: config_group_id
              description: 配置组ID
              required: true
              type: string
              paramType: form
        """
        try:
            config_group_id = request.data.get("config_group_id")
            if not config_group_id:
                return Response(general_message(400, "param error", "参数错误"), status=400)

            config_group = plugin_config_service.get_config_group_by_pk(config_group_id)
            if not config_group:
                return Response(general_message(404, "config group not exist", "配置组不存在"), status=404)
            plugin_config_service.delete_config_group_by_meta_type(config_group.plugin_id, config_group.build_version,
                                                                   config_group.service_meta_type)

            result = general_message(200, "success", "删除成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class ConfigPreviewView(PluginBaseView):
    @never_cache
    @perm_required('view_plugin')
    def get(self, request, *args, **kwargs):
        """
        获取某个插件某个版本的预览信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 版本
              required: true
              type: string
              paramType: path
        """
        try:
            wordpress_alias = "wordpress_alias"
            mysql_alias = "mysql_alias"
            wp_ports = [80, 8081]
            mysql_port = [3306]
            wp_id = "wp_service_id"
            mysql_id = "mysql_service_id"

            config_groups = plugin_config_service.get_config_group(self.plugin_version.plugin_id,
                                                                   self.plugin_version.build_version)
            all_config_group = []
            base_ports = []
            base_services = []
            base_normal = {}
            for config_group in config_groups:
                config_items = plugin_config_service.get_config_items(self.plugin_version.plugin_id,
                                                                      self.plugin_version.build_version,
                                                                      config_group.service_meta_type)
                items = []
                for item in config_items:
                    item_map = {}
                    item_map[item.attr_name] = item.attr_default_value
                    items.append(item_map)

                if config_group.service_meta_type == PluginMetaType.UPSTREAM_PORT:
                    for port in wp_ports:
                        base_port = {}
                        base_port["service_alias"] = wordpress_alias
                        base_port["service_id"] = wp_id
                        base_port["port"] = port
                        base_port["protocol"] = "http"
                        base_port["options"] = items
                        base_ports.append(base_port)
                if config_group.service_meta_type == PluginMetaType.DOWNSTREAM_PORT:
                    for port in mysql_port:
                        base_service = {}
                        base_service["service_alias"] = wordpress_alias
                        base_service["service_id"] = wp_id
                        base_service["port"] = port
                        #base_service["protocol"] = "stream"
                        base_service["protocol"] = "mysql"
                        base_service["options"] = items
                        base_service["depend_service_alias"] = mysql_alias
                        base_service["depend_service_id"] = mysql_id
                        base_services.append(base_service)
                if config_group.service_meta_type == PluginMetaType.UNDEFINE:
                    base_normal["options"] = items

            bean = {"base_ports": base_ports, "base_services": base_services,
                    "base_normal": base_normal.get("options", None)}

            result = general_message(200, "success", "查询成功", bean=bean, list=all_config_group)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
