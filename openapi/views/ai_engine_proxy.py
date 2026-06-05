# -*- coding: utf-8 -*-
import logging

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from console.exception.main import ServiceHandleException
from openapi.services.ai_engine_proxy_service import ai_engine_proxy_service

logger = logging.getLogger("default")


def build_openai_error_response(message, status_code):
    error_type = "authentication_error" if status_code == 401 else "invalid_request_error"
    return Response(
        {
            "error": {
                "message": message,
                "type": error_type,
            }
        },
        status=status_code,
    )


class AIEnginePublicProxyView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny, )

    def get(self, request, team_name, proxy_path="", *args, **kwargs):
        return self._handle_proxy(request, team_name, proxy_path)

    def post(self, request, team_name, proxy_path="", *args, **kwargs):
        return self._handle_proxy(request, team_name, proxy_path)

    def _handle_proxy(self, request, team_name, proxy_path):
        try:
            ai_engine_proxy_service.extract_bearer_token(request.META.get("HTTP_AUTHORIZATION"))
            normalized_path = ai_engine_proxy_service.validate_proxy_target(request.method, proxy_path)
            resolved_region = ai_engine_proxy_service.resolve_unique_region(team_name)
            return ai_engine_proxy_service.proxy_request(
                request,
                resolved_region,
                normalized_path,
                request.META.get("QUERY_STRING", ""),
            )
        except ServiceHandleException as err:
            return build_openai_error_response(err.msg, err.status_code)
        except Exception as err:
            logger.exception("ai engine public proxy failed: %s", err)
            return build_openai_error_response("upstream ai-engine proxy failed", 502)
