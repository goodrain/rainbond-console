# -*- coding: utf-8 -*-
import base64
import logging
import pickle
import random
import socket
import string

from console.models import DeployRelation
from console.repositories.deploy_repo import deploy_repo
from console.services.team_services import team_services
from console.views.base import AlowAnyApiView, JWTAuthApiView
from rest_framework.response import Response
from console.views.app_config.base import AppBaseView
from www.models.main import Tenants, TenantServiceInfo, Users
from console.services.app import app_service
from www.utils.return_message import general_message, error_message
from console.services.user_services import user_services
from www.decorator import perm_required

logger = logging.getLogger("default")


class WebHooksDeploy(AlowAnyApiView):

    def post(self, request, service_id, *args, **kwargs):
        """
        github，gitlab 回调接口 触发自动部署

        """
        try:

            service_obj = TenantServiceInfo.objects.get(service_id=service_id)
            tenant_obj = Tenants.objects.get(tenant_id=service_obj.tenant_id)
            if not service_obj.open_webhooks:
                logger.debug("没开启webhooks自动部署")
                result = general_message(400, "failed", "没有开启此功能")
                return Response(result, status=400)
            # github
            github_event = request.META.get("HTTP_X_GITHUB_EVENT", None)
            user_agent = request.META.get("HTTP_USER_AGENT", None)
            if user_agent:
                user_agent = user_agent.split("/")[0]
            if github_event and user_agent == "GitHub-Hookshot":

                if not github_event == "push":
                    logger.debug("不支持此事件类型")
                    result = general_message(400, "failed", "不支持此事件类型")
                    return Response(result, status=400)

                commits_info = request.data.get("head_commit")
                if not commits_info:
                    logger.debug("提交信息获取失败")
                    result = general_message(400, "failed", "提交信息获取失败")
                    return Response(result, status=400)
                message = commits_info.get("message")
                if "@deploy" not in message:
                    logger.debug("提交信息无效")
                    result = general_message(400, "failed", "提交信息无效")
                    return Response(result, status=400)

                # signature = request.META.get("HTTP_X_HUB_SIGNATURE", None)

                ref = request.data.get("ref")
                if not ref:
                    logger.debug("获取分支信息失败")
                    result = general_message(400, "failed", "获取分支信息失败")
                    return Response(result, status=400)
                ref = ref.split("/")[2]
                if not service_obj.code_version == ref:
                    logger.debug("当前分支与部署分支不同")
                    result = general_message(400, "failed", "提交分支与部署分支不同")
                    return Response(result, status=400)

                repository = request.data.get("repository")
                if not repository:
                    logger.debug("却少repository信息")
                    result = general_message(400, "failed", "却少repository信息")
                    return Response(result, status=400)
                clone_url = repository.get("clone_url")
                ssh_url = repository.get("ssh_url")
                logger.debug("git_url", service_obj.git_url)
                logger.debug("clone_url", clone_url)
                logger.debug("ssh_url", ssh_url)
                if not (service_obj.git_url == clone_url or service_obj.git_url == ssh_url):
                    logger.debug("github地址不相符")
                    result = general_message(400, "failed", "仓库地址不相符")
                    return Response(result, status=400)

                # 获取应用状态
                status_map = app_service.get_service_status(tenant_obj, service_obj)
                status = status_map.get("status", None)
                logger.debug(status)

                user_obj = Users.objects.get(user_id=service_obj.creater)
                committer_name = commits_info.get("author").get("username")
                if status == "running" or status == "abnormal":
                    return user_services.deploy_service(tenant_obj=tenant_obj, service_obj=service_obj, user=user_obj,
                                                        committer_name=committer_name)
                else:
                    logger.debug("应用状态异常")
                    result = general_message(400, "failed", "应用状态不支持")
                    return Response(result, status=400)
            # gitlab
            elif request.META.get("HTTP_X_GITLAB_EVENT", None):

                logger.debug(request.data)

                commits_info = request.data.get("commits")
                if not commits_info:
                    logger.debug("提交信息获取失败")
                    result = general_message(400, "failed", "提交信息获取失败")
                    return Response(result, status=400)
                message = commits_info[-1].get("message")
                if "@deploy" not in message:
                    logger.debug("提交信息无效")
                    result = general_message(400, "failed", "提交信息无效")
                    return Response(result, status=400)

                event_name = request.data.get("object_kind", None)
                logger.debug("kind", event_name)
                if not event_name == "push":
                    logger.debug("不支持此事件类型")
                    result = general_message(400, "failed", "不支持此事件类型")
                    return Response(result, status=400)

                ref = request.data.get("ref")
                if not ref:
                    logger.debug("获取分支信息失败")
                    result = general_message(400, "failed", "获取分支信息失败")
                    return Response(result, status=400)
                ref = ref.split("/")[2]
                if not service_obj.code_version == ref:
                    logger.debug("当前分支与部署分支不同")
                    result = general_message(400, "failed", "提交分支与部署分支不同")
                    return Response(result, status=400)

                repository = request.data.get("repository")
                if not repository:
                    logger.debug("却少repository信息")
                    result = general_message(400, "failed", "却少repository信息")
                    return Response(result, status=400)

                git_http_url = repository.get("git_http_url")
                gitlab_ssh_url = repository.get("git_ssh_url")
                git_ssh_url = gitlab_ssh_url.split("//", 1)[-1]

                logger.debug("service_url", service_obj.git_url)
                logger.debug("git_ssh_url", git_ssh_url)
                logger.debug("http_url", git_http_url)

                if not (service_obj.git_url == git_http_url or service_obj.git_url == git_ssh_url):
                    logger.debug("github地址不相符")
                    result = general_message(400, "failed", "仓库地址不相符")
                    return Response(result, status=400)

                # 获取应用状态
                status_map = app_service.get_service_status(tenant_obj, service_obj)
                status = status_map.get("status", None)
                user = Users.objects.get(user_id=service_obj.creater)
                committer_name = commits_info[-1].get("author").get("name")
                logger.debug("status", status_map)
                if status == "running" or status == "abnormal":
                    return user_services.deploy_service(tenant_obj=tenant_obj, service_obj=service_obj, user=user,
                                                        committer_name=committer_name)
                else:
                    logger.debug("应用状态异常")
                    result = general_message(400, "failed", "应用状态不支持")
                    return Response(result, status=400)
            # gitee
            elif request.META.get("HTTP_X_GITEE_EVENT", None) or request.META.get("HTTP_X_GIT_OSCHINA_EVENT", None):
                logger.debug(request.data)

                commits_info = request.data.get("head_commit")
                if not commits_info:
                    logger.debug("提交信息获取失败")
                    result = general_message(400, "failed", "提交信息获取失败")
                    return Response(result, status=400)
                message = commits_info.get("message")
                if "@deploy" not in message:
                    logger.debug("提交信息无效")
                    result = general_message(400, "failed", "提交信息无效")
                    return Response(result, status=400)
                ref = request.data.get("ref")
                if not ref:
                    logger.debug("获取分支信息失败")
                    result = general_message(400, "failed", "获取分支信息失败")
                    return Response(result, status=400)
                ref = ref.split("/")[2]
                if not service_obj.code_version == ref:
                    logger.debug("当前分支与部署分支不同")
                    result = general_message(400, "failed", "提交分支与部署分支不同")
                    return Response(result, status=400)

                repository = request.data.get("repository")
                if not repository:
                    logger.debug("却少repository信息")
                    result = general_message(400, "failed", "却少repository信息")
                    return Response(result, status=400)
                clone_url = repository.get("clone_url")
                ssh_url = repository.get("ssh_url")
                logger.debug("git_url", service_obj.git_url)
                logger.debug("clone_url", clone_url)
                logger.debug("ssh_url", ssh_url)
                if not (service_obj.git_url == clone_url or service_obj.git_url == ssh_url):
                    logger.debug("gitee地址不相符")
                    result = general_message(400, "failed", "仓库地址不相符")
                    return Response(result, status=400)

                # 获取应用状态
                status_map = app_service.get_service_status(tenant_obj, service_obj)
                status = status_map.get("status", None)
                logger.debug(status)

                user_obj = Users.objects.get(user_id=service_obj.creater)
                committer_name = commits_info.get("author").get("username")
                if status == "running" or status == "abnormal":
                    return user_services.deploy_service(tenant_obj=tenant_obj, service_obj=service_obj,
                                                        user=user_obj,
                                                        committer_name=committer_name)
                else:
                    logger.debug("应用状态异常")
                    result = general_message(400, "failed", "应用状态不支持")
                    return Response(result, status=400)
            # gogs
            elif request.META.get("HTTP_X_GOGS_EVENT", None):
                logger.debug(request.data)

                commits_info = request.data.get("commits")
                if not commits_info:
                    logger.debug("提交信息获取失败")
                    result = general_message(400, "failed", "提交信息获取失败")
                    return Response(result, status=400)
                message = commits_info[0].get("message")
                if "@deploy" not in message:
                    logger.debug("提交信息无效")
                    result = general_message(400, "failed", "提交信息无效")
                    return Response(result, status=400)
                ref = request.data.get("ref")
                if not ref:
                    logger.debug("获取分支信息失败")
                    result = general_message(400, "failed", "获取分支信息失败")
                    return Response(result, status=400)
                ref = ref.split("/")[2]
                if not service_obj.code_version == ref:
                    logger.debug("当前分支与部署分支不同")
                    result = general_message(400, "failed", "提交分支与部署分支不同")
                    return Response(result, status=400)

                repository = request.data.get("repository")
                if not repository:
                    logger.debug("却少repository信息")
                    result = general_message(400, "failed", "却少repository信息")
                    return Response(result, status=400)
                clone_url = repository.get("clone_url")
                ssh_url = repository.get("ssh_url")
                logger.debug("git_url", service_obj.git_url)
                logger.debug("clone_url", clone_url)
                logger.debug("ssh_url", ssh_url)
                if not (service_obj.git_url == clone_url or service_obj.git_url == ssh_url):
                    logger.debug("gogs地址不相符")
                    result = general_message(400, "failed", "仓库地址不相符")
                    return Response(result, status=400)

                # 获取应用状态
                status_map = app_service.get_service_status(tenant_obj, service_obj)
                status = status_map.get("status", None)
                logger.debug(status)

                user_obj = Users.objects.get(user_id=service_obj.creater)
                committer_name = commits_info[0].get("author").get("username")
                if status == "running" or status == "abnormal":
                    return user_services.deploy_service(tenant_obj=tenant_obj, service_obj=service_obj,
                                                        user=user_obj,
                                                        committer_name=committer_name)
                else:
                    logger.debug("应用状态异常")
                    result = general_message(400, "failed", "应用状态不支持")
                    return Response(result, status=400)



            else:
                logger.debug("暂时仅支持github与gitlab")
                result = general_message(400, "failed", "暂时仅支持github与gitlab哦～")
                return Response(result, status=400)

        except Tenants.DoesNotExist as e:
            logger.exception(e)
            logger.error(e)
            return Response(e.message, status=400)
        except TenantServiceInfo.DoesNotExist as e:
            logger.exception(e)
            logger.error(e)
            return Response(e.message, status=400)
        except Exception as e:
            logger.exception(e)
            logger.error(e)
            return Response(e.message, status=500)


