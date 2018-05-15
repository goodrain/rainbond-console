# -*- coding: utf-8 -*-
import logging
from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from rest_framework.response import Response

logger = logging.getLogger("default")


class WebHooks(AlowAnyApiView):

    def post(self, request, *args, **kwargs):
        event = request._request.META.get("X-GitHub-Event", None)
        content_type = request._request.META.get("content-type", None)
        ref = request.data.get("ref")
        id = request.data.get("repository")["id"]
        full_name = request.data.get("repository")["full_name"]

        logger.exception("xxxxx",[event, content_type, ref, id, full_name])

        return Response("ok", status=200)
