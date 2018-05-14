# -*- coding: utf-8 -*-

from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from rest_framework.response import Response


class WebHooks(AlowAnyApiView):

    def post(self, request, *args, **kwargs):
        print "xxxxxxxx", request.data

        return Response("ok", status=200)
