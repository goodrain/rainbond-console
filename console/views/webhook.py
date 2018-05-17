# -*- coding: utf-8 -*-
import logging
from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from rest_framework.response import Response
from rest_framework.views import APIView
from console.views.app_config.base import AppBaseView

logger = logging.getLogger("default")
import socket
from www.models.main import Tenants, TenantServiceInfo, Users
from console.services.app import app_service
from console.services.app_actions import app_manage_service
from console.services.app_actions import event_service
from www.utils.return_message import general_message, error_message

class WebHooks(AlowAnyApiView):

    def post(self, request, team_name, app_name, *args, **kwargs):
        try:

            if request.META.get("HTTP_X_GITHUB_EVENT", None):


                tenant = Tenants.objects.get(tenant_name=team_name)
                print "tenant",tenant
                service = TenantServiceInfo.objects.filter(service_alias=app_name, tenant_id=tenant.tenant_id)[0]
                print "service",service
                status_map = app_service.get_service_status(tenant, service)
                print "vvvv",status_map
                status = status_map.get("status", None)
                print "status", status
                user = Users.objects.get(user_id=100)

                if status == "running":
                    code, msg, event = app_manage_service.deploy(tenant, service, user)
                    bean = {}
                    if event:
                        bean = event.to_dict()
                        bean["type_cn"] = event_service.translate_event_type(event.type)
                    if code != 200:
                        return Response(general_message(code, "deploy app error", msg, bean=bean), status=code)
                    result = general_message(code, "success", "操作成功", bean=bean)
                    return Response(result, status=200)

                event = request.META.get("HTTP_X_GITHUB_EVENT", None)
                Signature = request.META.get("HTTP_X_HUB_SIGNATURE", None)
                DELIVERY = request.META.get("HTTP_X_GITHUB_DELIVERY", None)
                user_agent = request.META.get("HTTP_USER_AGENT", None)
                print (event, Signature, DELIVERY, user_agent)
                # logger.debug(request.META)
                ref = request.data.get("ref")
                # ref = ref.split("/")[-1]
                id = request.data.get("repository")["id"]
                full_name = request.data.get("repository")["full_name"]
                # url = "https://github.com/" + full_name

                print ("xxxxx", [ref, id, full_name])

            if request.META.get("HTTP_X_GITLAB_EVENT", None):
                print request.META
                x = request.META.get("CONTENT_TYPE", None)

                x2 = request.META.get("HTTP_X_GITLAB_EVENT", None)

                x3 = request.META.get("HTTP_X_GITLAB_TOKEN", None)
                type(x3)
                print x,x2,x3

                event_name = request.data.get("event_name", None)
                ref = request.data.get("ref", None)
                project_id = request.data.get("project_id", None)
                url = request.data.get("project")["git_http_url"]

                print event_name,ref,project_id,url






        except Exception as e:
            logger.exception(e)
            logger.error(e)
            return Response(e.message, status=400)

        return Response("ok", status=200)

    def get(self, request, *args, **kwargs):
        return Response("ok")


class WebHooksUrl(AppBaseView):
    def get(self, request, *args, **kwargs):
        team_name = self.team_name
        app_name = self.service.service_alias

        hostName = socket.gethostname()
        print hostName
        return Response("http://" + "127.0.0.1:9000/" + "console/team/" + team_name + "/apps" + app_name + "/webhook")

{"status":"closed","disabledAction":["visit","stop","manage_container","reboot"],
 "status_cn":"已关闭","activeAction":["restart","deploy"]}