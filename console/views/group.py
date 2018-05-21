# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
from rest_framework.response import Response

from console.views.base import RegionTenantHeaderView
import logging

from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.group_service import group_service
from console.services.compose_service import compose_service

logger = logging.getLogger("default")


class TenantGroupView(RegionTenantHeaderView):
    @perm_required("view_service")
    def get(self, request, *args, **kwargs):
        """
        查询租户在指定数据中心下的组
        ---
        """
        try:
            groups = group_service.get_tenant_groups_by_region(self.tenant, self.response_region)
            data = []
            for group in groups:
                data.append({"group_name": group.group_name, "group_id": group.ID})
            data.append({"group_name": "未分组", "group_id": -1})
            result = general_message(200, "success", "查询成功", list=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @perm_required("manage_group")
    def post(self, request, *args, **kwargs):
        """
        添加组信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_name
              description: 组名称
              required: true
              type: string
              paramType: form

        """
        try:
            group_name = request.data.get("group_name", None)
            code, msg, data = group_service.add_group(self.tenant, self.response_region, group_name)
            if code != 200:
                result = general_message(code, "group add error", msg)
            else:
                result = general_message(code, "success", msg, bean=data.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class TenantGroupOperationView(RegionTenantHeaderView):
    @perm_required("manage_group")
    def put(self, request, *args, **kwargs):
        """
            修改组信息
            ---
            parameters:
                - name: tenantName
                  description: 租户名
                  required: true
                  type: string
                  paramType: path
                - name: group_id
                  description: 组id
                  required: true
                  type: string
                  paramType: path
                - name: group_name
                  description: 组名称
                  required: true
                  type: string
                  paramType: form

        """
        try:
            group_name = request.data.get("group_name", None)
            group_id = int(kwargs.get("group_id", None))
            code, msg, data = group_service.update_group(self.tenant, self.response_region, group_id, group_name)
            if code != 200:
                result = general_message(code, "group add error", msg)
            else:
                result = general_message(code, "success", msg)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @perm_required("manage_group")
    def delete(self, request, *args, **kwargs):
        """
            删除组信息
            ---
            parameters:
                - name: tenantName
                  description: 租户名
                  required: true
                  type: string
                  paramType: path
                - name: group_id
                  description: 组id
                  required: true
                  type: string
                  paramType: path

        """
        try:
            group_id = int(kwargs.get("group_id", None))
            code, msg, data = group_service.delete_group(group_id)
            if code != 200:
                result = general_message(code, "delete group error", msg)
            else:
                result = general_message(code, "success", msg)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    def get(self, request, *args, **kwargs):
        """
            查询组信息
            ---
            parameters:
                - name: tenantName
                  description: 租户名
                  required: true
                  type: string
                  paramType: path
                - name: group_id
                  description: 组id
                  required: true
                  type: string
                  paramType: path

        """
        try:
            group_id = int(kwargs.get("group_id", None))
            code, msg, data = group_service.get_group_by_id(self.tenant, self.response_region, int(group_id))
            data["create_status"] = "complete"
            data["compose_id"] = None
            if group_id != -1:
                compose_group = compose_service.get_group_compose_by_group_id(group_id)
                if compose_group:
                    data["create_status"] = compose_group.create_status
                    data["compose_id"] = compose_group.compose_id

            if code != 200:
                result = general_message(code, "group query error", msg)
            else:
                result = general_message(code, "success", msg, bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