class GetWebHooksUrl(AppBaseView):
    def get(self, request, *args, **kwargs):
        """
        判断该应用是否有webhooks自动部署功能，有则返回URL
        """
        try:
            tenant_id = self.tenant.tenant_id
            service_alias = self.service.service_alias
            service_obj = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias)[0]
            code_from = service_obj.code_from
            service_code_from = code_from == "github" or code_from == "gitlab_new" or code_from == "gitlab_exit" or code_from == "gitlab_manual"
            if not (service_obj.service_source == "source_code" and service_code_from):
                result = general_message(200, "failed", "该应用不符合要求", bean={"display":False})
                return Response(result, status=200)
            host = request.get_host()
            url = "https://" + host + "/console/" + "webhooks/" + service_obj.service_id

            service_id = service_obj.service_id
            custom_url = "https://" + host + "/console/" + "/custom/deploy/" + service_obj.service_id
            deploy = deploy_repo.get_deploy_relation_by_service_id(service_id=service_id)
            # deploy_key = deploy.secret_key
            print deploy
            secret_key = pickle.loads(base64.b64decode(deploy)).get("secret_key")
            status = self.service.open_webhooks
            result = general_message(200, "success", "获取URl及开启状态成功", bean={"url": url, "custom_url":custom_url, "secret_key":secret_key, "status": status, "display":True})

            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=500)


