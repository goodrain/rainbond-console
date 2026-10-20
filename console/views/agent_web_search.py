# -*- coding: utf-8 -*-
from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.exception.main import ServiceHandleException
from console.services.agent_web_search_service import agent_web_search_service
from console.services.auth.authentication import AgentRuntimeAuthentication
from www.utils.return_message import general_message


class AgentWebSearchRuntimeView(APIView):
    authentication_classes = (AgentRuntimeAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        payload = request.data or {}
        try:
            scope = str(
                getattr(request.user, "enterprise_id", "")
                or request.META.get("HTTP_X_INTERNAL_TOKEN", "")
                or "global"
            )
            result = agent_web_search_service.search(
                str(payload.get("query") or ""),
                int(payload.get("max_results") or 5),
                scope,
            )
        except (TypeError, ValueError):
            return Response(general_message(400, "invalid_request", "参数不合法"), status=400)
        except ServiceHandleException as exc:
            return Response(general_message(exc.error_code, exc.msg, exc.msg_show), status=exc.status_code)
        return Response(general_message(200, "success", "搜索成功", bean=result), status=200)
