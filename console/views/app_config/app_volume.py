# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from console.services.app_config import volume_service
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from django.forms.models import model_to_dict
import logging

logger = logging.getLogger("default")


class AppVolumeView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务的持久化路径
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
            tenant_service_volumes = volume_service.get_service_volumes(self.tenant, self.service)

            volumes = [model_to_dict(volume) for volume in tenant_service_volumes]
            result = general_message(200, "success", "查询成功", list=volumes)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def post(self, request, *args, **kwargs):
        """
        为应用添加持久化目录
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
            - name: volume_name
              description: 持久化名称
              required: true
              type: string
              paramType: form
            - name: volume_type
              description: 持久化类型
              required: true
              type: string
              paramType: form
            - name: volume_path
              description: 持久化路径
              required: true
              type: string
              paramType: form

        """
        volume_name = request.data.get("volume_name", None)
        volume_type = request.data.get("volume_type", None)
        volume_path = request.data.get("volume_path", None)
        try:
            code, msg, data = volume_service.add_service_volume(self.tenant, self.service, volume_path, volume_type,
                                                                volume_name)
            if code != 200:
                result = general_message(code, "add volume error", msg)
                return Response(result, status=code)
            result = general_message(code, msg, u"持久化路径添加成功", bean=data.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppVolumeManageView(AppBaseView):
    @never_cache
    @perm_required('manage_service_config')
    def delete(self, request, *args, **kwargs):
        """
        删除应用的某个持久化路径
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
            - name: volume_id
              description: 需要删除的持久化ID
              required: true
              type: string
              paramType: path

        """
        volume_id = kwargs.get("volume_id", None)
        if not volume_id:
            return Response(general_message(400, "attr_name not specify", u"未指定需要删除的持久化路径"))
        try:
            code, msg, volume = volume_service.delete_service_volume_by_id(self.tenant, self.service, int(volume_id))
            if code != 200:
                return Response(general_message(code, "delete volume error", msg))

            result = general_message(200, "success", u"删除成功", bean=volume.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
