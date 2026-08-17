# -*- coding: utf8 -*-
import copy
import json
import logging
import time
import uuid
from queue import Empty, Queue
from threading import Lock
from typing import Any, Dict, Optional

from django.core import signing
from django.http import HttpResponse, StreamingHttpResponse
from console.utils.cache_decorators import never_cache

from console.exception.main import ServiceHandleException
from console.services.deployment_invocation import (
    deployment_invocation_context,
    get_deployment_invocation,
    is_rainskills_invocation,
)
from console.services.user_services import user_services
from console.services.mcp_query_service import mcp_query_service
from console.services.rainskills_deployment_service import rainskills_deployment_service
from console.views.base import JSONWebTokenAuthentication, InternalTokenAuthentication
from console.exception.exceptions import AuthenticationInfoHasExpiredError
from django.utils.encoding import smart_str
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from console.utils import jwt_issuer

logger = logging.getLogger("default")

_MCP_SESSION_LOCK = Lock()
_MCP_SSE_SESSIONS = {}
_MCP_HTTP_PROTOCOL_VERSIONS = ("2025-03-26", "2025-06-18")
_MCP_HTTP_DEFAULT_PROTOCOL_VERSION = "2025-03-26"
_MCP_HTTP_SESSION_SALT = "console.mcp.http.session"
_MCP_HTTP_SESSION_MAX_AGE_SECONDS = 1800


def _request_has_mcp_auth_input(request: Any) -> bool:
    if get_authorization_header(request):
        return True
    if jwt_issuer.JWT_AUTH_COOKIE and request.COOKIES.get(jwt_issuer.JWT_AUTH_COOKIE):
        return True
    for key in ("token", "access_token", "jwt"):
        if request.GET.get(key):
            return True
        if isinstance(getattr(request, "data", None), dict) and request.data.get(key):
            return True
    return False


def _build_mcp_auth_expired_response() -> Response:
    return Response({
        "code": "AUTH_TOKEN_EXPIRED",
        "status_code": 401,
        "error_code": 401,
        "msg": "token expired",
        "msg_show": "登录已过期，请重新登录",
    }, status=401)


class MCPSSEEventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"
    render_style = "binary"

    def render(self, data: Any, accepted_media_type: Optional[str] = None, renderer_context: Any = None) -> bytes:
        if data is None:
            return b""
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode(self.charset)
        return json.dumps(data, ensure_ascii=False, default=str).encode(self.charset)


class MCPSSESession(object):

    def __init__(self, user: Any, protocol_version: str = "2024-11-05") -> None:
        self.session_id = uuid.uuid4().hex
        self.user = user
        self.protocol_version = protocol_version
        self.queue: Queue = Queue()

    def send(self, message: Any) -> None:
        self.queue.put(message)


def _register_mcp_sse_session(user: Any, protocol_version: str = "2024-11-05") -> MCPSSESession:
    session = MCPSSESession(user, protocol_version=protocol_version)
    with _MCP_SESSION_LOCK:
        _MCP_SSE_SESSIONS[session.session_id] = session
    return session


def _get_mcp_sse_session(session_id: Optional[str]) -> Optional[MCPSSESession]:
    if not session_id:
        return None
    with _MCP_SESSION_LOCK:
        return _MCP_SSE_SESSIONS.get(session_id)


def _remove_mcp_sse_session(session_id: Optional[str]) -> None:
    if not session_id:
        return
    with _MCP_SESSION_LOCK:
        _MCP_SSE_SESSIONS.pop(session_id, None)


def _build_mcp_http_session_token(user: Any, protocol_version: str) -> str:
    payload = {"protocol_version": protocol_version}
    user_id = getattr(user, "user_id", None)
    if user_id is not None:
        payload["user_id"] = user_id
    return signing.dumps(payload, salt=_MCP_HTTP_SESSION_SALT, compress=True)


