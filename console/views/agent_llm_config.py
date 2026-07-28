# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.exception.main import ServiceHandleException
from console.services.agent_llm_config_service import agent_llm_config_service
from console.services.auth.authentication import AgentRuntimeAuthentication
from console.login.jwt_authentication import JSONWebTokenAuthentication
from console.models.main import EnterpriseUserPerm
from console.utils import jwt_issuer
from console.views.base import EnterpriseAdminView, JWTAuthApiView
from www.models.main import TenantEnterprise, Users
from www.utils.return_message import general_message

FEISHU_MCP_CREDENTIAL_TTL_SECONDS = 1800
FEISHU_GROUP_MCP_CREDENTIAL_TTL_SECONDS = 300


def _decode_agent_service_token(request: Request) -> Dict[str, Any]:
    try:
        payload = jwt_issuer.decode_jwt(request.auth or "")
        return dict(payload) if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _require_agent_service_token(request: Request) -> Optional[Response]:
    payload = _decode_agent_service_token(request)
    token_enterprise_id = str(payload.get("enterprise_id") or "")
    user_enterprise_id = str(getattr(request.user, "enterprise_id", "") or "")
    is_global_admin = bool(getattr(request.user, "sys_admin", False))
    if payload.get("token_purpose") != "agent_service" or not token_enterprise_id or \
            (not is_global_admin and token_enterprise_id != user_enterprise_id):
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


