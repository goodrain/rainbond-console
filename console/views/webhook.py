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


class WebHooks(AlowAnyApiView):

    def post(self, request, team_name, app_name, username, *args, **kwargs):
        try:
            tenant = Tenants.objects.get(tenant_name=team_name)

            service = TenantServiceInfo.objects.get(service_alias=app_name, tenant_id=tenant.tenant_id)
            event = request.META.get("HTTP_X_GITHUB_EVENT", None)
            user_agent = request.META.get("HTTP_USER_AGENT", None)
            if user_agent:
                user_agent2 = user_agent.split("/")[0]
            else:
                user_agent2 = None
            if event == "push" and user_agent2 == "GitHub-Hookshot":
                # github
                signature = request.META.get("HTTP_X_HUB_SIGNATURE", None)
                token = None
                if signature:
                    token = signature.split("=")[1]
                    print "token", token

                payload = json.dumps(request.data)
                hmac_obj = hmac.new(str("zhoujunhao"), str(payload), digestmod=sha1)
                token_2 = hmac_obj.hexdigest()
                logger.debug("token", token, token_2)
                print ("token", token, token_2)
                if hmac.compare_digest(str(token), str(token_2)):
                    logger.debug("yes")
                    print "yes"
                else:
                    logger.debug("no")
                    print "no"

                ref = request.data.get("ref")
                ref = ref.split("/")[2]
                if not service.code_version == ref:
                    logger.debug("---当前分支与部署分支不同")
                    result = general_message(400, "failed", "当前分支与部署分支不同")
                    return Response(result, status=400)

                git_url = request.data.get("repository")["clone_url"]
                ssh_url = request.data.get("repository")["ssh_url"]
                logger.debug("git_url", service.git_url)
                logger.debug("clone_url", git_url)
                logger.debug("ssh_url", ssh_url)
                if not (service.git_url == git_url or service.git_url == ssh_url):
                    logger.debug("github地址错误")
                    result = general_message(400, "failed", "URl错误")
                    return Response(result, status=400)

                # 获取应用状态
                status_map = app_service.get_service_status(tenant, service)
                print "vvvv", status_map
                status = status_map.get("status", None)
                print "status", status
                user = Users.objects.get(nick_name=username)

                if status:
                    logger.debug(status, "xxxx")
                    code, msg, event = app_manage_service.deploy(tenant, service, user)
                    bean = {}
                    if event:
                        bean = event.to_dict()
                        bean["type_cn"] = event_service.translate_event_type(event.type)
                    if code != 200:
                        return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
                    result = general_message(code, "success", "操作成功", bean=bean)
                    return Response(result, status=200)

            if request.META.get("HTTP_X_GITLAB_EVENT", None):

                event_name = request.data.get("object_kind", None)
                logger.debug("kind", event_name)
                if not event_name == "push":
                    return Response("事件类型不符", status=400)

                ref = request.data.get("ref", None)
                if not ref:
                    return Response("却少参数", status=400)
                logger.debug("yesref", ref.split("/")[2])
                branch = ref.split("/")[2]
                if not service.code_version == branch:
                    return Response("版本不符", status=400)

                repository = request.data.get("repository")
                if not repository:
                    logger.debug("越少参数1llll")
                    return Response("却少参数", status=400)
                url = repository["url"]
                git_http_url = repository["git_http_url"]
                git_ssh_url = repository["git_ssh_url"]
                id = request.data.get("project_id", None)
                logger.debug("ooo", service.git_url)
                logger.debug("ooox", git_ssh_url)
                logger.debug("eee", service.git_url == git_ssh_url)

                if not (service.git_url == git_http_url or service.git_url == git_ssh_url):
                    logger.debug("仓库地主不相符，fff")

                    return Response("仓库地主不相符", status=400)

                logger.debug("yessssssss")
                # 获取应用状态
                status_map = app_service.get_service_status(tenant, service)
                print "vvvv", status_map
                status = status_map.get("status", None)
                print "status", status
                user = Users.objects.get(nick_name=username)

                if status:
                    logger.debug(status, "status")
                    logger.debug("mmmmmmmmm")
                    code, msg, event = app_manage_service.deploy(tenant, service, user)
                    bean = {}
                    if event:
                        bean = event.to_dict()
                        bean["type_cn"] = event_service.translate_event_type(event.type)
                    if code != 200:
                        return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
                    result = general_message(code, "success", "操作成功", bean=bean)
                    return Response(result, status=200)

        except Exception as e:
            logger.exception(e)
            logger.error(e)
            return Response(e.message, status=400)
        except Tenants.DoesNotExist as e:
            logger.exception(e)
            logger.error(e)
            return Response(e.message, status=400)
        except TenantServiceInfo.DoesNotExist as e:
            logger.exception(e)
            logger.error(e)
            return Response(e.message, status=400)

        return Response("ok", status=200)

    def get(self, request, *args, **kwargs):
        return Response("ok")


class GetWebHooksUrl(AppBaseView):
    def get(self, request, *args, **kwargs):
        try:
            team_name = self.team_name
            tenant_id = self.tenant.tenant_id
            service_alias = self.service.service_alias
            username = self.user.nick_name

            service_obj = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias)[0]
            service_code_from = service_obj.code_from == "github" or service_obj.code_from == "gitlab_new" or service_obj.code_from == "gitlab_exit"
            if not (service_obj.service_source == "source_code" and service_code_from):
                result = general_message(400, "failed", "该应用不符合要求")
                return Response(result, status=400)
            hostname = socket.gethostname()
            logger.debug(hostname)
            print hostname

            url = "http://" + "127.0.0.1:9000/" + "console/team/" + team_name + "/apps/" + service_alias + "/users/" + username + "/webhook"
            result = general_message(200, "success", "获取webhooks-URl成功", list=[url])
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=400)

# {"status": "closed", "disabledAction": ["visit", "stop", "manage_container", "reboot"],
#  "status_cn": "已关闭", "activeAction": ["restart", "deploy"]}

# console/teams/gmbfztu3/apps/gr42d627/get-url
