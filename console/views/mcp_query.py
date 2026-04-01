# -*- coding: utf8 -*-
import json
import logging
import time
import uuid
from queue import Empty, Queue
from threading import Lock

from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.cache import never_cache

from console.exception.main import ServiceHandleException
from console.services.mcp_query_service import mcp_query_service
from console.views.base import JSONWebTokenAuthentication, InternalTokenAuthentication
from console.exception.exceptions import AuthenticationInfoHasExpiredError
from django.utils.encoding import smart_text
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header
from rest_framework.permissions import AllowAny
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.settings import api_settings

logger = logging.getLogger("default")

_MCP_SESSION_LOCK = Lock()
_MCP_SSE_SESSIONS = {}
_MCP_HTTP_PROTOCOL_VERSIONS = ("2025-03-26", "2025-06-18")
_MCP_HTTP_DEFAULT_PROTOCOL_VERSION = "2025-03-26"


class MCPSSEEventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode(self.charset)
        return json.dumps(data, ensure_ascii=False, default=str).encode(self.charset)


class MCPSSESession(object):

    def __init__(self, user, protocol_version="2024-11-05"):
        self.session_id = uuid.uuid4().hex
        self.user = user
        self.protocol_version = protocol_version
        self.queue = Queue()

    def send(self, message):
        self.queue.put(message)


def _register_mcp_sse_session(user, protocol_version="2024-11-05"):
    session = MCPSSESession(user, protocol_version=protocol_version)
    with _MCP_SESSION_LOCK:
        _MCP_SSE_SESSIONS[session.session_id] = session
    return session


def _get_mcp_sse_session(session_id):
    if not session_id:
        return None
    with _MCP_SESSION_LOCK:
        return _MCP_SSE_SESSIONS.get(session_id)


def _remove_mcp_sse_session(session_id):
    if not session_id:
        return
    with _MCP_SESSION_LOCK:
        _MCP_SSE_SESSIONS.pop(session_id, None)


class MCPJSONWebTokenAuthentication(JSONWebTokenAuthentication):
    """
    Compatible JWT parser for MCP clients:
    - GRJWT <token>
    - GRJWT<token>
    - Bearer <token>
    - raw token value
    - token in query/body (token/access_token/jwt)
    """

    def get_jwt_value(self, request):
        auth = get_authorization_header(request).split()
        auth_header_prefix = api_settings.JWT_AUTH_HEADER_PREFIX.lower()
        valid_prefixes = [auth_header_prefix, "jwt", "bearer"]

        raw_header = smart_text(get_authorization_header(request) or b"").strip()
        raw_lower = raw_header.lower()

        if auth:
            first = smart_text(auth[0].lower())
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

        if api_settings.JWT_AUTH_COOKIE:
            cookie_token = request.COOKIES.get(api_settings.JWT_AUTH_COOKIE)
            if cookie_token:
                return cookie_token

        for key in ("token", "access_token", "jwt"):
            token = request.GET.get(key)
            if not token and isinstance(getattr(request, "data", None), dict):
                token = request.data.get(key)
            if token:
                return token.strip()
        return None


class MCPJSONWebTokenAuthenticationSafe(MCPJSONWebTokenAuthentication):
    """
    Optional JWT auth for connection handshake:
    return None instead of raising auth errors.
    """

    def authenticate(self, request):
        try:
            return super(MCPJSONWebTokenAuthenticationSafe, self).authenticate(request=request)
        except (AuthenticationInfoHasExpiredError, exceptions.AuthenticationFailed):
            return None
        except Exception:
            return None


class MCPQueryRPCMixin(object):
    permission_classes = (AllowAny, )
    authentication_classes = (InternalTokenAuthentication, MCPJSONWebTokenAuthenticationSafe)
    renderer_classes = (MCPSSEEventStreamRenderer, JSONRenderer)

    def _parse_request_payload(self, request):
        if isinstance(request.data, dict):
            return request.data
        if not request.body:
            return {}
        try:
            return json.loads(request.body.decode("utf-8"))
        except Exception:
            return {}

    def _dispatch_rpc(self, payload, user, protocol_version="2024-11-05"):
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
                data = mcp_query_service.call_tool(user, tool_name, arguments)
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

        return self._jsonrpc_error(request_id, -32601, "Method not found: {}".format(method))

    @staticmethod
    def _jsonrpc_result(request_id, result):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    @staticmethod
    def _jsonrpc_error(request_id, code, message):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    @staticmethod
    def _format_sse_message(event, data, serialize_json=True):
        if serialize_json:
            payload = json.dumps(data, ensure_ascii=False, default=str)
        else:
            payload = smart_text(data)
        return "event: {event}\ndata: {data}\n\n".format(event=event, data=payload)

    @staticmethod
    def _format_sse_data(data, serialize_json=True):
        if serialize_json:
            payload = json.dumps(data, ensure_ascii=False, default=str)
        else:
            payload = smart_text(data)
        return "data: {data}\n\n".format(data=payload)

    @staticmethod
    def _is_authenticated_user(user):
        return user is not None and hasattr(user, "user_id") and getattr(user, "is_authenticated", True)


