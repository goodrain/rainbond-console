# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.views.app_config.base import AppBaseView
from console.services.app_config.env_service import AppEnvVarService
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from django.forms.models import model_to_dict
import logging

logger = logging.getLogger("default")

env_var_service = AppEnvVarService()


class AppEnvView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务的环境变量参数
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
            - name: env_type
              description: 环境变量类型[对内环境变量（inner）|对外环境变量（outer）]
              required: true
              type: string
              paramType: query
        """
        try:
            env_type = request.GET.get("env_type", None)
            if not env_type:
                return Response(general_message(400, "param error", "参数异常"), status=400)
            if env_type not in ("inner", "outer"):
                return Response(general_message(400, "param error", "参数异常"), status=400)
            if env_type == "inner":
                tenant_service_envs = env_var_service.get_service_inner_env(self.service)
            else:
                tenant_service_envs = env_var_service.get_service_outer_env(self.service)
            env_list = [model_to_dict(env) for env in tenant_service_envs]
            result = general_message(200, "success", "查询成功", list=env_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def post(self, request, *args, **kwargs):
        """
        为应用添加环境变量
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
            - name: name
              description: 环境变量说明
              required: false
              type: string
              paramType: form
            - name: attr_name
              description: 环境变量名称 大写
              required: true
              type: string
              paramType: form
            - name: attr_value
              description: 环境变量值
              required: true
              type: string
              paramType: form
            - name: scope
              description: 生效范围 inner(对内),outer(对外)
              required: true
              type: string
              paramType: form
            - name: is_change
              description: 是否可更改 (默认可更改)
              required: false
              type: string
              paramType: form

        """
        name = request.data.get("name", None)
        attr_name = request.data.get("attr_name", None)
        attr_value = request.data.get("attr_value", None)
        scope = request.data.get('scope', None)
        is_change = request.data.get('is_change', True)
        try:
            if not scope:
                return Response(general_message(400, "params error", "参数异常"), status=400)
            if scope not in ("inner", "outer"):
                return Response(general_message(400, "params error", "scope范围只能是inner或outer"), status=400)
            code, msg, data = env_var_service.add_service_env_var(self.tenant, self.service, 0, name, attr_name,
                                                                  attr_value, is_change, scope)
            if code != 200:
                result = general_message(code, "add env error", msg)
                return Response(result, status=code)
            result = general_message(code, msg, u"环境变量添加成功", bean=data.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppEnvManageView(AppBaseView):
    @never_cache
    @perm_required('manage_service_config')
    def delete(self, request, *args, **kwargs):
        """
        删除应用的某个环境变量
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
            - name: attr_name
              description: 环境变量名称 大写
              required: true
              type: string
              paramType: path

        """
        attr_name = kwargs.get("attr_name", None)
        if not attr_name:
            return Response(general_message(400, "attr_name not specify", u"环境变量名未指定"))
        try:
            env_var_service.delete_env_by_attr_name(self.tenant, self.service, attr_name)
            result = general_message(200, "success", u"删除成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用的某个环境变量详情
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
            - name: attr_name
              description: 环境变量名称 大写
              required: true
              type: string
              paramType: path

        """
        attr_name = kwargs.get("attr_name", None)
        if not attr_name:
            return Response(general_message(400, "attr_name not specify", u"环境变量名未指定"))
        try:
            env = env_var_service.get_env_by_attr_name(self.tenant, self.service, attr_name)

            result = general_message(200, "success", u"查询成功", bean=model_to_dict(env))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        修改应用环境变量
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
            - name: attr_name
              description: 环境变量名称 大写
              required: true
              type: string
              paramType: path
             - name: name
              description: 环境变量说明
              required: false
              type: string
              paramType: form
            - name: attr_value
              description: 环境变量值
              required: true
              type: string
              paramType: form

        """
        attr_name = kwargs.get("attr_name", None)
        if not attr_name:
            return Response(general_message(400, "attr_name not specify", u"环境变量名未指定"))
        try:
            name = request.data.get("name", None)
            attr_value = request.data.get("attr_value", None)

            code, msg, env = env_var_service.update_env_by_attr_name(self.tenant, self.service, attr_name, name,
                                                                     attr_value)
            if code != 200:
                return Response(general_message(code, "update value error", msg))
            result = general_message(200, "success", u"查询成功", bean=model_to_dict(env))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