class AgentMCPServiceCredentialsView(APIView):
    """Issue a short-lived service identity for Feishu user delegation."""

    authentication_classes = (AgentRuntimeAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        enterprise_id = str(request.META.get("HTTP_X_INTERNAL_TOKEN") or "").strip()
        if not enterprise_id or not TenantEnterprise.objects.filter(enterprise_id=enterprise_id).exists():
            return Response(general_message(403, "forbidden", "企业范围无效"), status=403)
        token = jwt_issuer.issue_agent_service_jwt(
            request.user, enterprise_id=enterprise_id,
            lifetime_seconds=FEISHU_MCP_CREDENTIAL_TTL_SECONDS)
        data = {
            "authorization": "{} {}".format(jwt_issuer.JWT_AUTH_HEADER_PREFIX, token),
            "cookie": "{}={}".format(jwt_issuer.JWT_AUTH_COOKIE, token),
            "enterprise_id": enterprise_id,
            "expires_in": FEISHU_MCP_CREDENTIAL_TTL_SECONDS,
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

        caller_enterprise_id = str(_decode_agent_service_token(request).get("enterprise_id") or "")
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

        token = jwt_issuer.issue_short_lived_jwt(
            delegated_user, lifetime_seconds=FEISHU_MCP_CREDENTIAL_TTL_SECONDS)
        data = {
            "authorization": "{} {}".format(jwt_issuer.JWT_AUTH_HEADER_PREFIX, token),
            "cookie": "{}={}".format(jwt_issuer.JWT_AUTH_COOKIE, token),
            "user_id": str(delegated_user.user_id),
            "enterprise_id": enterprise_id,
            "expires_in": FEISHU_MCP_CREDENTIAL_TTL_SECONDS,
        }
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)


class AgentMCPGroupDelegatedCredentialsView(APIView):
    """Issue an administrator-equivalent credential restricted to Console MCP."""

    authentication_classes = (JSONWebTokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        denied = _require_agent_service_token(request)
        if denied:
            return denied
        allowed_keys = {
            "enterprise_id", "operator_user_id", "delegated_by_user_id",
            "group_policy_id", "member_grant_id", "policy_revision",
        }
        if set(request.data.keys()) != allowed_keys:
            return Response(general_message(400, "invalid_request", "群委托参数不完整"), status=400)
        enterprise_id = str(request.data.get("enterprise_id") or "").strip()
        operator_user_id = _positive_int(request.data.get("operator_user_id"))
        delegated_by_user_id = _positive_int(request.data.get("delegated_by_user_id"))
        group_policy_id = str(request.data.get("group_policy_id") or "").strip()
        member_grant_id = str(request.data.get("member_grant_id") or "").strip()
        policy_revision = _positive_int(request.data.get("policy_revision"))
        if not enterprise_id or not operator_user_id or not delegated_by_user_id or not policy_revision or \
                not _valid_internal_id(group_policy_id) or not _valid_internal_id(member_grant_id):
            return Response(general_message(400, "invalid_request", "群委托参数无效"), status=400)
        service_enterprise_id = str(_decode_agent_service_token(request).get("enterprise_id") or "")
        if service_enterprise_id != enterprise_id:
            return Response(general_message(403, "forbidden", "企业范围不匹配"), status=403)
        if not TenantEnterprise.objects.filter(enterprise_id=enterprise_id).exists():
            return Response(general_message(403, "forbidden", "企业不存在"), status=403)
        if not EnterpriseUserPerm.objects.filter(
                enterprise_id=enterprise_id, user_id=delegated_by_user_id, identity="admin").exists():
            return Response(general_message(403, "forbidden", "群授权签发人不再是企业管理员"), status=403)
        operator = Users.objects.filter(
            user_id=operator_user_id, enterprise_id=enterprise_id, is_active=True).first()
        if not operator:
            return Response(general_message(403, "forbidden", "群操作人不存在或已停用"), status=403)
        token = jwt_issuer.issue_group_mcp_jwt(
            operator,
            enterprise_id=enterprise_id,
            delegated_by_user_id=str(delegated_by_user_id),
            group_policy_id=group_policy_id,
            member_grant_id=member_grant_id,
            policy_revision=policy_revision,
            lifetime_seconds=FEISHU_GROUP_MCP_CREDENTIAL_TTL_SECONDS,
        )
        data = {
            "authorization": "{} {}".format(jwt_issuer.JWT_AUTH_HEADER_PREFIX, token),
            "cookie": "{}={}".format(jwt_issuer.JWT_AUTH_COOKIE, token),
            "operator_user_id": str(operator_user_id),
            "enterprise_id": enterprise_id,
            "group_policy_id": group_policy_id,
            "member_grant_id": member_grant_id,
            "policy_revision": policy_revision,
            "expires_in": FEISHU_GROUP_MCP_CREDENTIAL_TTL_SECONDS,
        }
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)


class AgentFeishuRuntimeIdentityView(APIView):
    """Resolve a current enterprise employee for a server-issued Feishu invite."""

    authentication_classes = (JSONWebTokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        denied = _require_agent_service_token(request)
        if denied:
            return denied
        if set(request.data.keys()) != {"enterprise_id", "user_id"}:
            return Response(general_message(400, "invalid_request", "员工身份参数不完整"), status=400)
        enterprise_id = str(request.data.get("enterprise_id") or "").strip()
        user_id = _positive_int(request.data.get("user_id"))
        service_enterprise_id = str(_decode_agent_service_token(request).get("enterprise_id") or "")
        if not enterprise_id or not user_id:
            return Response(general_message(400, "invalid_request", "员工身份参数无效"), status=400)
        if service_enterprise_id != enterprise_id:
            return Response(general_message(403, "forbidden", "企业范围不匹配"), status=403)
        employee = Users.objects.filter(
            user_id=user_id, enterprise_id=enterprise_id, is_active=True).first()
        if not employee:
            return Response(general_message(404, "user_not_found", "员工不存在或已停用"), status=404)
        is_admin = bool(getattr(employee, "sys_admin", False)) or EnterpriseUserPerm.objects.filter(
            enterprise_id=enterprise_id, user_id=user_id, identity="admin").exists()
        data = {
            "user_id": str(employee.user_id),
            "username": employee.nick_name or str(employee.user_id),
            "display_name": employee.real_name or employee.nick_name or str(employee.user_id),
            "enterprise_id": enterprise_id,
            "roles": ["enterprise_admin"] if is_admin else [],
            "is_active": True,
        }
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)


def _positive_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _valid_internal_id(value: str) -> bool:
    if not value or len(value) > 64:
        return False
    return all(character.isalnum() or character in ("-", "_") for character in value)