class MCPQuerySSEView(MCPQueryRPCMixin, APIView):
    """Legacy MCP HTTP+SSE endpoint for backwards-compatible clients."""

    @never_cache
    def get(self, request, *args, **kwargs):
        session = _register_mcp_sse_session(request.user if self._is_authenticated_user(request.user) else None)
        return self._build_sse_response(request, session)

    @never_cache
    def post(self, request, *args, **kwargs):
        return Response(
            {"detail": "Use the endpoint event URI for POST requests."},
            status=405,
        )

    @never_cache
    def options(self, request, *args, **kwargs):
        response = HttpResponse(status=204)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Content-Type, Authorization"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    def _build_sse_response(self, request, session):
        message_endpoint = request.build_absolute_uri(
            "/console/mcp/query/message?session_id={}".format(session.session_id)
        )

        def event_stream():
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


class MCPQueryMessageView(MCPQueryRPCMixin, APIView):

    @never_cache
    def post(self, request, *args, **kwargs):
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
    def options(self, request, *args, **kwargs):
        response = HttpResponse(status=204)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Content-Type, Authorization"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response


class MCPQueryHTTPView(MCPQueryRPCMixin, APIView):
    """Streamable HTTP MCP endpoint."""

    @never_cache
    def post(self, request, *args, **kwargs):
        payload = self._parse_request_payload(request)
        if not isinstance(payload, dict):
            return Response({"detail": "Invalid JSON-RPC payload."}, status=400)

        method = payload.get("method")
        session_id = request.META.get("HTTP_MCP_SESSION_ID", "")
        session = _get_mcp_sse_session(session_id)

        if method == "initialize":
            protocol_version = self._resolve_http_protocol_version(request)
            user = request.user if self._is_authenticated_user(request.user) else None
            session = _register_mcp_sse_session(user, protocol_version=protocol_version)
        else:
            if not session_id:
                return Response({"detail": "Mcp-Session-Id header is required."}, status=400)
            if session is None:
                return Response({"detail": "MCP HTTP session not found."}, status=404)
            protocol_version = session.protocol_version or self._resolve_http_protocol_version(request)

        user = request.user if self._is_authenticated_user(request.user) else (session.user if session else None)
        rpc_response = self._dispatch_rpc(payload, user, protocol_version=protocol_version)

        if payload.get("id") is None:
            response = HttpResponse(status=202)
        else:
            if self._request_accepts_sse(request):
                response = StreamingHttpResponse(
                    self._single_rpc_sse_stream(rpc_response),
                    content_type="text/event-stream",
                )
                response["Cache-Control"] = "no-cache"
                response["Content-Encoding"] = "identity"
            else:
                response = Response(rpc_response, status=200)
        if session is not None:
            response["Mcp-Session-Id"] = session.session_id
        response["MCP-Protocol-Version"] = protocol_version
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = (
            "Cache-Control, Content-Type, Authorization, MCP-Protocol-Version, Mcp-Session-Id"
        )
        response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return response

    @never_cache
    def get(self, request, *args, **kwargs):
        session_id = request.META.get("HTTP_MCP_SESSION_ID", "")
        session = _get_mcp_sse_session(session_id)
        if not session_id:
            return Response({"detail": "Mcp-Session-Id header is required."}, status=400)
        if session is None:
            return Response({"detail": "MCP HTTP session not found."}, status=404)
        protocol_version = session.protocol_version or self._resolve_http_protocol_version(request)

        def event_stream():
            try:
                while True:
                    try:
                        rpc_response = session.queue.get(timeout=15)
                    except Empty:
                        yield ": keepalive {}\n\n".format(int(time.time()))
                        continue
                    yield self._format_sse_data(rpc_response)
            except GeneratorExit:
                logger.info("mcp http stream session closed: %s", session.session_id)

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Content-Encoding'] = 'identity'
        response["Mcp-Session-Id"] = session.session_id
        response["MCP-Protocol-Version"] = protocol_version
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Cache-Control, Content-Type, Authorization, MCP-Protocol-Version, Mcp-Session-Id'
        response['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        return response

    @never_cache
    def delete(self, request, *args, **kwargs):
        session_id = request.META.get("HTTP_MCP_SESSION_ID", "")
        if not session_id:
            return Response({"detail": "Mcp-Session-Id header is required."}, status=400)
        if _get_mcp_sse_session(session_id) is None:
            return Response({"detail": "MCP HTTP session not found."}, status=404)
        _remove_mcp_sse_session(session_id)
        response = HttpResponse(status=204)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Content-Type, Authorization, MCP-Protocol-Version, Mcp-Session-Id"
        response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return response

    @never_cache
    def options(self, request, *args, **kwargs):
        response = HttpResponse(status=204)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Cache-Control, Content-Type, Authorization, MCP-Protocol-Version, Mcp-Session-Id"
        response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        return response

    @staticmethod
    def _request_accepts_sse(request):
        accept = smart_text(request.META.get("HTTP_ACCEPT", "")).lower()
        return "text/event-stream" in accept

    @staticmethod
    def _single_rpc_sse_stream(rpc_response):
        yield "event: message\n" + MCPQueryRPCMixin._format_sse_data(rpc_response)

    def _resolve_http_protocol_version(self, request):
        version = request.META.get("HTTP_MCP_PROTOCOL_VERSION", "") or _MCP_HTTP_DEFAULT_PROTOCOL_VERSION
        if version not in _MCP_HTTP_PROTOCOL_VERSIONS:
            raise exceptions.ParseError("Unsupported MCP-Protocol-Version: {}".format(version))
        return version
