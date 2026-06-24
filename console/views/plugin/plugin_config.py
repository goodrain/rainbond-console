# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import logging
from typing import Any

from console.utils.cache_decorators import never_cache
from rest_framework.request import Request
from rest_framework.response import Response

from console.services.operation_log import operation_log_service, Operation
from console.services.plugin import plugin_config_service
from console.utils.realtime_proxy import build_console_realtime_proxy_url
from console.views.plugin.base import PluginBaseView
from www.utils.return_message import general_message
from console.constants import PluginMetaType

logger = logging.getLogger("default")


class ConfigPluginManageView(PluginBaseView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
        config_groups = plugin_config_service.get_config_details(self.plugin_version.plugin_id,
                                                                 self.plugin_version.build_version)
        data = self.plugin_version.to_dict()
        data["web_socket_url"] = build_console_realtime_proxy_url(request, self.response_region, "event_log", scheme_type="ws")

        result = general_message(200, "success", "查询成功", bean=data, list=config_groups)
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
        config = request.data

        injection = config.get("injection")
        service_meta_type = config.get("service_meta_type")
        config_name = config.get("config_name")
        config_group_pk = config.get("ID")
        modify_type = config.get("modify_type", False)
        old_config = plugin_config_service.get_config_group_by_pk(config_group_pk)  # type: ignore[arg-type]
        old_information = plugin_config_service.json_config_group(old_config)  # type: ignore[arg-type]
        config_groups = plugin_config_service.get_config_group(self.plugin_version.plugin_id,
                                                               self.plugin_version.build_version).exclude(pk=config_group_pk)
        is_pass, msg = plugin_config_service.check_group_config(
            service_meta_type, injection, config_groups)  # type: ignore[arg-type]

        if not is_pass:
            return Response(general_message(400, "param error", msg), status=400)
        config_group = plugin_config_service.get_config_group_by_pk(config_group_pk)  # type: ignore[arg-type]
        # NOTE: config.get / get_config_group_by_pk may yield None; backlog
        old_meta_type = config_group.service_meta_type  # type: ignore[union-attr]
        plugin_config_service.update_config_group_by_pk(
            config_group_pk, config_name, service_meta_type, injection)  # type: ignore[arg-type]

        # 删除原有配置项
        plugin_config_service.delet_config_items(self.plugin_version.plugin_id, self.plugin_version.build_version,
                                                 old_meta_type)
        options = config.get("options")
        if modify_type and injection == "plugin_storage":
            plugin_config_service.delete_config_group_by_meta_type(
                config_group.plugin_id,  # type: ignore[union-attr]
                config_group.build_version,  # type: ignore[union-attr]
                config_group.service_meta_type)  # type: ignore[union-attr]
        else:
            plugin_config_service.create_config_items(
                self.plugin_version.plugin_id, self.plugin_version.build_version,
                service_meta_type,  # type: ignore[arg-type]
                *options)  # type: ignore[misc]
        result = general_message(200, "success", "修改成功")
        plugin_name = operation_log_service.process_plugin_name(self.plugin.plugin_alias, self.response_region,
                                                                self.tenant.tenant_name, self.plugin.plugin_id)
        new_config = plugin_config_service.get_config_group_by_pk(config_group_pk)  # type: ignore[arg-type]
        new_information = plugin_config_service.json_config_group(new_config)  # type: ignore[arg-type]
        comment = operation_log_service.generate_team_comment(
            operation=Operation.IN,
            module_name=self.tenant.tenant_alias,  # type: ignore[arg-type]
            region=self.response_region,
            team_name=self.tenant.tenant_name,
            suffix=" 中编辑了插件 {} 的配置组 {}".format(plugin_name, config.get("config_name", "")))
        operation_log_service.create_team_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,  # type: ignore[arg-type]
            team_name=self.tenant.tenant_name,
            old_information=old_information,
            new_information=new_information)
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
        config = request.data
        modify_type = config.get("modify_type", "")
        injection = config.get("injection")
        service_meta_type = config.get("service_meta_type")
        config_groups = plugin_config_service.get_config_group(self.plugin_version.plugin_id, self.plugin_version.build_version)
        is_pass, msg = plugin_config_service.check_group_config(
            service_meta_type, injection, config_groups)  # type: ignore[arg-type]

        if not is_pass:
            return Response(general_message(400, "param error", msg), status=400)
        create_data = [config]
        new_information = ""
        if modify_type and injection == "plugin_storage":
            plugin_config_service.create_config_items(
                self.plugin_version.plugin_id, self.plugin_version.build_version,
                service_meta_type, config["options"][0])  # type: ignore[arg-type]
        else:
            new_config = plugin_config_service.create_config_groups(self.plugin_version.plugin_id, self.plugin_version.build_version,
                                                       create_data)

            new_information = plugin_config_service.json_config_group(new_config[0])
        result = general_message(200, "success", "添加成功")
        plugin_name = operation_log_service.process_plugin_name(self.plugin.plugin_alias, self.response_region,
                                                                self.tenant.tenant_name, self.plugin.plugin_id)
        comment = operation_log_service.generate_team_comment(
            operation=Operation.IN,
            module_name=self.tenant.tenant_alias,  # type: ignore[arg-type]
            region=self.response_region,
            team_name=self.tenant.tenant_name,
            suffix=" 中添加了插件 {} 的配置组 {}".format(plugin_name, config.get("config_name", "")))
        operation_log_service.create_team_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,  # type: ignore[arg-type]
            team_name=self.tenant.tenant_name,
            new_information=new_information)
        return Response(result, status=result["code"])

    @never_cache
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
        config_group_id = request.data.get("config_group_id")
        if not config_group_id:
            return Response(general_message(400, "param error", "参数错误"), status=400)

        config_group = plugin_config_service.get_config_group_by_pk(config_group_id)
        if not config_group:
            return Response(general_message(404, "config group not exist", "配置组不存在"), status=404)
        plugin_config_service.delete_config_group_by_meta_type(config_group.plugin_id, config_group.build_version,
                                                               config_group.service_meta_type)
        # NOTE: delete_config_group_by_meta_type returns None; old_config is always None (latent bug)
        old_config = plugin_config_service.delete_config_group_by_meta_type(
            config_group.plugin_id, config_group.build_version,
            config_group.service_meta_type)  # type: ignore[func-returns-value]
        old_information = plugin_config_service.json_config_group(old_config)  # type: ignore[arg-type]

        result = general_message(200, "success", "删除成功")

        plugin_name = operation_log_service.process_plugin_name(self.plugin.plugin_alias, self.response_region,
                                                                self.tenant.tenant_name, self.plugin.plugin_id)
        comment = operation_log_service.generate_team_comment(
            operation=Operation.IN,
            module_name=self.tenant.tenant_alias,  # type: ignore[arg-type]
            region=self.response_region,
            team_name=self.tenant.tenant_name,
            suffix=" 中删除了插件 {} 的配置组 {}".format(plugin_name, config_group.config_name))
        operation_log_service.create_team_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,  # type: ignore[arg-type]
            team_name=self.tenant.tenant_name,
            old_information=old_information)
        return Response(result, status=result["code"])


