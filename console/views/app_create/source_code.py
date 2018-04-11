# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import ResourceNotEnoughException
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
import logging
from www.utils.return_message import general_message, error_message
from console.services.app import app_service
from console.services.app_config import port_service, compile_env_service
from console.services.group_service import group_service
from console.views.app_config.base import AppBaseView
import json

logger = logging.getLogger("default")


class SourceCodeCreateView(RegionTenantHeaderView):
    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        """
        源码创建应用
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
              paramType: form
            - name: code_from
              description: 应用代码来源
              required: true
              type: string
              paramType: form
            - name: service_cname
              description: 应用名称
              required: true
              type: string
              paramType: form
            - name: git_url
              description: git地址
              required: false
              type: string
              paramType: form
            - name: git_project_id
              description: 代码ID
              required: false
              type: string
              paramType: form
            - name: code_version
              description: 代码版本
              required: false
              type: string
              paramType: form
            - name: username
              description: 私有云用户名称
              required: false
              type: string
              paramType: form
            - name: password
              description: 私有云账户密码
              required: false
              type: string
              paramType: form

        """

        group_id = request.data.get("group_id", -1)
        service_code_from = request.data.get("code_from", None)
        service_cname = request.data.get("service_cname", None)
        service_code_clone_url = request.data.get("git_url", None)
        git_password = request.data.get("password", None)
        git_user_name = request.data.get("username", None)
        service_code_id = request.data.get("git_project_id", None)
        service_code_version = request.data.get("code_version", "master")
        result = {}
        try:
            if not service_code_clone_url:
                return Response(general_message(400, "code url is null", "仓库地址未指明"), status=400)
            if not service_code_from:
                return Response(general_message(400, "params error", "参数service_code_from未指明"), status=400)
            # 创建源码应用
            if service_code_clone_url:
                service_code_clone_url = service_code_clone_url.strip()
            code, msg_show, new_service = app_service.create_source_code_app(self.response_region, self.tenant,
                                                                             self.user, service_code_from,
                                                                             service_cname, service_code_clone_url,
                                                                             service_code_id,
                                                                             service_code_version)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)
            # 添加username,password信息
            if git_password or git_user_name:
                app_service.create_service_source_info(self.tenant, new_service, git_user_name, git_password)

            # 添加服务所在组
            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id,
                                                                new_service.service_id)
            if code != 200:
                logger.debug("service.create", msg_show)
            result = general_message(200, "success", "创建成功", bean=new_service.to_dict())
        except ResourceNotEnoughException as re:
            logger.exception(re)
            return Response(general_message(10406, "resource is not enough", re.message), status=412)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppCompileEnvView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务运行环境信息
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
            compile_env = compile_env_service.get_service_compile_env(self.service)
            bean = dict()

            if compile_env:
                check_dependency = json.loads(compile_env.check_dependency)
                user_dependency = {}
                if compile_env.user_dependency:
                    user_dependency = json.loads(compile_env.user_dependency)
                bean["check_dependency"] = check_dependency
                bean["user_dependency"] = user_dependency
                bean["service_id"] = compile_env.service_id
            result = general_message(200, "success", "查询编译环境成功",bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('create_service')
    def put(self, request, *args, **kwargs):
        """
        修改应用运行环境信息
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
            - name: service_runtimes
              description: 服务运行版本，如php5.5等
              required: false
              type: string
              paramType: form
            - name: service_server
              description: 服务使用的服务器，如tomcat,apache,nginx等
              required: false
              type: string
              paramType: form
            - name: service_dependency
              description: 服务依赖，如php-mysql扩展等
              required: false
              type: string
              paramType: form

        """
        try:
            service_runtimes = request.data.get("service_runtimes", "")
            service_server = request.data.get("service_server", "")
            service_dependency = request.data.get("service_dependency", "")
            checkJson = {}
            checkJson["language"] = self.service.language
            checkJson["runtimes"] = service_runtimes
            checkJson["procfile"] = service_server
            if service_dependency != "":
                dps = service_dependency.split(",")
                d = {}
                for dp in dps:
                    if dp is not None and dp != "":
                        d["ext-" + dp] = "*"
                checkJson["dependencies"] = d
            else:
                checkJson["dependencies"] = {}
            update_params = {
                "user_dependency": json.dumps(checkJson)
            }
            compile_env = compile_env_service.update_service_compile_env(self.service,**update_params)
            bean = dict()
            if compile_env:
                check_dependency = json.loads(compile_env.check_dependency)
                user_dependency = {}
                if compile_env.user_dependency:
                    user_dependency = json.loads(compile_env.user_dependency)
                bean["check_dependency"] = check_dependency
                bean["user_dependency"] = user_dependency
                bean["service_id"] = compile_env.service_id

            result = general_message(200,"success", "操作成功",bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])