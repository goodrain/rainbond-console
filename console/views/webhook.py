# -*- coding: utf-8 -*-
import logging
from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from rest_framework.response import Response
logger = logging.getLogger("default")

class WebHooks(AlowAnyApiView):

    def post(self, request, *args, **kwargs):
        logger.exception("xxxxx",request.data)

        return Response("ok", status=200)
