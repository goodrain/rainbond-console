# -*- coding: utf-8 -*-
from typing import Any, Optional, cast
from urllib.parse import quote, urlparse

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler

from console.login.jwt_authentication import JSONWebTokenAuthentication
from console.services import mcp_device_authorization as device_auth
from console.utils import jwt_issuer
from www.models.main import Users
from www.utils.return_message import general_message


DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


def _oauth_error(error: str, description: Optional[str] = None, status: int = 400,
                 retry_after: Optional[int] = None) -> Response:
    payload = {"error": error}
    if description:
        payload["error_description"] = description
    response = Response(payload, status=status)
    if retry_after is not None:
        response["Retry-After"] = str(retry_after)
    return response


def _single_form_value(request: Request, key: str, required: bool = True) -> str:
    if request.content_type != "application/x-www-form-urlencoded":
        raise device_auth.DeviceAuthorizationError("invalid_request")
    values = request.data.getlist(key) if hasattr(request.data, "getlist") else []
    if len(values) > 1:
        raise device_auth.DeviceAuthorizationError("invalid_request")
    value = values[0].strip() if values else ""
    if required and not value:
        raise device_auth.DeviceAuthorizationError("invalid_request")
    return value


def _public_origin(request: Request) -> str:
    configured = getattr(settings, "RAINBOND_MCP_DEVICE_PUBLIC_ORIGIN", "").rstrip("/")
    if configured:
        parsed = urlparse(configured)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path not in ("", "/"):
            raise device_auth.DeviceAuthorizationError("server_error", "invalid device public origin")
        return configured
    return "{}://{}".format(request.scheme, request.get_host())


class DeviceResponseMixin(object):

    def finalize_response(self, request: Request, response: Response, *args: Any, **kwargs: Any) -> Response:
        response = APIView.finalize_response(cast(APIView, self), request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        response["Pragma"] = "no-cache"
        return response

    def handle_exception(self, exc: Exception) -> Response:
        response = exception_handler(exc, APIView.get_exception_handler_context(cast(APIView, self)))
        if response is None:
            raise exc
        return response


class DeviceFeatureMixin(object):

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if not getattr(settings, "RAINBOND_MCP_DEVICE_FLOW_ENABLED", False):
            response = HttpResponse("Not Found", status=404, content_type="text/plain; charset=utf-8")
            response["Cache-Control"] = "no-store"
            response["Pragma"] = "no-cache"
            return response
        return APIView.dispatch(cast(APIView, self), request, *args, **kwargs)


class HeaderOnlyConsoleJWTAuthentication(JSONWebTokenAuthentication):

    def authenticate(self, request: Request) -> Any:
        if not get_authorization_header(request):
            raise exceptions.AuthenticationFailed("authorization header is required")
        return super(HeaderOnlyConsoleJWTAuthentication, self).authenticate(request)

    def get_jwt_value(self, request: Request) -> Any:
        if not get_authorization_header(request):
            return None
        return super(HeaderOnlyConsoleJWTAuthentication, self).get_jwt_value(request)

    def authenticate_header(self, request: Request) -> str:
        return "GRJWT"


class BrowserDeviceView(DeviceResponseMixin, DeviceFeatureMixin, APIView):
    authentication_classes = (HeaderOnlyConsoleJWTAuthentication, )
    permission_classes = (IsAuthenticated, )


class MCPDeviceCodeView(DeviceFeatureMixin, DeviceResponseMixin, APIView):
    authentication_classes = ()
    permission_classes = (AllowAny, )

    def post(self, request: Request) -> Response:
        try:
            client_id = _single_form_value(request, "client_id")
            scope = _single_form_value(request, "scope")
            created = device_auth.create_device_authorization(
                client_id=client_id,
                client_name="Rainskills",
                scope=scope,
                source=device_auth.get_request_source(request),
            )
            verification_uri = _public_origin(request) + "/#/device"
            return Response({
                "device_code": created.device_code,
                "user_code": created.user_code,
                "verification_uri": verification_uri,
                "verification_uri_complete": verification_uri + "?user_code=" + quote(created.user_code),
                "expires_in": created.expires_in,
                "interval": created.interval,
            })
        except device_auth.DeviceAuthorizationRateLimited as exc:
            return _oauth_error("slow_down", status=429, retry_after=exc.retry_after)
        except device_auth.DeviceAuthorizationError as exc:
            return _oauth_error(exc.error)


class MCPDeviceTokenView(DeviceFeatureMixin, DeviceResponseMixin, APIView):
    authentication_classes = ()
    permission_classes = (AllowAny, )

    def post(self, request: Request) -> Response:
        try:
            grant_type = _single_form_value(request, "grant_type")
            client_id = _single_form_value(request, "client_id")
            device_code = _single_form_value(request, "device_code")
            if grant_type != DEVICE_GRANT_TYPE:
                return _oauth_error("unsupported_grant_type")
            result = device_auth.poll_device_token(
                device_code, client_id, device_auth.get_request_source(request))
            if result.status != device_auth.POLL_APPROVED:
                return _oauth_error(result.status)

            user = Users.objects.filter(user_id=result.user_id, is_active=True).first()
            if not user or (result.enterprise_id and user.enterprise_id != result.enterprise_id):
                device_auth.mark_consumed_authorization_denied(result.record_id)
                return _oauth_error("access_denied")
            access_token = jwt_issuer.issue_mcp_jwt(user)
            return Response({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": int(jwt_issuer.get_mcp_token_lifetime().total_seconds()),
                "scope": "mcp",
            })
        except device_auth.DeviceAuthorizationRateLimited as exc:
            return _oauth_error("slow_down", status=429, retry_after=exc.retry_after)
        except device_auth.DeviceAuthorizationError as exc:
            return _oauth_error(exc.error)


class MCPDeviceInspectView(BrowserDeviceView):

    def post(self, request: Request) -> Response:
        user_code = request.data.get("user_code") if isinstance(request.data, dict) else None
        try:
            inspected = device_auth.inspect_user_code(
                user_code, request.user, device_auth.get_request_source(request))
            bean = {
                "user_code": inspected.user_code,
                "client_id": inspected.client_id,
                "client_name": inspected.client_name,
                "scope": inspected.scope,
                "expires_at": inspected.expires_at.isoformat(),
                "status": inspected.status,
            }
            return Response(general_message(200, "success", "查询成功", bean=bean))
        except device_auth.DeviceAuthorizationRateLimited as exc:
            response = Response(general_message(429, "rate limited", "请求过于频繁"), status=429)
            response["Retry-After"] = str(exc.retry_after)
            return response
        except device_auth.DeviceAuthorizationError as exc:
            return Response(general_message(400, exc.error, "设备授权码无效或已过期"), status=400)


class MCPDeviceAuthorizeView(BrowserDeviceView):

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        try:
            decided = device_auth.decide_user_code(
                data.get("user_code"),
                request.user,
                data.get("decision"),
                device_auth.get_request_source(request),
            )
            return Response(general_message(
                200, "success", "授权决定已保存", bean={"status": decided.status}))
        except device_auth.DeviceAuthorizationRateLimited as exc:
            response = Response(general_message(429, "rate limited", "请求过于频繁"), status=429)
            response["Retry-After"] = str(exc.retry_after)
            return response
        except device_auth.DeviceAuthorizationError as exc:
            return Response(general_message(400, exc.error, "设备授权码无效或已处理"), status=400)
