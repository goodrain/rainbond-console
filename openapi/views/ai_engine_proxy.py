# -*- coding: utf-8 -*-
import logging
from typing import Any

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.exception.main import ServiceHandleException
from openapi.services.ai_engine_proxy_service import ai_engine_proxy_service

logger = logging.getLogger("default")


def build_openai_error_response(message: Any, status_code: int, anthropic: bool = False) -> Response:
    if status_code == 401:
        error_type = "authentication_error"
    elif anthropic and status_code == 403:
        error_type = "permission_error"
    elif anthropic and status_code == 429:
        error_type = "rate_limit_error"
    elif status_code >= 500:
        error_type = "api_error" if anthropic else "server_error"
    else:
        error_type = "invalid_request_error"
    payload = {
        "error": {
            "message": message,
            "type": error_type,
        }
    }
    if anthropic:
        payload["type"] = "error"
    return Response(payload, status=status_code)


class AIEnginePublicProxyView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny, )

    def get(self, request: Request, team_name: str, proxy_path: str = "", *args: Any, **kwargs: Any) -> Response:
        return self._handle_proxy(request, team_name, proxy_path, kwargs.get("region_name"))

    def post(self, request: Request, team_name: str, proxy_path: str = "", *args: Any, **kwargs: Any) -> Response:
        return self._handle_proxy(request, team_name, proxy_path, kwargs.get("region_name"))

    def _handle_proxy(self, request: Request, team_name: str, proxy_path: str, region_name: Any = None) -> Response:
        anthropic = proxy_path.strip("/") == "v1/messages"
        try:
            ai_engine_proxy_service.extract_api_key(request.META.get("HTTP_AUTHORIZATION"), request.META.get("HTTP_X_API_KEY"))
            normalized_path = ai_engine_proxy_service.validate_proxy_target(request.method, proxy_path)
            resolved_region = ai_engine_proxy_service.resolve_region(team_name, region_name)
            return ai_engine_proxy_service.proxy_request(
                request,
                resolved_region,
                normalized_path,
                request.META.get("QUERY_STRING", ""),
                team_name=team_name,
            )
        except ServiceHandleException as err:
            return build_openai_error_response(err.msg, err.status_code, anthropic)
        except Exception as err:
            logger.exception("ai engine public proxy failed: %s", err)
            return build_openai_error_response("upstream ai-engine proxy failed", 502, anthropic)
