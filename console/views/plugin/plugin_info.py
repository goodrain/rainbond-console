# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
from rest_framework.response import Response

from console.views.base import RegionTenantHeaderView
from console.views.plugin.base import PluginBaseView
from django.views.decorators.cache import never_cache

from goodrain_web.tools import JuncheePaginator
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
import logging
from console.services.plugin import plugin_version_service, plugin_service, plugin_config_service,app_plugin_service
import threading
from console.repositories.plugin import app_plugin_relation_repo, plugin_version_repo

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class PluginBaseInfoView(PluginBaseView):
    @never_cache
    @perm_required('view_plugin')
    def get(self, request, *args, **kwargs):
        """
        获取插件基础信息
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
        """
        try:
            base_info = self.plugin
            data = base_info.to_dict()
            newest_build_version = plugin_version_service.get_newest_plugin_version(self.plugin.plugin_id)
            if newest_build_version:
                data.update(newest_build_version.to_dict())
            result = general_message(200, "success", "查询成功", bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class PluginEventLogView(PluginBaseView):
    @never_cache
    @perm_required('view_plugin')
    def get(self, request, *args, **kwargs):
        """
        获取event事件
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
              description: 插件版本
              required: true
              type: string
              paramType: path
            - name: level
              description: 事件等级
              required: true
              type: string
              paramType: query
        """
        try:
            level = request.GET.get("level", "info")
            event_id = self.plugin_version.event_id
            logs = plugin_service.get_plugin_event_log(self.response_region, self.tenant, event_id, level)
            result = general_message(200, "success", "查询成功", list=logs)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AllPluginVersionInfoView(PluginBaseView):
    @never_cache
    @perm_required('view_plugin')
    def get(self, request, *args, **kwargs):
        """
        插件构建历史信息展示
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
            - name: page
              description: 当前页
              required: true
              type: string
              paramType: query
            - name: page_size
              description: 每页大小,默认为8
              required: true
              type: string
              paramType: query
        """
        try:
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 8)
            pbvs = plugin_version_service.get_plugin_versions(self.plugin.plugin_id)
            paginator = JuncheePaginator(pbvs, int(page_size))
            show_pbvs = paginator.page(int(page))

            update_status_thread = threading.Thread(target=plugin_version_service.update_plugin_build_status,
                                                    args=(self.response_region, self.tenant))
            update_status_thread.start()

            data = [pbv.to_dict() for pbv in show_pbvs]
            result = general_message(200, "success", "查询成功", list=data, total=paginator.count, current_page=int(page),
                                     next_page=int(page) + 1)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class PluginVersionInfoView(PluginBaseView):
    @never_cache
    @perm_required('view_plugin')
    def get(self, request, *args, **kwargs):
        """
        获取插件某个版本的信息
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
              description: 插件版本
              required: true
              type: string
              paramType: path
        """
        try:
            base_info = self.plugin
            data = base_info.to_dict()
            data.update(self.plugin_version.to_dict())
            update_status_thread = threading.Thread(target=plugin_version_service.update_plugin_build_status,
                                                    args=(self.response_region, self.tenant))
            update_status_thread.start()
            result = general_message(200, "success", "查询成功", bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_plugin')
    def put(self, request, *args, **kwargs):
        """
        更新某个版本插件的信息
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
              description: 插件版本
              required: true
              type: string
              paramType: path
            - name: plugin_alias
              description: 插件名称
              required: false
              type: string
              paramType: form
            - name: update_info
              description: 更新信息
              required: false
              type: string
              paramType: form
            - name: build_cmd
              description: 构建命令
              required: false
              type: string
              paramType: form
            - name: image_tag
              description: 镜像版本
              required: false
              type: string
              paramType: form
            - name: code_version
              description: 代码版本
              required: false
              type: string
              paramType: form
            - name: min_memory
              description: 最小内存
              required: false
              type: string
              paramType: form

        """
        try:
            plugin_alias = request.data.get("plugin_alias", self.plugin.plugin_alias)
            update_info = request.data.get("update_info", self.plugin_version.update_info)
            build_cmd = request.data.get("build_cmd", self.plugin_version.build_cmd)
            image_tag = request.data.get("image_tag", self.plugin_version.image_tag)
            code_version = request.data.get("code_version", self.plugin_version.code_version)
            min_memory = request.data.get("min_memory", self.plugin_version.min_memory)
            min_cpu = plugin_version_service.calculate_cpu(self.response_region, min_memory)
            # 保存基本信息
            self.plugin.plugin_alias = plugin_alias
            self.plugin.save()
            # 保存版本信息
            self.plugin_version.update_info = update_info
            self.plugin_version.build_cmd = build_cmd
            self.plugin_version.image_tag = image_tag
            self.plugin_version.code_version = code_version
            self.plugin_version.min_memory = min_memory
            self.plugin_version.min_cpu = min_cpu
            self.plugin_version.save()
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_plugin')
    def delete(self, request, *args, **kwargs):
        """
        删除插件某个版本
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

            app_plugin_relations = app_plugin_relation_repo.get_service_plugin_relation_by_plugin_unique_key(
                self.plugin_version.plugin_id,
                self.plugin_version.build_version)
            if app_plugin_relations:
                return Response(general_message(409, "plugin is being using", "插件已被使用，无法删除"), status=409)
            count_of_version = plugin_version_repo.get_plugin_versions(self.plugin_version.plugin_id).count()
            if count_of_version == 1:
                return Response(general_message(409, "at least keep one version", "至少保留一个插件版本"), status=409)
            # 数据中心端删除
            region_api.delete_plugin_version(self.response_region, self.tenant.tenant_name,
                                             self.plugin_version.plugin_id,
                                             self.plugin_version.build_version)
            plugin_version_service.delete_build_version_by_id_and_version(self.plugin_version.plugin_id,
                                                                          self.plugin_version.build_version)

            plugin_config_service.delete_plugin_version_config(self.plugin_version.plugin_id,
                                                               self.plugin_version.build_version)
            result = general_message(200, "success", "删除成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AllPluginBaseInfoView(RegionTenantHeaderView):
    @never_cache
    @perm_required('view_plugin')
    def get(self, request, *args, **kwargs):
        """
        获取插件基础信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
        """
        try:
            plugin_list = plugin_service.get_tenant_plugins(self.response_region, self.tenant)
            dict_list = [plugin.to_dict() for plugin in plugin_list]
            result = general_message(200, "success", "查询成功", list=dict_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class PluginUsedServiceView(PluginBaseView):
    @never_cache
    @perm_required('view_plugin')
    def get(self, request, *args, **kwargs):
        """
        获取插件被哪些当前团队哪些应用使用
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
            - name: page
              description: 当前页
              required: true
              type: string
              paramType: query
            - name: page_size
              description: 每页大小,默认为10
              required: true
              type: string
              paramType: query
        """
        try:
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 10)
            data = app_plugin_service.get_plugin_used_services(self.plugin.plugin_id, self.tenant.tenant_id, page,
                                                               page_size)

            result = general_message(200, "success", "查询成功", list=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
