# -*- coding: utf-8 -*-
from typing import Any, Optional

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.exception.main import ServiceHandleException
from console.services.agent_llm_config_service import agent_llm_config_service
from console.login.jwt_authentication import JSONWebTokenAuthentication
from console.models.main import EnterpriseUserPerm
from console.utils import jwt_issuer
from console.views.base import EnterpriseAdminView, JWTAuthApiView
from www.models.main import TenantEnterprise, Users
from www.utils.return_message import general_message


def _require_agent_service_token(request: Request) -> Optional[Response]:
    try:
        payload = jwt_issuer.decode_jwt(str(request.auth or ""))
    except Exception:
        payload = {}
    token_enterprise_id = str(payload.get("enterprise_id") or "")
    user_enterprise_id = str(getattr(request.user, "enterprise_id", "") or "")
    if payload.get("token_purpose") != "agent_service" or not token_enterprise_id or \
            token_enterprise_id != user_enterprise_id:
        return Response(general_message(403, "forbidden", "无效的 Agent 服务身份"), status=403)
    return None


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
    authentication_classes = (JSONWebTokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        denied = _require_agent_service_token(request)
        if denied:
            return denied
        data = agent_llm_config_service.get_runtime_config()
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)


class AgentMCPRuntimeCredentialsView(APIView):
    authentication_classes = (JSONWebTokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        denied = _require_agent_service_token(request)
        if denied:
            return denied
        token = jwt_issuer.issue_jwt(request.user)
        data = {
            "authorization": "{} {}".format(jwt_issuer.JWT_AUTH_HEADER_PREFIX, token),
            "cookie": "{}={}".format(jwt_issuer.JWT_AUTH_COOKIE, token),
        }
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)


class AgentMCPDelegatedCredentialsView(APIView):
    authentication_classes = (JSONWebTokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        denied = _require_agent_service_token(request)
        if denied:
            return denied
        enterprise_id = str(request.data.get("enterprise_id") or "").strip()
        raw_user_id: object = request.data.get("user_id")
        if isinstance(raw_user_id, bool) or not isinstance(raw_user_id, (int, str)):
            user_id = 0
        else:
            try:
                user_id = int(raw_user_id)
            except ValueError:
                user_id = 0
        if not enterprise_id or user_id <= 0:
            return Response(
                general_message(400, "invalid_request", "enterprise_id 和 user_id 必填"), status=400)

        caller_enterprise_id = str(getattr(request.user, "enterprise_id", "") or "")
        if caller_enterprise_id != enterprise_id:
            return Response(general_message(403, "forbidden", "企业范围不匹配"), status=403)
        if not TenantEnterprise.objects.filter(enterprise_id=enterprise_id).exists():
            return Response(general_message(403, "forbidden", "企业不存在"), status=403)

        caller_user_id = getattr(request.user, "user_id", None)
        if not isinstance(caller_user_id, int) or caller_user_id <= 0:
            return Response(general_message(403, "forbidden", "无效的 Agent 服务用户"), status=403)
        if not getattr(request.user, "sys_admin", False) and not EnterpriseUserPerm.objects.filter(
                enterprise_id=enterprise_id, user_id=caller_user_id, identity="admin").exists():
            return Response(general_message(403, "forbidden", "Agent 服务身份无企业管理权限"), status=403)

        permission = EnterpriseUserPerm.objects.filter(
            enterprise_id=enterprise_id, user_id=user_id, identity="admin").first()
        if not permission:
            return Response(general_message(403, "forbidden", "用户不再具备企业管理员权限"), status=403)
        delegated_user = Users.objects.filter(user_id=user_id).first()
        if not delegated_user:
            return Response(general_message(404, "user_not_found", "用户不存在"), status=404)

        token = jwt_issuer.issue_short_lived_jwt(delegated_user, lifetime_seconds=300)
        data = {
            "authorization": "{} {}".format(jwt_issuer.JWT_AUTH_HEADER_PREFIX, token),
            "cookie": "{}={}".format(jwt_issuer.JWT_AUTH_COOKIE, token),
            "user_id": str(delegated_user.user_id),
            "enterprise_id": enterprise_id,
            "expires_in": 300,
        }
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)