def _load_mcp_http_session(session_id: Optional[str]) -> Optional[dict]:
    if not session_id:
        return None
    try:
        payload = signing.loads(session_id, salt=_MCP_HTTP_SESSION_SALT, max_age=_MCP_HTTP_SESSION_MAX_AGE_SECONDS)
    except (signing.BadSignature, signing.SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    protocol_version = payload.get("protocol_version")
    if protocol_version not in _MCP_HTTP_PROTOCOL_VERSIONS:
        return None
    return payload


class MCPJSONWebTokenAuthentication(JSONWebTokenAuthentication):
    """
    Compatible JWT parser for MCP clients:
    - GRJWT <token>
    - GRJWT<token>
    - Bearer <token>
    - raw token value
    - token in query/body (token/access_token/jwt)
    """

    def get_jwt_value(self, request: Any) -> Any:
        auth = get_authorization_header(request).split()
        auth_header_prefix = jwt_issuer.JWT_AUTH_HEADER_PREFIX.lower()
        valid_prefixes = [auth_header_prefix, "jwt", "bearer"]

        raw_header = smart_str(get_authorization_header(request) or b"").strip()
        raw_lower = raw_header.lower()

        if auth:
            first = smart_str(auth[0].lower())
            if first in valid_prefixes and len(auth) >= 2:
                return auth[1]

            # Accept "GRJWT<token>" / "JWT<token>" / "Bearer<token>"
            for prefix in valid_prefixes:
                if raw_lower.startswith(prefix):
                    token = raw_header[len(prefix):].strip(" =")
                    if token:
                        return token

            # Accept raw jwt token in Authorization value.
            if raw_header.count(".") == 2:
                return raw_header

        if jwt_issuer.JWT_AUTH_COOKIE:
            cookie_token = request.COOKIES.get(jwt_issuer.JWT_AUTH_COOKIE)
            if cookie_token:
                return cookie_token

        for key in ("token", "access_token", "jwt"):
            token = request.GET.get(key)
            if not token and isinstance(getattr(request, "data", None), dict):
                token = request.data.get(key)
            if token:
                return token.strip()
        return None

    def validate_token_payload(self, payload: dict) -> None:
        if not jwt_issuer.is_valid_mcp_token_payload(payload, allow_legacy=True):
            raise AuthenticationInfoHasExpiredError("MCP token scope is invalid")

    def authenticate(self, request: Any) -> Any:
        setattr(request, "_allow_group_mcp_token", True)
        result = super(MCPJSONWebTokenAuthentication, self).authenticate(request)
        if not result:
            return result
        user, raw_token = result
        payload = jwt_issuer.decode_jwt(raw_token)
        if payload.get("token_purpose") != jwt_issuer.GROUP_MCP_TOKEN_PURPOSE:
            return result
        context = self._group_context(payload, user)
        delegated_user = copy.copy(user)
        delegated_user.is_enterprise_admin = True
        delegated_user.agent_group_mcp_context = context
        return delegated_user, raw_token

    @staticmethod
    def _group_context(payload: Dict[str, Any], user: Any) -> Dict[str, Any]:
        required = (
            "enterprise_id", "operator_user_id", "delegated_by_user_id",
            "group_policy_id", "member_grant_id", "policy_revision",
        )
        if any(payload.get(key) in (None, "") for key in required):
            raise exceptions.AuthenticationFailed("群委托凭据缺少必要范围")
        if str(getattr(user, "user_id", "")) != str(payload.get("operator_user_id")):
            raise exceptions.AuthenticationFailed("群委托操作人不匹配")
        if str(getattr(user, "enterprise_id", "")) != str(payload.get("enterprise_id")):
            raise exceptions.AuthenticationFailed("群委托企业不匹配")
        revision_value = payload.get("policy_revision")
        if revision_value is None:
            raise exceptions.AuthenticationFailed("群委托版本无效")
        try:
            revision = int(revision_value)
        except (TypeError, ValueError):
            raise exceptions.AuthenticationFailed("群委托版本无效")
        if revision <= 0:
            raise exceptions.AuthenticationFailed("群委托版本无效")
        return {
            "enterprise_id": str(payload["enterprise_id"]),
            "operator_user_id": str(payload["operator_user_id"]),
            "delegated_by_user_id": str(payload["delegated_by_user_id"]),
            "group_policy_id": str(payload["group_policy_id"]),
            "member_grant_id": str(payload["member_grant_id"]),
            "policy_revision": revision,
        }


class MCPJSONWebTokenAuthenticationSafe(MCPJSONWebTokenAuthentication):
    """
    Optional JWT auth for connection handshake:
    return None instead of raising auth errors.
    """

    def authenticate(self, request: Any) -> Any:
        try:
            return super(MCPJSONWebTokenAuthenticationSafe, self).authenticate(request=request)
        except AuthenticationInfoHasExpiredError as exc:
            if _request_has_mcp_auth_input(request):
                setattr(request, "_mcp_auth_error", exc)
            return None
        except exceptions.AuthenticationFailed as exc:
            if _request_has_mcp_auth_input(request):
                setattr(request, "_mcp_auth_error", exc)
            return None
        except Exception:
            return None


class MCPQueryRPCMixin(object):
    permission_classes = (AllowAny, )
    authentication_classes = (InternalTokenAuthentication, MCPJSONWebTokenAuthenticationSafe)
    renderer_classes = (MCPSSEEventStreamRenderer, JSONRenderer)

    def _parse_request_payload(self, request: Any) -> Any:
        if isinstance(request.data, dict):
            return request.data
        if not request.body:
            return {}
        try:
            return json.loads(request.body.decode("utf-8"))
        except Exception:
            return {}

    def _dispatch_rpc(self, payload: Any, user: Any, protocol_version: str = "2024-11-05") -> dict:
        if not isinstance(payload, dict):
            return self._jsonrpc_error(None, -32600, "Invalid Request")

        request_id = payload.get("id")
        if payload.get("jsonrpc") != "2.0":
            return self._jsonrpc_error(request_id, -32600, "Invalid JSON-RPC version")

        method = payload.get("method")
        params = payload.get("params") or {}

        if method == "initialize":
            return self._jsonrpc_result(request_id, {
                "protocolVersion": protocol_version,
                "serverInfo": {
                    "name": "rainbond-console-mcp",
                    "version": "0.1.0",
                },
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    }
                },
            })

        if method == "notifications/initialized":
            return self._jsonrpc_result(request_id, {"ok": True})

        if method == "tools/list":
            return self._jsonrpc_result(request_id, {
                "tools": mcp_query_service.list_tools(user),
            })

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(tool_name, str) or not tool_name:
                return self._jsonrpc_error(request_id, -32602, "tools/call requires string param 'name'")
            if not isinstance(arguments, dict):
                return self._jsonrpc_error(request_id, -32602, "tools/call requires object param 'arguments'")

            if not self._is_authenticated_user(user):
                err = {
                    "status_code": 401,
                    "error_code": 401,
                    "msg": "unauthorized",
                    "msg_show": "未登录或认证信息无效",
                }
                return self._jsonrpc_result(request_id, {
                    "isError": True,
                    "content": [{"type": "text", "text": json.dumps(err, ensure_ascii=False, default=str)}],
                    "structuredContent": err,
                })

            try:
                data = self._call_tool(user, tool_name, arguments)
                return self._jsonrpc_result(request_id, {
                    "isError": False,
                    "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str)}],
                    "structuredContent": data,
                })
            except ServiceHandleException as exc:
                err = {
                    "status_code": getattr(exc, "status_code", 400),
                    "error_code": getattr(exc, "error_code", getattr(exc, "status_code", 400)),
                    "msg": exc.msg,
                    "msg_show": exc.msg_show,
                }
                if getattr(exc, "details", None) is not None:
                    err["details"] = exc.details
                return self._jsonrpc_result(request_id, {
                    "isError": True,
                    "content": [{"type": "text", "text": json.dumps(err, ensure_ascii=False, default=str)}],
                    "structuredContent": err,
                })
            except Exception as exc:
                # Catch-all so NO tool failure escapes the MCP error shape. Without it,
                # non-ServiceHandleException errors (region CallApiError, AttributeError,
                # ...) bubble up to DRF as an opaque 500 that rainbond-copilot's
                # extractMcpErrorText cannot read, leaving telemetry error_message null.
                logger.exception("mcp tool call failed: tool=%s", tool_name)
                status_code, reason = self._describe_tool_exception(exc)
                err = {
                    "status_code": status_code,
                    "error_code": status_code,
                    "msg": "tool execution error",
                    "msg_show": reason,
                }
                return self._jsonrpc_result(request_id, {
                    "isError": True,
                    "content": [{"type": "text", "text": json.dumps(err, ensure_ascii=False, default=str)}],
                    "structuredContent": err,
                })

        return self._jsonrpc_error(request_id, -32601, "Method not found: {}".format(method))

    def _call_tool(self, user: Any, tool_name: str, arguments: dict) -> Any:
        if not is_rainskills_invocation():
            return mcp_query_service.call_tool(user, tool_name, arguments)

        mcp_query_service.assert_tool_visible(tool_name)

        service_sources = None
        if tool_name in ("rainbond_build_component", "rainbond_operate_app"):
            try:
                service_sources = mcp_query_service.resolve_deployment_service_sources(
                    user, tool_name, arguments)
            except Exception as exc:
                logger.warning(
                    "resolve RainSkills deployment sources failed: tool=%s error=%s",
                    tool_name, exc)
                service_sources = []

        tracker = None
        try:
            spec = rainskills_deployment_service.classify_tool_call(
                tool_name, arguments, service_sources=service_sources)
            if spec is not None:
                invocation = get_deployment_invocation()
                source_language = arguments.get("source_language") or arguments.get("language") or ""
                if not isinstance(source_language, str):
                    source_language = ""
                tracker = rainskills_deployment_service.safe_begin_tracking(
                    client=invocation.client,
                    tool=tool_name,
                    deploy_type=spec.deploy_type,
                    deploy_stage=spec.deploy_stage,
                    trigger=spec.trigger,
                    enterprise_id=getattr(user, "enterprise_id", "") or "",
                    tenant_name=arguments.get("team_name") or "",
                    region_name=arguments.get("region_name") or "",
                    app_id=arguments.get("app_id") or 0,
                    resource_created=spec.resource_created,
                    source_language=source_language,
                )
        except Exception as exc:
            logger.warning(
                "start RainSkills deployment tracking failed: tool=%s error=%s",
                tool_name, exc)

        try:
            result = mcp_query_service.call_tool(user, tool_name, arguments)
        except Exception as exc:
            reason = getattr(exc, "msg_show", None) or str(exc)
            if tracker is not None:
                try:
                    rainskills_deployment_service.safe_mark_failure(
                        tracker,
                        reason=reason,
                        failure_stage="tool",
                        failure_category=exc.__class__.__name__.lower(),
                    )
                except Exception as tracking_exc:
                    logger.warning(
                        "mark RainSkills deployment failure failed: tool=%s error=%s",
                        tool_name, tracking_exc)
            raise

        if tracker is not None:
            try:
                rainskills_deployment_service.safe_bind_tool_result(tracker, result)
            except Exception as exc:
                logger.warning(
                    "bind RainSkills deployment result failed: tool=%s error=%s",
                    tool_name, exc)
        return result

    @staticmethod
    def _jsonrpc_result(request_id: Any, result: Any) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    @staticmethod
    def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    @staticmethod
    def _format_sse_message(event: str, data: Any, serialize_json: bool = True) -> str:
        if serialize_json:
            payload = json.dumps(data, ensure_ascii=False, default=str)
        else:
            payload = smart_str(data)
        return "event: {event}\ndata: {data}\n\n".format(event=event, data=payload)

    @staticmethod
    def _format_sse_data(data: Any, serialize_json: bool = True) -> str:
        if serialize_json:
            payload = json.dumps(data, ensure_ascii=False, default=str)
        else:
            payload = smart_str(data)
        return "data: {data}\n\n".format(data=payload)

    @staticmethod
    def _is_authenticated_user(user: Any) -> bool:
        return user is not None and hasattr(user, "user_id") and getattr(user, "is_authenticated", True)

    @staticmethod
    def _describe_tool_exception(exc: Exception) -> Any:
        """Map an arbitrary tool exception to (http_status, human readable reason)."""
        status_raw = getattr(exc, "status", None)
        try:
            # NOTE: status_raw may be None; TypeError caught below (legacy, backlog).
            status_code = int(status_raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            status_code = 500
        if not (100 <= status_code <= 599):
            status_code = 500
        return status_code, MCPQueryRPCMixin._extract_tool_error_reason(exc)

    @staticmethod
    def _extract_tool_error_reason(exc: Exception) -> str:
        """Pull a concise, non-sensitive failure reason out of an exception.

        Region CallApiError carries a dict `message` whose `body` usually holds the
        upstream human message; prefer that over dumping the full url/body blob.
        """
        message = getattr(exc, "message", None)
        if isinstance(message, dict):
            body = message.get("body")
            if isinstance(body, dict):
                for key in ("msg_show", "msg", "message", "error"):
                    value = body.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()[:1000]
            httpcode = message.get("httpcode")
            if httpcode is not None:
                return "集群接口返回错误状态 {}".format(httpcode)
        if isinstance(message, str) and message.strip():
            return message.strip()[:1000]
        text = str(exc).strip()
        if text:
            return text[:1000]
        return exc.__class__.__name__


# NOTE: mixin declares permission/renderer/authentication_classes incompatibly with APIView (pre-existing).
class MCPQuerySSEView(MCPQueryRPCMixin, APIView):  # type: ignore[misc]
    """Legacy MCP HTTP+SSE endpoint for backwards-compatible clients."""

    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        if getattr(request, "_mcp_auth_error", None) is not None:
            return _build_mcp_auth_expired_response()
        session = _register_mcp_sse_session(request.user if self._is_authenticated_user(request.user) else None)
        return self._build_sse_response(request, session)

    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(
            {"detail": "Use the endpoint event URI for POST requests."},
            status=405,
        )

    @never_cache
    # NOTE: APIView.options returns Response/takes HttpRequest; CORS preflight needs raw HttpResponse (legacy, backlog).
    def options(self, request: Request, *args: Any, **kwargs: Any) -> HttpResponse:  # type: ignore[override]
        response = HttpResponse(status=204)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Content-Type, Authorization"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    def _build_sse_response(self, request: Any, session: MCPSSESession) -> StreamingHttpResponse:
        message_endpoint = request.build_absolute_uri(
            "/console/mcp/query/message?session_id={}".format(session.session_id)
        )

        def event_stream() -> Any:
            yield self._format_sse_message("endpoint", message_endpoint, serialize_json=False)

            try:
                while True:
                    try:
                        rpc_response = session.queue.get(timeout=15)
                    except Empty:
                        yield ": keepalive {}\n\n".format(int(time.time()))
                        continue
                    yield self._format_sse_message("message", rpc_response)
            except GeneratorExit:
                logger.info("mcp sse session closed: %s", session.session_id)
            finally:
                _remove_mcp_sse_session(session.session_id)

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Content-Encoding'] = 'identity'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Cache-Control, Content-Type, Authorization'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return response


class MCPQueryMessageView(MCPQueryRPCMixin, APIView):  # type: ignore[misc]

    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        if getattr(request, "_mcp_auth_error", None) is not None:
            return _build_mcp_auth_expired_response()
        session_id = request.GET.get("session_id")
        session = _get_mcp_sse_session(session_id)
        if session is None:
            return Response({"detail": "MCP SSE session not found."}, status=404)

        payload = self._parse_request_payload(request)
        if not isinstance(payload, dict):
            return Response({"detail": "Invalid JSON-RPC payload."}, status=400)

        user = request.user if self._is_authenticated_user(request.user) else session.user
        rpc_response = self._dispatch_rpc(payload, user)

        if payload.get("id") is not None:
            session.send(rpc_response)

        return HttpResponse(status=202)

    @never_cache
    def options(self, request: Request, *args: Any, **kwargs: Any) -> HttpResponse:  # type: ignore[override]
        response = HttpResponse(status=204)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Content-Type, Authorization"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response


class MCPQueryHTTPView(MCPQueryRPCMixin, APIView):  # type: ignore[misc]
    """Streamable HTTP MCP endpoint."""

    _EXPOSE_HEADERS = "Mcp-Session-Id, MCP-Protocol-Version"
    deploy_origin = "unknown"
    deploy_client = "unknown"

    @staticmethod
    def _get_http_session_user(session_payload: Optional[dict]) -> Any:
        user_id = (session_payload or {}).get("user_id")
        if not user_id:
            return None
        try:
            return user_services.get_user_by_user_id(user_id)
        except Exception:
            logger.exception("failed to load mcp http session user: %s", user_id)
            return None

    @classmethod
    def _apply_http_headers(cls, response: Any, protocol_version: str, session_id: Optional[str] = None) -> Any:
        if session_id:
            response["Mcp-Session-Id"] = session_id
        response["MCP-Protocol-Version"] = protocol_version
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = (
            "Cache-Control, Content-Type, Authorization, MCP-Protocol-Version, Mcp-Session-Id"
        )
        response["Access-Control-Expose-Headers"] = cls._EXPOSE_HEADERS
        response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return response

    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        if getattr(request, "_mcp_auth_error", None) is not None:
            return _build_mcp_auth_expired_response()
        payload = self._parse_request_payload(request)
        if not isinstance(payload, dict):
            return Response({"detail": "Invalid JSON-RPC payload."}, status=400)

        method = payload.get("method")
        session_id = request.META.get("HTTP_MCP_SESSION_ID", "")
        session_payload = _load_mcp_http_session(session_id)
        authenticated_user = request.user if self._is_authenticated_user(request.user) else None

        if method == "initialize":
            protocol_version = self._resolve_http_protocol_version(request)
            user = authenticated_user
            session_id = _build_mcp_http_session_token(user, protocol_version)
        else:
            if session_payload is not None:
                protocol_version = session_payload.get("protocol_version") or self._resolve_http_protocol_version(request)
            elif session_id:
                return Response({"detail": "MCP HTTP session not found."}, status=404)
            elif authenticated_user is not None:
                protocol_version = self._resolve_http_protocol_version(request)
                session_id = _build_mcp_http_session_token(authenticated_user, protocol_version)
            else:
                return Response({"detail": "Mcp-Session-Id header is required."}, status=400)

        user = authenticated_user or self._get_http_session_user(session_payload)
        with deployment_invocation_context(self.deploy_origin, self.deploy_client):
            rpc_response = self._dispatch_rpc(payload, user, protocol_version=protocol_version)

        if payload.get("id") is None:
            response = HttpResponse(status=202)
        else:
            if self._request_accepts_sse(request):
                # NOTE: response var reused across HttpResponse/StreamingHttpResponse/Response (legacy, backlog).
                response = StreamingHttpResponse(  # type: ignore[assignment]
                    self._single_rpc_sse_stream(rpc_response),
                    content_type="text/event-stream",
                )
                response["Cache-Control"] = "no-cache"
                response["Content-Encoding"] = "identity"
            else:
                response = Response(rpc_response, status=200)
        return self._apply_http_headers(response, protocol_version, session_id=session_id)

    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        if getattr(request, "_mcp_auth_error", None) is not None:
            return _build_mcp_auth_expired_response()
        session_id = request.META.get("HTTP_MCP_SESSION_ID", "")
        session_payload = _load_mcp_http_session(session_id)
        if not session_id:
            return Response({"detail": "Mcp-Session-Id header is required."}, status=400)
        if session_payload is None:
            return Response({"detail": "MCP HTTP session not found."}, status=404)
        protocol_version = session_payload.get("protocol_version") or self._resolve_http_protocol_version(request)

        def event_stream() -> Any:
            try:
                while True:
                    yield ": keepalive {}\n\n".format(int(time.time()))
                    time.sleep(15)
            except GeneratorExit:
                logger.info("mcp http stream session closed")

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Content-Encoding'] = 'identity'
        return self._apply_http_headers(response, protocol_version, session_id=session_id)

    @never_cache
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        if getattr(request, "_mcp_auth_error", None) is not None:
            return _build_mcp_auth_expired_response()
        session_id = request.META.get("HTTP_MCP_SESSION_ID", "")
        if not session_id:
            return Response({"detail": "Mcp-Session-Id header is required."}, status=400)
        session_payload = _load_mcp_http_session(session_id)
        if session_payload is None:
            return Response({"detail": "MCP HTTP session not found."}, status=404)
        response = HttpResponse(status=204)
        protocol_version = session_payload.get("protocol_version", _MCP_HTTP_DEFAULT_PROTOCOL_VERSION)
        return self._apply_http_headers(response, protocol_version, session_id=session_id)

    @never_cache
    def options(self, request: Request, *args: Any, **kwargs: Any) -> HttpResponse:  # type: ignore[override]
        response = HttpResponse(status=204)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Content-Type, Authorization, MCP-Protocol-Version, Mcp-Session-Id"
        response["Access-Control-Expose-Headers"] = self._EXPOSE_HEADERS
        response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return response

    @staticmethod
    def _request_accepts_sse(request: Any) -> bool:
        accept = smart_str(request.META.get("HTTP_ACCEPT", "")).lower()
        return "text/event-stream" in accept

    @staticmethod
    def _single_rpc_sse_stream(rpc_response: Any) -> Any:
        yield "event: message\n" + MCPQueryRPCMixin._format_sse_data(rpc_response)

    def _resolve_http_protocol_version(self, request: Any) -> str:
        version = request.META.get("HTTP_MCP_PROTOCOL_VERSION", "") or _MCP_HTTP_DEFAULT_PROTOCOL_VERSION
        if version not in _MCP_HTTP_PROTOCOL_VERSIONS:
            raise exceptions.ParseError("Unsupported MCP-Protocol-Version: {}".format(version))
        return version
