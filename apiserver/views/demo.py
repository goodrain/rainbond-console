# coding: utf-8
"""demo"""
from rest_framework.response import Response

from apiserver.utils.authentication import BaseView


class DemoView(BaseView):
    RESOURCE = "service"

    def get(self, request, *args, **kwargs):
        return Response(data={"msg": "this is demo"})