class WebHooksStatus(AppBaseView):
    @perm_required("manage_service_config")
    def post(self, request, *args, **kwargs):
        """
        开启或关闭自动部署功能
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
            - name: action
              description: 操作 打开:open 关闭:close
              required: true
              type: string 格式：{"action":"open"}
              paramType: body

        """
        try:
            action = request.data.get("action", None)
            if not action:
                result = general_message(400, "Parameter cannot be empty", "却少参数")
                return Response(result, status=400)
            if action != "open" and action != "close":
                result = general_message(400, "action error", "操作类型不存在")
                return Response(result, status=400)
            if action == "open":
                self.service.open_webhooks = True
                self.service.save()
                result = general_message(200, "success", "开启成功")
            else:
                self.service.open_webhooks = False
                self.service.save()
                result = general_message(200, "success", "关闭成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)
        return Response(result, status=200)


class CustomWebHooksDeploy(AlowAnyApiView):


    def post(self, request, service_id, *args, **kwargs):
        """自定义回调接口出发自动部署"""
        logger.debug(request.data)
        import pickle , base64
        secret_key = request.data.get("secret_key")
        # 加密
        pwd = base64.b64encode(pickle.dumps({"secret_key": secret_key}))
        deploy = DeployRelation.objects.filter(secret_key=pwd)
        deploy_key = deploy[0].secret_key
        deploy_key_decode = pickle.loads(base64.b64decode(deploy_key)).get("secret_key")
        # base64.b64encode(pickle.dumps({"secret_key": "zhufeng"}))
        if not deploy and secret_key != deploy_key_decode:
            result = general_message(400, "failed", "密钥错误")
            return Response(result, status=400)
        service_obj = TenantServiceInfo.objects.get(service_id=service_id)
        tenant_obj = Tenants.objects.get(tenant_id=service_obj.tenant_id)
        status_map = app_service.get_service_status(tenant_obj, service_obj)
        user_obj = Users.objects.get(user_id=service_obj.creater)
        user_name = user_obj.nick_name
        status = status_map.get("status", None)
        logger.debug(status)
        if status == "running" or status == "abnormal":
            return user_services.deploy_service(tenant_obj=tenant_obj, service_obj=service_obj,
                                                user=user_obj,
                                                committer_name=user_name)
        else:
            logger.debug("应用状态异常")
            result = general_message(400, "failed", "应用状态不支持")
            return Response(result, status=400)


class UpdateSecretKey(AppBaseView):

    def put(self, request, *args, **kwargs):
        try:
            secret_key = request.data.get("secret_key", None)
            if not secret_key:
                code = 400
                result = general_message(code, "no secret_key", "请输入密钥")
                return Response(result, status=code)
            tenant_id = self.tenant.tenant_id
            service_alias = self.service.service_alias
            service_obj = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias)[0]
            deploy_obj = DeployRelation.objects.filter(service_id=service_obj.service_id)
            pwd = base64.b64encode(pickle.dumps({"secret_key": secret_key}))
            if deploy_obj:
                deploy_obj.update(secret_key=pwd)
                result = general_message(200, "success", "修改成功")
                return Response(result, 200)
            else:
                result = general_message(404, "not found", "没有该应用")
                return Response(result, 404)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=500)

