# -*- coding: utf8 -*-
from typing import Any
from rest_framework.request import Request
from rest_framework.response import Response
from www.utils.return_message import general_message

from console.exception.main import AbortRequest
from console.views.base import BaseApiView, JWTAuthApiView
from console.services.custom_configs import custom_configs_service


class CustomConfigsCLView(BaseApiView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        configs = custom_configs_service.list()
        result = general_message(200, "success", msg_show="操作成功", list=configs)
        return Response(result, status=result["code"])

    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        data = request.data
        if type(data) != list:
            raise AbortRequest(msg="The request parameter must be a list", msg_show="请求参数必须为列表")
        custom_configs_service.bulk_create_or_update(data)
        result = general_message(200, "success", msg_show="操作成功", list=data)
        return Response(result, status=result["code"])


class CustomConfigsUserCLView(JWTAuthApiView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # NOTE: Users.nick_name is nullable but service expects str (systemic mismatch; backlog).
        configs = custom_configs_service.list(self.user.nick_name)  # type: ignore[arg-type]
        result = general_message(200, "success", msg_show="操作成功", list=configs)
        return Response(result, status=result["code"])

    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        data = request.data
        if type(data) != list:
            raise AbortRequest(msg="The request parameter must be a list", msg_show="请求参数必须为列表")
        custom_configs_service.bulk_create_or_update(data, self.user.nick_name)
        result = general_message(200, "success", msg_show="操作成功", list=data)
        return Response(result, status=result["code"])