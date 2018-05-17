# -*- coding: utf-8 -*-
import logging
from console.views.base import BaseApiView, JWTAuthApiView, AlowAnyApiView
from rest_framework.response import Response

logger = logging.getLogger("default")


class WebHooks(AlowAnyApiView):

    def post(self, request, *args, **kwargs):
        host = self.request.META.get("HOST",None)
        event = request.META.get("X-GitHub-Event", None)
        content_type = request.META.get("Content-Type", None)
        Signature = request.META.get("X-Hub-Signature", None)

        ref = request.data.get("ref")
        ref = ref.split("/")[-1]
        id = request.data.get("repository")["id"]
        full_name = request.data.get("repository")["full_name"]
        url = "https://github.com/"+full_name

        print ("xxxxx",[host,event, content_type,Signature,ref, id, url])



        return Response("ok", status=200)
