# -*- coding: utf-8 -*-
import logging
from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("default")


class WebHooks(AlowAnyApiView):

    def post(self, request, *args, **kwargs):
        type = self.request.META.get("HTTP_X_GITHUB_EVENT", None)
        event = request.META.get("HTTP_X_GITHUB_EVENT", None)
        content_type = request.META.get("CONTENT-TYPE", None)
        Signature = request.META.get("HTTP_X_HUB_SIGNATURE", None)
        DELIVERY = request.META.get("HTTP_X_GITHUB_DELIVERY", None)

        x = request.META.get("X-Github-Delivery",None)
        x2 = request.META.get("X-Hub-Signature", None)
        x3 = request.META.get("User-Agent",None)
        x4 = request.META.get("X-GitHub-Event",None)
        x5 = request.META.get("Content-Type",None)

        ref = request.data.get("ref")
        ref = ref.split("/")[-1]
        id = request.data.get("repository")["id"]
        full_name = request.data.get("repository")["full_name"]
        url = "https://github.com/" + full_name

        logger.debug(request.META)

        logger.debug("xxxxx", [type, event, content_type, Signature,DELIVERY, ref, id, url])
        logger.debug( "ccc",x,x2,x3,x4,x5)

        return Response("ok", status=200)

    def get(self, request, *args, **kwargs):
        return Response("ok")
