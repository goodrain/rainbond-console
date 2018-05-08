# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app import app_service
from console.services.app_config import mnt_service
from console.views.app_config.base import AppBaseView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
import json

logger = logging.getLogger("default")


class AppMntView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务挂载的服务
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
            - name: type
              description: 查询的类别 mnt（已挂载的,默认）| unmnt (未挂载的)
              required: false
              type: string
              paramType: query
            - name: page
              description: 页号（默认第一页）
              required: false
              type: integer
              paramType: query
            - name: page_size
              description: 每页大小(默认10)
              required: false
              type: integer
              paramType: query

        """
        result = {}
        query_type = request.GET.get("type", "mnt")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        try:

            if query_type == "mnt":
                mnt_list, total = mnt_service.get_service_mnt_details(self.tenant, self.service)
            elif query_type == "unmnt":
                services = app_service.get_app_list(self.tenant.pk, self.user, self.tenant.tenant_id,
                                                    self.service.service_region)
                services_ids = [s.service_id for s in services]
                mnt_list, total = mnt_service.get_service_unmnt_details(self.tenant, self.service, services_ids, page,
                                                                 page_size)
            else:
                return Response(general_message(400, "param error", "参数错误"), status=400)
            result = general_message(200, "success", "查询成功", list=mnt_list,total=total)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def post(self, request, *args, **kwargs):
        """
        为应用添加挂载依赖
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
            - name: body
              description: 批量添加挂载[{"id":49,"path":"/add"},{"id":85,"path":"/dadd"}]
              required: true
              type: string
              paramType: body

        """
        result = {}
        try:
            dep_vol_data = request.data["body"]
            dep_vol_data = json.loads(dep_vol_data)
            code, msg = mnt_service.batch_mnt_serivce_volume(self.tenant, self.service, dep_vol_data)

            if code != 200:
                return Response(general_message(code, "add error", msg), status=code)

            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppMntManageView(AppBaseView):
    @never_cache
    @perm_required('manage_service_config')
    def delete(self, request, *args, **kwargs):
        """
        为应用取消挂载依赖
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
            - name: dep_vol_id
              description: 挂载的服务持久化ID
              required: true
              type: string
              paramType: path

        """
        result = {}
        try:
            dep_vol_id = kwargs.get("dep_vol_id", None)
            code, msg = mnt_service.delete_service_mnt_relation(self.tenant, self.service, dep_vol_id)

            if code != 200:
                return Response(general_message(code, "add error", msg), status=code)

            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

