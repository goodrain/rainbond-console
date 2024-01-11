# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import json
import logging

from django.db import connection
from django.forms.models import model_to_dict
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from console.repositories.app_config import compile_env_repo
from console.services.app_config.env_service import AppEnvVarService
from console.utils.reqparse import parse_item
from console.utils.response import MessageResponse
from console.views.app_config.base import AppBaseView
from www.utils.return_message import general_message
from console.exception.main import AbortRequest

logger = logging.getLogger("default")

env_var_service = AppEnvVarService()


class AppEnvView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件的环境变量参数
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
            - name: env_type
              description: 环境变量类型[对内环境变量（inner）|对外环境变量（outer）]
              required: true
              type: string
              paramType: query
        """
        env_type = request.GET.get("env_type", None)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        env_name = request.GET.get("env_name", None)

        if not env_type:
            return Response(general_message(400, "param error", "参数异常"), status=400)
        if env_type not in ("inner", "outer"):
            return Response(general_message(400, "param error", "参数异常"), status=400)
        env_list = []
        if env_type == "inner":
            if env_name:
                # 获取总数
                cursor = connection.cursor()
                cursor.execute("select count(*) from tenant_service_env_var where tenant_id='{0}' and \
                        service_id='{1}' and scope='inner' and attr_name like '%{2}%';".format(
                    self.service.tenant_id, self.service.service_id, env_name))
                env_count = cursor.fetchall()

                total = env_count[0][0]
                start = (page - 1) * page_size
                remaining_num = total - (page - 1) * page_size
                end = page_size
                if remaining_num < page_size:
                    end = remaining_num

                cursor = connection.cursor()
                cursor.execute("select ID, tenant_id, service_id, container_port, name, attr_name, \
                        attr_value, is_change, scope, create_time from tenant_service_env_var \
                            where tenant_id='{0}' and service_id='{1}' and scope='inner' and \
                                attr_name like '%{2}%' order by attr_name LIMIT {3},{4};".format(
                    self.service.tenant_id, self.service.service_id, env_name, start, end))
                env_tuples = cursor.fetchall()
            else:

                cursor = connection.cursor()
                cursor.execute("select count(*) from tenant_service_env_var where tenant_id='{0}' and service_id='{1}'\
                         and scope='inner';".format(self.service.tenant_id, self.service.service_id))
                env_count = cursor.fetchall()

                total = env_count[0][0]
                start = (page - 1) * page_size
                remaining_num = total - (page - 1) * page_size
                end = page_size
                if remaining_num < page_size:
                    end = remaining_num

                cursor = connection.cursor()
                cursor.execute("select ID, tenant_id, service_id, container_port, name, attr_name, attr_value,\
                         is_change, scope, create_time from tenant_service_env_var where tenant_id='{0}' \
                             and service_id='{1}' and scope='inner' order by attr_name LIMIT {2},{3};".format(
                    self.service.tenant_id, self.service.service_id, start, end))
                env_tuples = cursor.fetchall()
            if len(env_tuples) > 0:
                for env_tuple in env_tuples:
                    env_dict = dict()
                    env_dict["ID"] = env_tuple[0]
                    env_dict["tenant_id"] = env_tuple[1]
                    env_dict["service_id"] = env_tuple[2]
                    env_dict["container_port"] = env_tuple[3]
                    env_dict["name"] = env_tuple[4]
                    env_dict["attr_name"] = env_tuple[5]
                    env_dict["attr_value"] = env_tuple[6]
                    env_dict["is_change"] = env_tuple[7]
                    env_dict["scope"] = env_tuple[8]
                    env_dict["create_time"] = env_tuple[9]
                    env_list.append(env_dict)
            bean = {"total": total}

        else:
            if env_name:

                cursor = connection.cursor()
                cursor.execute("select count(*) from tenant_service_env_var where tenant_id='{0}' and service_id='{1}'\
                         and scope='outer' and attr_name like '%{2}%';".format(self.service.tenant_id, self.service.service_id,
                                                                               env_name))
                env_count = cursor.fetchall()

                total = env_count[0][0]
                start = (page - 1) * page_size
                remaining_num = total - (page - 1) * page_size
                end = page_size
                if remaining_num < page_size:
                    end = remaining_num

                cursor = connection.cursor()
                cursor.execute("select ID, tenant_id, service_id, container_port, name, attr_name, attr_value, is_change, \
                        scope, create_time from tenant_service_env_var where tenant_id='{0}' and service_id='{1}'\
                             and scope='outer' and attr_name like '%{2}%' order by attr_name LIMIT {3},{4};".format(
                    self.service.tenant_id, self.service.service_id, env_name, start, end))
                env_tuples = cursor.fetchall()
            else:

                cursor = connection.cursor()
                cursor.execute("select count(*) from tenant_service_env_var where tenant_id='{0}' and service_id='{1}' \
                        and scope='outer';".format(self.service.tenant_id, self.service.service_id))
                env_count = cursor.fetchall()

                total = env_count[0][0]
                start = (page - 1) * page_size
                remaining_num = total - (page - 1) * page_size
                end = page_size
                if remaining_num < page_size:
                    end = remaining_num

                cursor = connection.cursor()
                cursor.execute("select ID, tenant_id, service_id, container_port, name, attr_name, attr_value, is_change,\
                         scope, create_time from tenant_service_env_var where tenant_id='{0}' and service_id='{1}'\
                              and scope='outer' order by attr_name LIMIT {2},{3};".format(
                    self.service.tenant_id, self.service.service_id, start, end))
                env_tuples = cursor.fetchall()
            if len(env_tuples) > 0:
                for env_tuple in env_tuples:
                    env_dict = dict()
                    env_dict["ID"] = env_tuple[0]
                    env_dict["tenant_id"] = env_tuple[1]
                    env_dict["service_id"] = env_tuple[2]
                    env_dict["container_port"] = env_tuple[3]
                    env_dict["name"] = env_tuple[4]
                    env_dict["attr_name"] = env_tuple[5]
                    env_dict["attr_value"] = env_tuple[6]
                    env_dict["is_change"] = env_tuple[7]
                    env_dict["scope"] = env_tuple[8]
                    env_dict["create_time"] = env_tuple[9]
                    env_list.append(env_dict)
            bean = {"total": total}

        result = general_message(200, "success", "查询成功", bean=bean, list=env_list)
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        为组件添加环境变量
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
        name = request.data.get("name", "")
        attr_name = request.data.get("attr_name", "")
        attr_value = request.data.get("attr_value", "")
        scope = request.data.get('scope', "")
        is_change = request.data.get('is_change', True)
        # try:
        if not scope or not attr_name:
            return Response(general_message(400, "params error", "参数异常"), status=400)
        if scope not in ("inner", "outer"):
            return Response(general_message(400, "params error", "scope范围只能是inner或outer"), status=400)
        code, msg, data = env_var_service.add_service_env_var(self.tenant, self.service, 0, name, attr_name, attr_value,
                                                              is_change, scope, self.user.nick_name)
        if code != 200:
            result = general_message(code, "add env error", msg)
            return Response(result, status=code)
        result = general_message(code, msg, "环境变量添加成功", bean=data.to_dict())
        return Response(result, status=result["code"])


class AppEnvManageView(AppBaseView):
    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        删除组件的某个环境变量
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
            - name: attr_name
              description: 环境变量名称 大写
              required: true
              type: string
              paramType: path

        """
        env_id = kwargs.get("env_id", None)
        if not env_id:
            return Response(general_message(400, "env_id not specify", "环境变量ID未指定"))
        env_var_service.delete_env_by_env_id(self.tenant, self.service, env_id, self.user.nick_name)
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])

    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件的某个环境变量详情
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
            - name: attr_name
              description: 环境变量名称 大写
              required: true
              type: string
              paramType: path

        """
        attr_name = kwargs.get("attr_name", None)
        if not attr_name:
            return Response(general_message(400, "attr_name not specify", "环境变量名未指定"))
        env = env_var_service.get_env_by_attr_name(self.tenant, self.service, attr_name)

        result = general_message(200, "success", "查询成功", bean=model_to_dict(env))
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, *args, **kwargs):
        """
        修改组件环境变量
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
            - name: env_id
              description: 环境变量ID
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
        env_id = kwargs.get("env_id", None)
        if not env_id:
            return Response(general_message(400, "env_id not specify", "环境变量ID未指定"))
        name = request.data.get("name", "")
        attr_value = request.data.get("attr_value", "")

        code, msg, env = env_var_service.update_env_by_env_id(self.tenant, self.service, env_id, name, attr_value,
                                                              self.user.nick_name)
        if code != 200:
            raise AbortRequest(msg="update value error", msg_show=msg, status_code=code)
        result = general_message(200, "success", "更新成功", bean=model_to_dict(env))
        return Response(result, status=result["code"])

    @never_cache
    def patch(self, request, env_id, *args, **kwargs):
        """变更环境变量范围"""
        scope = parse_item(request, 'scope', required=True, error="scope is is a required parameter")
        env = env_var_service.patch_env_scope(self.tenant, self.service, env_id, scope, self.user.nick_name)
        if env:
            return MessageResponse(msg="success", msg_show="更新成功", bean=env.to_dict())
        else:
            return MessageResponse(msg="success", msg_show="更新成功", bean={})