class ConfigPreviewView(PluginBaseView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
        wordpress_alias = "wordpress_alias"
        mysql_alias = "mysql_alias"
        wp_ports = [80, 8081]
        mysql_port = [3306]
        wp_id = "wp_service_id"
        mysql_id = "mysql_service_id"

        config_groups = plugin_config_service.get_config_group(self.plugin_version.plugin_id, self.plugin_version.build_version)
        all_config_group: list = []
        base_ports = []
        base_services = []
        base_normal = {}
        for config_group in config_groups:
            config_items = plugin_config_service.get_config_items(
                self.plugin_version.plugin_id, self.plugin_version.build_version, config_group.service_meta_type)
            items = []
            for item in config_items:
                item_map = {}
                item_map[item.attr_name] = item.attr_default_value
                items.append(item_map)

            if config_group.service_meta_type == PluginMetaType.UPSTREAM_PORT:
                for port in wp_ports:
                    base_port: dict = {}
                    base_port["service_alias"] = wordpress_alias
                    base_port["service_id"] = wp_id
                    base_port["port"] = port
                    base_port["protocol"] = "http"
                    base_port["options"] = items
                    base_ports.append(base_port)
            if config_group.service_meta_type == PluginMetaType.DOWNSTREAM_PORT:
                for port in mysql_port:
                    base_service: dict = {}
                    base_service["service_alias"] = wordpress_alias
                    base_service["service_id"] = wp_id
                    base_service["port"] = port
                    base_service["protocol"] = "mysql"
                    base_service["options"] = items
                    base_service["depend_service_alias"] = mysql_alias
                    base_service["depend_service_id"] = mysql_id
                    base_services.append(base_service)
            if config_group.service_meta_type == PluginMetaType.UNDEFINE:
                base_normal["options"] = items

        bean = {"base_ports": base_ports, "base_services": base_services, "base_normal": base_normal.get("options", None)}

        result = general_message(200, "success", "查询成功", bean=bean, list=all_config_group)
        return Response(result, status=result["code"])
