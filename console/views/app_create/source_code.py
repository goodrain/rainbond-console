# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import json
import os
from re import split as re_split
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.main import ResourceNotEnoughException, AccountOverdueException
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.app import app_service
from console.services.app_config import compile_env_service
from console.services.group_service import group_service
from console.services.oauth_service import GitApi
from console.repositories.oauth_repo import oauth_repo
from console.repositories.oauth_repo import oauth_user_repo
from console.repositories.app import service_webhooks_repo
from console.views.app_config.base import AppBaseView


logger = logging.getLogger("default")


class SourceCodeCreateView(RegionTenantHeaderView):
    @never_cache
    @perm_required('create_service')
    def post(self, request, *args, **kwargs):
        """
        源码创建组件
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
              description: 组件代码来源
              required: true
              type: string
              paramType: form
            - name: service_cname
              description: 组件名称
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
            - name: server_type
              description: 仓库类型git或svn
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
        is_oauth = request.data.get("is_oauth", False)
        check_uuid = request.data.get("check_uuid")
        event_id = request.data.get("event_id")
        server_type = request.data.get("server_type", "git")
        user_id = request.user.user_id

        git_service = None
        full_name = None
        open_webhook = False
        host = os.environ.get('DEFAULT_DOMAIN', request.get_host())

        result = {}
        if is_oauth:
            service_id = request.data.get("service_id")
            full_name = request.data.get("full_name")
            open_webhook = request.data.get("open_webhook", False)
            oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=service_id)
            oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=service_id, user_id=user_id)
            git_service = GitApi(oauth_service=oauth_service, oauth_user=oauth_user)
            access_token = oauth_user.access_token
            urls = service_code_clone_url.split("//")
            service_code_from = "oauth_"+oauth_service.oauth_type

            if oauth_service.oauth_type == "github" or oauth_service.oauth_type == "gitee":
                service_code_clone_url = urls[0]+'//'+oauth_user.oauth_user_name\
                                         +':'+access_token+'@'+urls[-1]
            elif oauth_service.oauth_type == "gitlab":
                service_code_clone_url = urls[0]+'//oauth2:'+access_token+'@'+urls[-1]
            else:
                service_code_clone_url = None

        try:
            if not service_code_clone_url:
                return Response(general_message(400, "code url is null", "仓库地址未指明"), status=400)
            if not service_code_from:
                return Response(general_message(400, "params error", "参数service_code_from未指明"), status=400)
            if not server_type:
                return Response(general_message(400, "params error", "仓库类型未指明"), status=400)
            # 创建源码组件
            if service_code_clone_url:
                service_code_clone_url = service_code_clone_url.strip()
            code, msg_show, new_service = app_service.create_source_code_app(
                self.response_region, self.tenant, self.user, service_code_from, service_cname, service_code_clone_url,
                service_code_id, service_code_version, server_type, check_uuid, event_id)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)
            # 添加username,password信息
            if git_password or git_user_name:
                app_service.create_service_source_info(self.tenant, new_service, git_user_name, git_password)

            # 自动添加hook
            if open_webhook and is_oauth and not new_service.open_webhooks:
                service_webhook = service_webhooks_repo.create_service_webhooks(new_service.service_id, "code_Webhooks")
                service_webhook.state=True
                service_webhook.deploy_keyword="deploy"
                service_webhook.save()
                git_service.api.creat_hooks(host=host, full_name_or_id=full_name, endpoint='console/webhooks/'+ new_service.service_id)
                new_service.open_webhooks = True
                new_service.save()
            # 添加组件所在组

            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id,
                                                                new_service.service_id)

            if code != 200:
                logger.debug("service.create", msg_show)
            bean = new_service.to_dict()
            if is_oauth:
                result_url = re_split("[:,@]", bean["git_url"])

                bean["git_url"] = result_url[0]+'//'+result_url[-1]
            result = general_message(200, "success", "创建成功", bean=bean)
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppCompileEnvView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取组件运行环境信息
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

        """
        try:
            compile_env = compile_env_service.get_service_compile_env(self.service)
            bean = dict()
            selected_dependency = []
            if compile_env:
                check_dependency = json.loads(compile_env.check_dependency)
                user_dependency = {}
                if compile_env.user_dependency:
                    user_dependency = json.loads(compile_env.user_dependency)
                    selected_dependency = [key.replace("ext-", "") for key in user_dependency.get("dependencies", {}).keys()]
                bean["check_dependency"] = check_dependency
                bean["user_dependency"] = user_dependency
                bean["service_id"] = compile_env.service_id
                bean["selected_dependency"] = selected_dependency
            result = general_message(200, "success", "查询编译环境成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('create_service')
    def put(self, request, *args, **kwargs):
        """
        修改组件运行环境信息
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
            - name: service_runtimes
              description: 组件运行版本，如php5.5等
              required: false
              type: string
              paramType: form
            - name: service_server
              description: 组件使用的服务器，如tomcat,apache,nginx等
              required: false
              type: string
              paramType: form
            - name: service_dependency
              description: 组件依赖，如php-mysql扩展等
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
            update_params = {"user_dependency": json.dumps(checkJson)}
            compile_env = compile_env_service.update_service_compile_env(self.service, **update_params)
            bean = dict()
            if compile_env:
                check_dependency = json.loads(compile_env.check_dependency)
                user_dependency = {}
                if compile_env.user_dependency:
                    user_dependency = json.loads(compile_env.user_dependency)
                bean["check_dependency"] = check_dependency
                bean["user_dependency"] = user_dependency
                bean["service_id"] = compile_env.service_id

            result = general_message(200, "success", "操作成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
