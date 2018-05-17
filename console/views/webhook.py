# -*- coding: utf-8 -*-
import logging
from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from rest_framework.response import Response
from rest_framework.views import APIView
from console.views.app_config.base import AppBaseView

logger = logging.getLogger("default")
import socket


class WebHooks(AlowAnyApiView):

    def post(self, request, *args, **kwargs):
        try:
            type = self.request.META.get("HTTP_X_GITHUB_EVENT", None)
            event = request.META.get("HTTP_X_GITHUB_EVENT", None)
            content_type = request.META.get("CONTENT-TYPE", None)
            Signature = request.META.get("HTTP_X_HUB_SIGNATURE", None)
            DELIVERY = request.META.get("HTTP_X_GITHUB_DELIVERY", None)

            x = request.META.get("X-Github-Delivery", None)
            x2 = request.META.get("X-Hub-Signature", None)
            x3 = request.META.get("User-Agent", None)
            x4 = request.META.get("X-GitHub-Event", None)
            x5 = request.META.get("Content-Type", None)
            logger.debug(type, event, content_type, Signature, DELIVERY, x, x2, x3, x4, x5)
            logger.debug(request.META)
            ref = request.data.get("ref")
            # ref = ref.split("/")[-1]
            id = request.data.get("repository")["id"]
            full_name = request.data.get("repository")["full_name"]
            # url = "https://github.com/" + full_name

            logger.debug("xxxxx", [ref, id, full_name])

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