class AppBuildEnvView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取构建组件的环境变量参数
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
            - name: env_type
              description: 环境变量类型[构建运行时环境变量（build)]
              required: true
              type: string
              paramType: query
        """
        # 获取组件构建时环境变量
        build_env_dict = dict()
        build_envs = env_var_service.get_service_build_envs(self.service)
        if build_envs:
            for build_env in build_envs:
                build_env_dict[build_env.attr_name] = build_env.attr_value
        result = general_message(200, "success", "查询成功", bean=build_env_dict)
        return Response(result, status=result["code"])

    # 全量更新，build_env_dict必须为包含环境变量
    def put(self, request, *args, **kwargs):
        """
        修改构建运行时环境变量
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        build_env_dict = request.data.get("build_env_dict", None)
        build_envs = env_var_service.get_service_build_envs(self.service)
        # 传入为空，清除
        if not build_env_dict:
            for build_env in build_envs:
                build_env.delete()
            return Response(general_message(200, "success", "设置成功"))

        # 传入有值，清空再添加
        if build_envs:
            for build_env in build_envs:
                build_env.delete()
        for key, value in list(build_env_dict.items()):
            name = "构建运行时环境变量"
            attr_name = key
            attr_value = value
            is_change = True
            code, msg, data = env_var_service.add_service_build_env_var(self.tenant, self.service, 0, name, attr_name,
                                                                        attr_value, is_change)
            if code != 200:
                continue
        compile_env = compile_env_repo.get_service_compile_env(self.service.service_id)
        compile_env.user_dependency = json.dumps(build_env_dict)
        compile_env.save()
        result = general_message(200, "success", "环境变量添加成功")
        return Response(result, status=result["code"])
