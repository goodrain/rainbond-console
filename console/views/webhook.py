# -*- coding: utf-8 -*-
import logging
import hmac
import json
import socket
from hashlib import sha1
from console.views.base import AlowAnyApiView
from rest_framework.response import Response
from console.views.app_config.base import AppBaseView
from www.models.main import Tenants, TenantServiceInfo, Users
from console.services.app import app_service
from console.services.app_actions import app_manage_service
from console.services.app_actions import event_service
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")


class WebHooksDeploy(AlowAnyApiView):

    def post(self, request, service_id, *args, **kwargs):
        try:
            print service_id
            service_obj = TenantServiceInfo.objects.get(service_id=service_id)
            tenant_obj = Tenants.objects.get(tenant_id=service_obj.tenant_id)
            if not service_obj.open_webhooks:
                print "bbbb"
                logger.debug("没开启webhooks自动部署")
                result = general_message(400, "failed", "没有开启此功能")
                return Response(result, status=400)

            github_event = request.META.get("HTTP_X_GITHUB_EVENT", None)
            user_agent = request.META.get("HTTP_USER_AGENT", None)
            if user_agent:
                user_agent = user_agent.split("/")[0]
            print github_event, user_agent

            if github_event and user_agent == "GitHub-Hookshot":
                # github
                print "进到github"
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
                if not "@automatic_deployment@" in message:
                    logger.debug("提交信息无效")
                    result = general_message(400, "failed", "提交信息无效")
                    return Response(result, status=400)

                signature = request.META.get("HTTP_X_HUB_SIGNATURE", None)
                token = None
                if signature:
                    token = signature.split("=")[1]
                    print "token", token

                payload = json.dumps(request.data)
                secret = service_obj.secret
                hmac_obj = hmac.new(str(secret), msg=payload, digestmod=sha1)
                my_token = hmac_obj.hexdigest()
                logger.debug("token", token)
                logger.debug("token2", my_token)

                print ("token", token, my_token)
                if hmac.compare_digest(token, my_token):
                    logger.debug("yes")
                    print "yes"
                else:
                    logger.debug("no")
                    print "no"

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
                print "vvvv", status_map
                status = status_map.get("status", None)
                logger.debug(status)

                user_obj = Users.objects.get(user_id=service_obj.creater)
                committer_name = commits_info.get("committer").get("username")
                if status:
                    code, msg, event = app_manage_service.deploy(tenant_obj, service_obj, user_obj, committer_name)
                    bean = {}
                    if event:
                        bean = event.to_dict()
                        bean["type_cn"] = event_service.translate_event_type(event.type)
                    if code != 200:
                        return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
                    result = general_message(code, "success", "操作成功", bean=bean)
                    return Response(result, status=200)
            # gitlab
            gitlab_event = request.META.get("HTTP_X_GITLAB_EVENT", None)
            if gitlab_event:

                commits_info = request.data.get("commits")
                if not commits_info:
                    logger.debug("提交信息获取失败")
                    result = general_message(400, "failed", "提交信息获取失败")
                    return Response(result, status=400)
                message = commits_info[-1].get("message")
                if not "@automatic_deployment@" in message:
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

                url = repository["url"]
                git_http_url = repository.get("git_http_url")
                git_ssh_url = repository.get("git_ssh_url")

                logger.debug("ooo", service_obj.git_url)
                logger.debug("ooox", git_ssh_url)

                if not (service_obj.git_url == git_http_url or service_obj.git_url == git_ssh_url):
                    logger.debug("github地址不相符")
                    result = general_message(400, "failed", "仓库地址不相符")
                    return Response(result, status=400)

                logger.debug("yessssssss")
                # 获取应用状态
                status_map = app_service.get_service_status(tenant_obj, service_obj)
                print "vvvv", status_map
                status = status_map.get("status", None)
                user = Users.objects.get(service_obj.creater)
                committer_name = commits_info.get("author").get("name")
                if status:
                    logger.debug(status, "status")
                    logger.debug("mmmmmmmmm")
                    code, msg, event = app_manage_service.deploy(tenant_obj, service_obj, user, committer_name)
                    bean = {}
                    if event:
                        bean = event.to_dict()
                        bean["type_cn"] = event_service.translate_event_type(event.type)
                    if code != 200:
                        return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
                    result = general_message(code, "success", "操作成功", bean=bean)
                    return Response(result, status=200)
            else:
                logger.debug("暂时仅支持github与gitlab的webhooks")
                result = general_message(400, "failed", "暂时仅支持github与gitlab的webhooks")
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
            return Response(e.message, status=400)

    def get(self, request, *args, **kwargs):
        return Response("ok")


class GetWebHooksUrl(AppBaseView):
    def get(self, request, *args, **kwargs):
        try:
            tenant_id = self.tenant.tenant_id
            service_alias = self.service.service_alias
            service_obj = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias)[0]
            service_code_from = service_obj.code_from == "github" or service_obj.code_from == "gitlab_new" or service_obj.code_from == "gitlab_exit"
            if not (service_obj.service_source == "source_code" and service_code_from):
                result = general_message(400, "failed", "该应用不符合要求")
                return Response(result, status=400)
            hostname = socket.gethostname()
            logger.debug(hostname)
            print hostname

            url = "http://" + "127.0.0.1:9000/" + "console/" + "webhooks/" + service_obj.service_id
            result = general_message(200, "success", "获取webhooks-URl成功", list=[url])
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=400)

# {"status": "closed", "disabledAction": ["visit", "stop", "manage_container", "reboot"],
#  "status_cn": "已关闭", "activeAction": ["restart", "deploy"]}
