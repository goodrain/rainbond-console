# -*- coding: utf8 -*-
"""
  Created on 2018/6/21.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")

region_api = RegionInvokeApi()


class AppVersionsView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务的构建版本
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
        """
        try:
            body = region_api.get_service_build_versions(self.response_region, self.tenant.tenant_name,
                                                         self.service.service_alias, self.tenant.enterprise_id)
            version_list = body["data"]["list"]
            result = general_message(200, "success", "查询成功", list=version_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppVersionManageView(AppBaseView):
    @never_cache
    @perm_required('manage_service_config')
    def delete(self, request, *args, **kwargs):
        """
        删除应用的某次构建版本
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
            - name: version_id
              description: 版本ID
              required: true
              type: string
              paramType: path

        """
        version_id = kwargs.get("version_id", None)
        try:
            if not version_id:
                return Response(general_message(400, "attr_name not specify", u"请指定需要删除的具体版本"))
            region_api.delete_service_build_version(self.response_region, self.tenant.tenant_name,
                                                    self.service.service_alias, version_id)
            result = general_message(200, "success", u"删除成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用的某个具体版本
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
            - name: version_id
              description: 版本id
              required: true
              type: string
              paramType: path

        """
        version_id = kwargs.get("version_id", None)
        try:
            if not version_id:
                return Response(general_message(400, "attr_name not specify", u"请指定需要查询的具体版本"))

            is_build_versions_exist = True
            try:
                region_api.get_service_build_version_by_id(self.response_region, self.tenant.tenant_name,
                                                           self.service.service_alias, version_id)
            except region_api.CallApiError as e:
                if e.status != 404:
                    raise e
                else:
                    is_build_versions_exist = False

            result = general_message(200, "success", u"查询成功", bean={"is_exist": is_build_versions_exist})
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
