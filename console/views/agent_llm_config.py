# -*- coding: utf-8 -*-
from typing import Any, Optional

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.exception.main import ServiceHandleException
from console.services.agent_llm_config_service import agent_llm_config_service
from console.services.auth.authentication import AgentRuntimeAuthentication
from console.utils import jwt_issuer
from console.views.base import EnterpriseAdminView, JWTAuthApiView
from www.utils.return_message import general_message


class AgentLLMConfigView(JWTAuthApiView):

    def _ensure_enterprise_admin(self) -> Optional[Response]:
        if not self.is_enterprise_admin:
            return Response(general_message(403, "forbidden", "无权限操作 AI 助手配置"), status=403)
        return None

    def get(self, request: Request, eid: str, *args: Any, **kwargs: Any) -> Response:
        data = agent_llm_config_service.get_masked_config()
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)

    def put(self, request: Request, eid: str, *args: Any, **kwargs: Any) -> Response:
        denied = self._ensure_enterprise_admin()
        if denied:
            return denied
        try:
            data = agent_llm_config_service.update_config(
                request.data,
                updated_by=getattr(self.user, "nick_name", "") or getattr(self.user, "user_id", ""),
            )
        except ServiceHandleException as exc:
            return Response(general_message(exc.error_code, exc.msg, exc.msg_show, bean=exc.bean), status=exc.status_code)
        return Response(general_message(200, "success", "更新成功", bean=data), status=200)

    def delete(self, request: Request, eid: str, *args: Any, **kwargs: Any) -> Response:
        denied = self._ensure_enterprise_admin()
        if denied:
            return denied
        data = agent_llm_config_service.clear_config()
        return Response(general_message(200, "success", "清空成功", bean=data), status=200)


class AgentLLMRuntimeConfigView(APIView):
    authentication_classes = (AgentRuntimeAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        data = agent_llm_config_service.get_runtime_config()
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)


class AgentMCPRuntimeCredentialsView(APIView):
    authentication_classes = (AgentRuntimeAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        token = jwt_issuer.issue_jwt(request.user)
        data = {
            "authorization": "{} {}".format(jwt_issuer.JWT_AUTH_HEADER_PREFIX, token),
            "cookie": "{}={}".format(jwt_issuer.JWT_AUTH_COOKIE, token),
        }
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)
