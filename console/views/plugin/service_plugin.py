# -*- coding: utf8 -*-
"""
  Created on 2018/4/19.
"""
import json
import logging

from django.db import transaction
from rest_framework.response import Response

from console.services.plugin import app_plugin_service
from console.services.plugin import plugin_version_service
from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.common_services import common_services

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class ServicePluginsView(AppBaseView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用可用的插件列表
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: category
              description: 插件类型 性能分析（analysis）| 网络治理（net_manage）
              required: true
              type: string
              paramType: query

        """
        try:
            category = request.GET.get("category", "")
            if category:
                if category not in ("analysis", "net_manage"):
                    return Response(general_message(400, "param can only be analysis or net_manage", "参数错误"),
                                    status=400)
            installed_plugins, not_install_plugins = app_plugin_service.get_plugins_by_service_id(
                self.service.service_region, self.tenant.tenant_id, self.service.service_id, category)
            bean = {"installed_plugins": installed_plugins, "not_install_plugins": not_install_plugins}
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, e.message, "查询失败")
        return Response(result, status=result["code"])


class ServicePluginInstallView(AppBaseView):
    @perm_required('manage_service_plugin')
    def post(self, request, plugin_id, *args, **kwargs):
        """
        应用安装插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
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
        try:
            if not plugin_id:
                return Response(general_message(400, "params error", "参数错误"), status=400)
            if not build_version:
                plugin_version = plugin_version_service.get_newest_usable_plugin_version(plugin_id)
                build_version = plugin_version.build_version
            logger.debug("start install plugin ! plugin_id {0}  build_version {1}".format(plugin_id, build_version))
            # 1.生成console数据，存储
            code, msg = app_plugin_service.save_default_plugin_config(self.tenant, self.service, plugin_id,
                                                                      build_version)
            if code != 200:
                return Response(general_message(code, "install plugin fail", msg), status=code)
            # 2.从console数据库取数据生成region数据
            region_config = app_plugin_service.get_region_config_from_db(self.service, plugin_id, build_version)

            data = dict()
            data["plugin_id"] = plugin_id
            data["switch"] = True
            data["version_id"] = build_version
            data.update(region_config)
            code, msg, relation = app_plugin_service.create_service_plugin_relation(self.service.service_id, plugin_id,
                                                                                    build_version, "",
                                                                                    True)
            if code != 200:
                return Response(general_message(code, "install plugin fail", msg), status=code)
            region_api.install_service_plugin(self.response_region, self.tenant.tenant_name, self.service.service_alias,
                                              data)

            result = general_message(200, "success", "安装成功")
        except Exception as e:
            logger.exception(e)
            app_plugin_service.delete_service_plugin_config(self.service, plugin_id)
            app_plugin_service.delete_service_plugin_relation(self.service, plugin_id)
            result = general_message(500, e.message, "插件安装失败")
        return Response(result, status=result["code"])

    @perm_required('manage_service_plugin')
    def delete(self, request, plugin_id, *args, **kwargs):
        """
        应用卸载插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
        """
        try:
            region_api.uninstall_service_plugin(self.response_region, self.tenant.tenant_name, plugin_id,
                                                self.service.service_alias)
            app_plugin_service.delete_service_plugin_relation(self.service, plugin_id)
            app_plugin_service.delete_service_plugin_config(self.service, plugin_id)
            return Response(general_message(200, "success", "卸载成功"))
        except Exception, e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=200)


class ServicePluginOperationView(AppBaseView):
    @perm_required('manage_service_plugin')
    def put(self, request, plugin_id, *args, **kwargs):
        """
        启停用应用插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
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
        try:
            if not plugin_id:
                return Response(general_message(400, "params error", "参数异常"), status=400)
            is_active = request.data.get("is_switch", True)
            service_plugin_relation = app_plugin_service.get_service_plugin_relation(self.service.service_id, plugin_id)
            if not service_plugin_relation:
                return Response(general_message(404, "params error", "未找到关联插件的构建版本"), status=404)
            else:
                build_version = service_plugin_relation.build_version
            pbv = plugin_version_service.get_by_id_and_version(plugin_id,build_version)
            # 更新内存和cpu
            min_memory = request.data.get("min_memory", pbv.min_memory)
            min_cpu = common_services.calculate_cpu(self.service.service_region, min_memory)

            data = dict()
            data["plugin_id"] = plugin_id
            data["switch"] = is_active
            data["version_id"] = build_version
            data["plugin_memory"] = min_memory
            data["plugin_cpu"] = min_cpu
            # 更新数据中心数据参数
            region_api.update_plugin_service_relation(self.response_region, self.tenant.tenant_name,
                                                      self.service.service_alias, data)
            # 更新本地数据
            app_plugin_service.start_stop_service_plugin(self.service.service_id, plugin_id, is_active)
            pbv.min_memory = min_memory
            pbv.min_cpu = min_cpu
            pbv.save()
            result = general_message(200, "success", "操作成功")
        except Exception, e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class ServicePluginConfigView(AppBaseView):
    @perm_required('view_service')
    def get(self, request, plugin_id, *args, **kwargs):
        """
        应用插件查看配置
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
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
            logger.error("plugin.relation", u'参数错误，plugin_id and version_id')
            return Response(general_message(400, "params error", "请指定插件版本"), status=400)
        try:
            result_bean = app_plugin_service.get_service_plugin_config(self.tenant, self.service, plugin_id,
                                                                       build_version)
            pbv = plugin_version_service.get_by_id_and_version(plugin_id, build_version)
            if pbv:
                result_bean["build_info"] = pbv.update_info
                result_bean["memory"] = pbv.min_memory
            result = general_message(200, "success", "查询成功", bean=result_bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, result["code"])

    @perm_required('manage_service_plugin')
    @transaction.atomic
    def put(self, request, plugin_id, *args, **kwargs):
        """
        应用插件配置更新
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
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
        sid = None
        try:
            logger.debug("update service plugin config ")
            config = json.loads(request.body)
            logger.debug("====> {0}".format(config))
            if not config:
                return Response(general_message(400, "params error", "参数配置不可为空"), status=400)
            pbv = plugin_version_service.get_newest_usable_plugin_version(plugin_id)
            if not pbv:
                return Response(general_message(400, "no usable plugin version", "无最新更新的版本信息，无法更新配置"), status=400)
            sid = transaction.savepoint()
            # 删除原有配置
            app_plugin_service.delete_service_plugin_config(self.service, plugin_id)
            # 全量插入新配置
            app_plugin_service.update_service_plugin_config(self.service, plugin_id, pbv.build_version, config)
            # 更新数据中心配置
            region_config = app_plugin_service.get_region_config_from_db(self.service, plugin_id, pbv.build_version)
            region_api.update_service_plugin_config(self.response_region, self.tenant.tenant_name,
                                                    self.service.service_alias, plugin_id, region_config)
            # 提交操作
            transaction.savepoint_commit(sid)
            result = general_message(200, "success", "配置更新成功")
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            result = error_message(e.message)
        return Response(result, result["code"])
