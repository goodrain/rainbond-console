# -*- coding: utf8 -*-
from rest_framework.response import Response
from www.utils.return_message import general_message

from console.exception.main import AbortRequest
from console.views.base import BaseApiView
from console.services.custom_configs import custom_configs_service


class CustomConfigsCLView(BaseApiView):
    def get(self, request, *args, **kwargs):
        configs = custom_configs_service.list()
        result = general_message(200, "success", msg_show="操作成功", list=configs)
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        data = request.data
        if type(data) != list:
            raise AbortRequest(msg="The request parameter must be a list", msg_show="请求参数必须为列表")
        custom_configs_service.bulk_create_or_update(data)
        result = general_message(200, "success", msg_show="操作成功", list=data)
        return Response(result, status=result["code"])
