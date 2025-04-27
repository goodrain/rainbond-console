# -*- coding: utf8 -*-
"""
  Created on 18/3/4.
"""
import datetime
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.operation_log import operation_log_service, Operation
from console.services.plugin import plugin_config_service
from console.services.plugin import plugin_service
from console.services.plugin import plugin_version_service
from console.views.plugin.base import PluginBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class PluginBuildView(PluginBaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        构建插件
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
            - name: update_info
              description: 更新说明
              required: false
              type: string
              paramType: form
        """
        update_info = request.data.get("update_info", None)
        if self.plugin_version.build_status == "building":
            return Response(general_message(409, "too offen", "构建中，请稍后再试"), status=409)
        if update_info:
            self.plugin_version.update_info = update_info
            self.plugin_version.save()
        event_id = make_uuid()
        self.plugin_version.build_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.plugin_version.save()
        # prepare image info for
        image_info = {
            "hub_user": self.plugin.username,
            "hub_password": self.plugin.password,
        }
        try:
            plugin_service.build_plugin(self.response_region, self.plugin, self.plugin_version, self.user, self.tenant,
                                        event_id, image_info)
            self.plugin_version.build_status = "building"
            self.plugin_version.event_id = event_id
            self.plugin_version.save()
            bean = {"event_id": event_id}
            result = general_message(200, "success", "操作成功", bean=bean)
            plugin_name = operation_log_service.process_plugin_name(self.plugin.plugin_alias, self.response_region,
                                                                    self.tenant.tenant_name, self.plugin.plugin_id)
            comment = operation_log_service.generate_team_comment(
                operation=Operation.IN,
                module_name=self.tenant.tenant_alias,
                region=self.response_region,
                team_name=self.tenant.tenant_name,
                suffix=" 中构建了插件 {}".format(plugin_name))
            operation_log_service.create_team_log(
                user=self.user, comment=comment, enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, "region invoke error", "构建失败，请查看镜像或源代码是否正确")
        return Response(result, status=result["code"])


class CreatePluginVersionView(PluginBaseView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        创建插件新版本
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
        plugin_versions = plugin_version_service.get_plugin_versions(self.tenant.tenant_id, self.plugin.plugin_id)

        if not plugin_versions:
            return Response(general_message(412, "current version not exist", "插件不存在任何版本，无法创建"), status=412)
        if self.plugin.origin != "source_code":
            return Response(general_message(412, "market plugin can not create new version", "云市插件不能创建版本"), status=412)
        pbv = plugin_versions[0]
        if pbv.build_status != "build_success":
            return Response(general_message(412, "no useable plugin version", "您的插件构建未成功，无法创建新版本"), status=412)

        new_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        plugin_version_service.copy_build_version_info(self.tenant.tenant_id, pbv.plugin_id, pbv.build_version, new_version)
        plugin_config_service.copy_config_group(pbv.plugin_id, pbv.build_version, new_version)
        plugin_config_service.copy_group_items(pbv.plugin_id, pbv.build_version, new_version)

        pbv.plugin_version_status = "fixed"
        pbv.save()
        bean = {"plugin_id": self.plugin.plugin_id, "new_version": new_version}
        result = general_message(200, "success", "操作成功", bean=bean)
        return Response(result, status=result["code"])


class PluginBuildStatusView(PluginBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取插件构建状态
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
              description: 构建版本
              required: true
              type: string
              paramType: path
        """
        pbv = plugin_version_service.get_plugin_build_status(self.response_region, self.tenant, self.plugin_version.plugin_id,
                                                             self.plugin_version.build_version)
        result = general_message(200, "success", "查询成功", {"status": pbv.build_status, "event_id": pbv.event_id})
        return Response(result, status=result["code"])
