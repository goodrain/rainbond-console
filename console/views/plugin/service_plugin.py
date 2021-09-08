# -*- coding: utf8 -*-
"""
  Created on 2018/4/19.
"""
import json
import logging

from console.services.plugin import app_plugin_service, plugin_version_service
from console.views.app_config.base import AppBaseView
from django.db import transaction
from rest_framework.response import Response
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class ServicePluginsView(AppBaseView):
    def get(self, request, *args, **kwargs):
        """
        获取组件可用的插件列表
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: category
              description: 插件类型 性能分析（analysis）| 网络治理（net_manage）
              required: true
              type: string
              paramType: query

        """
        category = request.GET.get("category", "")
        if category:
            if category not in ("analysis", "net_manage"):
                return Response(general_message(400, "param can only be analysis or net_manage", "参数错误"), status=400)
        installed_plugins, not_install_plugins = app_plugin_service.get_plugins_by_service_id(
            self.service.service_region, self.tenant.tenant_id, self.service.service_id, category)
        bean = {"installed_plugins": installed_plugins, "not_install_plugins": not_install_plugins}
        result = general_message(200, "success", "查询成功", bean=bean)
        return Response(result, status=result["code"])


class ServicePluginInstallView(AppBaseView):
    def post(self, request, plugin_id, *args, **kwargs):
        """
        组件安装插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 插件版本
              required: true
              type: string
              paramType: form
        """
        result = {}
        build_version = request.data.get("build_version", None)
        if not plugin_id:
            return Response(general_message(400, "not found plugin_id", "参数错误"), status=400)
        app_plugin_service.check_the_same_plugin(plugin_id, self.tenant.tenant_id, self.service.service_id)
        app_plugin_service.install_new_plugin(self.response_region, self.tenant, self.service, plugin_id, build_version,
                                              self.user)

        result = general_message(200, "success", "安装成功")
        return Response(result, status=result["code"])

    def delete(self, request, plugin_id, *args, **kwargs):
        """
        组件卸载插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
        """
        body = dict()
        body["operator"] = self.user.nick_name
        region_api.uninstall_service_plugin(self.response_region, self.tenant.tenant_name, plugin_id,
                                            self.service.service_alias, body)
        app_plugin_service.delete_service_plugin_relation(self.service, plugin_id)
        app_plugin_service.delete_service_plugin_config(self.service, plugin_id)
        return Response(general_message(200, "success", "卸载成功"))


class ServicePluginOperationView(AppBaseView):
    def put(self, request, plugin_id, *args, **kwargs):
        """
        启停用组件插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: is_switch
              description: 插件启停状态
              required: false
              type: boolean
              paramType: form
            - name: min_memory
              description: 插件内存
              required: false
              type: boolean
              paramType: form
        """
        if not plugin_id:
            return Response(general_message(400, "not found plugin_id", "参数异常"), status=400)
        is_active = request.data.get("is_switch", True)
        service_plugin_relation = app_plugin_service.get_service_plugin_relation(self.service.service_id, plugin_id)
        if not service_plugin_relation:
            return Response(general_message(404, "not found plugin relation", "未找到组件使用的插件"), status=404)
        else:
            build_version = service_plugin_relation.build_version
        # 更新内存和cpu
        memory = request.data.get("min_memory")
        cpu = request.data.get("min_cpu")

        data = dict()
        data["plugin_id"] = plugin_id
        data["switch"] = is_active
        data["version_id"] = build_version
        if memory is not None:
            data["plugin_memory"] = int(memory)
        if cpu is not None:
            data["plugin_cpu"] = int(cpu)
        # 更新数据中心数据参数
        region_api.update_plugin_service_relation(self.response_region, self.tenant.tenant_name, self.service.service_alias,
                                                  data)
        # 更新本地数据
        app_plugin_service.start_stop_service_plugin(self.service.service_id, plugin_id, is_active, cpu, memory)
        result = general_message(200, "success", "操作成功")
        return Response(result, status=result["code"])


class ServicePluginConfigView(AppBaseView):
    def get(self, request, plugin_id, *args, **kwargs):
        """
        组件插件查看配置
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 插件版本
              required: true
              type: string
              paramType: query
        """
        build_version = request.GET.get("build_version", None)
        if not plugin_id or not build_version:
            logger.error("plugin.relation", '参数错误，plugin_id and version_id')
            return Response(general_message(400, "params error", "请指定插件版本"), status=400)
        result_bean = app_plugin_service.get_service_plugin_config(self.tenant, self.service, plugin_id, build_version)
        svc_plugin_relation = app_plugin_service.get_service_plugin_relation(self.service.service_id, plugin_id)
        pbv = plugin_version_service.get_by_id_and_version(self.tenant.tenant_id, plugin_id, build_version)
        if pbv:
            result_bean["build_info"] = pbv.update_info
            result_bean["memory"] = svc_plugin_relation.min_memory if svc_plugin_relation else pbv.min_memory
        result = general_message(200, "success", "查询成功", bean=result_bean)
        return Response(result, result["code"])

    @transaction.atomic
    def put(self, request, plugin_id, *args, **kwargs):
        """
        组件插件配置更新
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: body
              description: 配置内容
              required: true
              type: string
              paramType: body

        """
        config = json.loads(request.body)
        if not config:
            return Response(general_message(400, "params error", "参数配置不可为空"), status=400)
        pbv = plugin_version_service.get_newest_usable_plugin_version(self.tenant.tenant_id, plugin_id)
        if not pbv:
            return Response(general_message(400, "no usable plugin version", "无最新更新的版本信息，无法更新配置"), status=400)
        # update service plugin config
        app_plugin_service.update_service_plugin_config(self.tenant, self.service, plugin_id, pbv.build_version, config,
                                                        self.response_region)
        result = general_message(200, "success", "配置更新成功")
        return Response(result, result["code"])
