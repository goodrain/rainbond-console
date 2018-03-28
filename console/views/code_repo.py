# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""
import logging

from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.git_service import GitCodeService
from console.services.user_services import user_services
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView, JWTAuthApiView
from www.decorator import perm_required
from www.utils.return_message import error_message, general_message
from www.utils.url import get_redirect_url

logger = logging.getLogger("default")
git_service = GitCodeService()


class GithubCodeRepoView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        查询用户github代码仓库
        ---
        """
        try:
            code, msg, data = git_service.get_github_repo(self.user)
            is_auth = False
            if code == 200:
                is_auth = True
                result = general_message(code, msg, "获取数据成功", bean={"is_auth": is_auth}, list=data)
            elif code == 403:
                data.update({"is_auth": is_auth})
                result = general_message(200, "operation suspend", msg, bean=data)
            else:
                data.update({"is_auth": is_auth})
                result = general_message(code, "service error", msg, bean=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


# class GithubCallBackView():

class GithubCallBackView(JWTAuthApiView):
    def redirect_to(self, path, *args, **kwargs):
        full_url = get_redirect_url(path, request=self.request)
        return redirect(full_url, *args, **kwargs)

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        github 回调地址 由github自己调用
        ---
        parameters:
            - name: code
              description: 用户github key
              required: true
              type: string
              paramType: form
            - name: state
              description: 状态码
              required: true
              type: string
              paramType: form
        """
        code = request.data.get("code", "")
        state = request.data.get("state", "")

        logger.debug("============> code {0} state {1}".format(code, state))
        if code != "" and state != "" and int(state) == self.user.pk:
            git_service.github_callback(self.user, code)
            msg = "success"
        else:
            msg = "not success"
        result = general_message(200, msg, "操作成功")

        # return self.redirect_to("/index#/create/code/github")
        return Response(result, status=result["code"])


class GitlabCodeRepoView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        查询用户gitlab代码仓库
        ---
        """
        try:
            code, msg, data = git_service.get_gitlab_repo(self.tenant)
            result = general_message(code, msg, "获取数据成功", list=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        """
        创建gitlab代码仓库
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: project_name
              description: 要创建的代码仓库名称
              required: true
              type: string
              paramType: form
        """
        try:
            project_name = request.data.get("project_name", None)
            if not project_name:
                return Response(general_message(400, "params error", "请填写项目名称"), status=400)
            code, msg, rt_data = git_service.create_gitlab_project(self.tenant, self.user, project_name)
            if code != 200:
                return Response(general_message(code, "create gitlab code error", msg), status=code)

            result = general_message(200, "success", "创建成功", bean=rt_data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CodeBranchView(RegionTenantHeaderView):
    def post(self, request, *args, **kwargs):
        """
        查询代码分支
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: type
              description: 类型 github 或 gitlab
              required: true
              type: string
              paramType: query
            - name: service_code_clone_url
              description: git地址
              required: true
              type: string
              paramType: query
            - name: service_code_id
              description: 代码ID
              required: true
              type: string
              paramType: query

        """
        try:
            code_type = request.data.get("type", None)
            git_url = request.data.get("service_code_clone_url", None)
            git_project_id = request.data.get("service_code_id", None)
            if code_type not in ("gitlab", "github"):
                return Response(general_message(400, "params error", "代码类型错误"))

            code, msg, data = git_service.get_code_branch(self.user, code_type, git_url, git_project_id)
            if code != 200:
                return Response(general_message(code, "get branch error", msg), status=code)
            result = general_message(code, msg, "获取数据成功", list=data)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class ServiceCodeBranch(AppBaseView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用代码仓库分支
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
        result = dict()
        try:
            branches = git_service.get_service_code_branch(self.user, self.service)
            bean = {"current_version": self.service.code_version}
            result = general_message(200, "success", "查询成功", bean=bean, list=branches)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @perm_required('deploy_service')
    def put(self, request, *args, **kwargs):
        """
        修改应用代码仓库分支
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
            - name: branch
              description: 代码分支
              required: true
              type: string
              paramType: form
        """
        try:
            branch = request.data.get('branch', None)
            if not branch:
                return Response(general_message(400, "params error", "请指定具体分支"), status=400)
            self.service.code_version = branch
            self.service.save(update_fields=['code_version'])
            result = general_message(200, "success", "代码仓库分支修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class GitLabUserRegisterView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        """
        gitlab上创建账号
        ---
        parameters:
            - name: email
              description: 邮箱账户
              required: true
              type: string
              paramType: form
            - name: password
              description: 云帮登录密码
              required: true
              type: string
              paramType: form

        """
        try:
            email = request.data.get("email", None)
            password = request.data.get("password", None)
            if not email or not password:
                return Response(general_message(400, "params error", "请填写必要参数"), status=400)
            if self.user.git_user_id > 0:
                return Response(general_message(409, "alread register gitlab", "您已注册gitlab账户，请勿重复注册"), status=409)
            if self.user.email:
                if email != self.user.email:
                    return Response(general_message(409, "email conflict", "用户已存在邮箱{0},请使用该邮箱".format(self.user.email)),
                                    status=409)
            else:
                u = user_services.get_user_by_email(email)
                if u:
                    return Response(general_message(409, "email conflict", "该邮箱已存在"),
                                    status=409)
            if not self.user.check_password(password):
                return Response(general_message(401, "password error", "密码错误"), status=401)

            code, msg, git_info = git_service.create_git_lab_user(self.user, email, password)
            if code != 200:
                return Response(general_message(code, "create gitlab account error", msg), status=code)

            result = general_message(200, "success", "创建成功", bean=git_info)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
