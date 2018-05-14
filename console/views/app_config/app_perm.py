# -*- coding: utf8 -*-
"""
  Created on 18/1/31.
"""
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.perm_services import app_perm_service
import logging

logger = logging.getLogger("default")


class ServicePermView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取为服务添加的用户权限
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
        result = {}
        try:
            service_perms = app_perm_service.get_service_perm(self.service)
            result = general_message(200, "success", "查询成功", list=service_perms)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_member_perms')
    def post(self, request, *args, **kwargs):
        """
        为服务添加的用户权限
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
            - name: user_id
              description: 用户id
              required: true
              type: string
              paramType: form
            - name: identity
              description: 权限
              required: true
              type: string
              paramType: form

        """
        result = {}
        try:
            identity = request.data.get("identity", None)
            user_id = request.data.get("user_id", None)
            if not identity or not user_id:
                return Response(general_message(400, "params error", "参数异常"), status=400)
            code, msg, service_perm = app_perm_service.add_service_perm(self.user, user_id, self.tenant, self.service,
                                                                        identity)
            if code != 200:
                return Response(general_message(code, "add service perm error", msg), status=400)
            result = general_message(code, "success", "操作成功", bean=service_perm.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_member_perms')
    def put(self, request, *args, **kwargs):
        """
        为服务修改用户的权限
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
            - name: user_id
              description: 用户id
              required: true
              type: string
              paramType: form
            - name: identity
              description: 权限
              required: true
              type: string
              paramType: form

        """
        result = {}
        try:
            identity = request.data.get("identity", None)
            user_id = request.data.get("user_id", None)
            if not identity or not user_id:
                return Response(general_message(400, "params error", "参数异常"), status=400)
            code, msg, service_perm = app_perm_service.update_service_perm(self.user, user_id,
                                                                           self.service,
                                                                           identity)
            if code != 200:
                return Response(general_message(code, "update service perm error", msg), status=400)
            result = general_message(code, "success", "修改成功", bean=service_perm.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_member_perms')
    def delete(self, request, *args, **kwargs):
        """
        删除应用添加的权限
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
            - name: user_id
              description: 用户id
              required: true
              type: string
              paramType: form

        """
        result = {}
        try:
            user_id = request.data.get("user_id", None)
            if not user_id:
                return Response(general_message(400, "params error", "参数异常"), status=400)
            code, msg = app_perm_service.delete_service_perm(self.user, user_id,
                                                             self.service)
            if code != 200:
                return Response(general_message(code, "delete service perm error", msg), status=400)
            result = general_message(code, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_member_perms')
    def patch(self, request, *args, **kwargs):
        """
        为服务批量添加用户权限
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
            - name: user_ids
              description: 多个用户id，以逗号分隔
              required: true
              type: string
              paramType: form
            - name: identity
              description: 权限
              required: true
              type: string
              paramType: form

        """
        result = {}
        try:
            identity = request.data.get("identity", None)
            user_ids = request.data.get("user_ids", None)
            if not identity or not user_ids:
                return Response(general_message(400, "params error", "参数异常"), status=400)
            try:
                user_id_list = [int(user_id) for user_id in user_ids.split(",")]
            except Exception as e:
                logger.exception(e)
                result = general_message(400, "Incorrect parameter format", "参数格式错误")
                return Response(result, status=400)
            service_perm_list = []
            for u_id in user_id_list:
                code, msg, service_perm = app_perm_service.add_service_perm(self.user, u_id, self.tenant, self.service,
                                                                            identity)
                if code != 200:
                    return Response(general_message(code, "add service perm error", msg), status=400)

                service_perm_list.append(
                    {"ID": service_perm.pk, "user_id": service_perm.user_id, "service_id": service_perm.service_id,
                     "identity": service_perm.identity, "role_id": service_perm.role_id})
            result = general_message(200, "success", "操作成功", list=service_perm_list)
        except Exception as e:
            print(e)
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
