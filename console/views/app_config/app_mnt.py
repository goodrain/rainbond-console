# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import json
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app import app_service
from console.services.app_config import mnt_service
from console.utils.reqparse import parse_argument
from console.views.app_config.base import AppBaseView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class AppMntView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件挂载的组件
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
        dep_app_name = request.GET.get("dep_app_name", "")
        if dep_app_name == "undefined":
            dep_app_name = ""
        dep_app_group = request.GET.get("dep_app_group", "")
        if dep_app_group == "undefined":
            dep_app_group = ""
        config_name = request.GET.get("config_name", "")
        query_type = request.GET.get("type", "mnt")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        volume_types = parse_argument(request, 'volume_types', value_type=list)
        is_config = parse_argument(request, 'is_config', value_type=bool, default=False)

        if volume_types is not None and ('config-file' in volume_types):
            is_config = True

        if query_type == "mnt":
            mnt_list, total = mnt_service.get_service_mnt_details(self.tenant, self.service, volume_types)
        elif query_type == "unmnt":
            services = app_service.get_app_list(self.tenant.tenant_id, self.service.service_region, dep_app_name)
            services_ids = [s.service_id for s in services]
            mnt_list, total = mnt_service.get_service_unmount_volume_list(self.tenant, self.service, services_ids, page,
                                                                          page_size, is_config, dep_app_group, config_name)
        else:
            return Response(general_message(400, "param error", "参数错误"), status=400)
        result = general_message(200, "success", "查询成功", list=mnt_list, total=total)

        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        为组件添加挂载依赖
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
            - name: body
              description: 批量添加挂载[{"id":49,"path":"/add"},{"id":85,"path":"/dadd"}]
              required: true
              type: string
              paramType: body

        """
        dep_vol_data = request.data["body"]
        dep_vol_data = json.loads(dep_vol_data)
        mnt_service.batch_mnt_serivce_volume(self.tenant, self.service, dep_vol_data, self.user.nick_name)
        result = general_message(200, "success", "操作成功")
        return Response(result, status=result["code"])


class AppMntManageView(AppBaseView):
    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        为组件取消挂载依赖
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
            - name: dep_vol_id
              description: 挂载的组件持久化ID
              required: true
              type: string
              paramType: path

        """
        dep_vol_id = kwargs.get("dep_vol_id", None)
        code, msg = mnt_service.delete_service_mnt_relation(self.tenant, self.service, dep_vol_id, self.user.nick_name)

        if code != 200:
            return Response(general_message(code, "add error", msg), status=code)

        result = general_message(200, "success", "操作成功")
        return Response(result, status=result["code"])
