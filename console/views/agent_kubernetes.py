# -*- coding: utf-8 -*-
import json
import logging
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.exception.main import ServiceHandleException
from console.services.platform_plugin_service import platform_plugin_service
from console.views.base import JWTAuthApiView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()

OPS_CREDENTIAL_PROFILE = "ops"
READONLY_CREDENTIAL_PROFILE = "readonly"
OPS_SERVICE_ACCOUNT = "rainbond-agent"
READONLY_SERVICE_ACCOUNT = "rainbond-agent-reader"
SUPPORTED_CREDENTIAL_PROFILES = {OPS_CREDENTIAL_PROFILE, READONLY_CREDENTIAL_PROFILE}


class AgentKubernetesBootstrapView(JWTAuthApiView):
    """Generate an agent-owned kubeconfig on a target Rainbond region."""

    def post(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        if not self.is_enterprise_admin:
            return Response(general_message(403, "forbidden", "无权限生成 Kubernetes 凭据"), status=403)
        if enterprise_id != self.user.enterprise_id:
            return Response(general_message(403, "forbidden", "无权限操作该企业"), status=403)

        payload = dict(request.data or {})
        credential_profile = payload.get("credential_profile", OPS_CREDENTIAL_PROFILE)
        if not isinstance(credential_profile, str) or credential_profile not in SUPPORTED_CREDENTIAL_PROFILES:
            return Response(
                general_message(400, "invalid credential profile", "不支持的 Kubernetes 凭据类型"),
                status=400,
            )

        requested_service_account = payload.get("service_account")
        if credential_profile == READONLY_CREDENTIAL_PROFILE:
            if requested_service_account and requested_service_account != READONLY_SERVICE_ACCOUNT:
                return Response(
                    general_message(400, "invalid readonly service account", "只读凭据必须使用 rainbond-agent-reader"),
                    status=400,
                )
            readonly_context_id = "{}:readonly".format(region_name)
            if "context_id" in payload and payload["context_id"] != readonly_context_id:
                return Response(
                    general_message(400, "invalid readonly context", "只读凭据必须使用 {}".format(readonly_context_id)),
                    status=400,
                )
            payload["context_id"] = readonly_context_id
            payload["service_account"] = READONLY_SERVICE_ACCOUNT
        else:
            payload.setdefault("context_id", region_name)
            payload.setdefault("service_account", OPS_SERVICE_ACCOUNT)

        payload["credential_profile"] = credential_profile
        payload.setdefault("region_name", region_name)

        try:
            _, body = region_api.bootstrap_agent_kubeconfig(enterprise_id, region_name, payload)
        except ServiceHandleException as exc:
            return Response(general_message(exc.status_code, exc.msg, exc.msg_show), status=exc.status_code)
        except Exception as exc:
            logger.exception("bootstrap agent kubeconfig failed")
            return Response(general_message(500, "bootstrap agent kubeconfig failed", str(exc)), status=500)

        bean = body.get("bean") if isinstance(body, dict) else body
        if not isinstance(bean, dict) or not bean.get("kubeconfig"):
            return Response(general_message(500, "invalid kubeconfig response", "目标集群未返回有效 kubeconfig"), status=500)

        agent_payload = {
            "enterprise_id": enterprise_id,
            "region_name": bean.get("region_name") or region_name,
            "region_alias": bean.get("region_name") or region_name,
            "kubeconfig": bean.get("kubeconfig"),
            "credential_profile": bean.get("credential_profile") or payload["credential_profile"],
            "service_account": bean.get("service_account") or payload["service_account"],
            "context_id": bean.get("context_id") or payload["context_id"],
        }
        return region_api.proxy(
            request,
            "/v2/platform/backend/plugins/rainbond-agent/api/v1/kubernetes/credentials/bootstrap",
            region_name,
            requests_args={
                "body": json.dumps(agent_payload),
                "headers": {"Content-Type": "application/json"},
            },
        )


class AgentKubernetesEncryptionKeyView(JWTAuthApiView):
    """Manage the persisted Agent encryption-key state without exposing the key."""

    def _check_access(self, enterprise_id: str) -> Response | None:
        if not self.is_enterprise_admin:
            return Response(general_message(403, "forbidden", "无权限管理凭据加密密钥"), status=403)
        if enterprise_id != self.user.enterprise_id:
            return Response(general_message(403, "forbidden", "无权限操作该企业"), status=403)
        return None

    def get(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        denied = self._check_access(enterprise_id)
        if denied:
            return denied
        try:
            result = platform_plugin_service.get_agent_credential_encryption_key_status(
                enterprise_id, region_name)
            return Response(general_message(200, "success", "查询成功", bean=result), status=200)
        except ServiceHandleException as exc:
            return Response(general_message(exc.status_code, exc.msg, exc.msg_show), status=exc.status_code)

    def post(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        denied = self._check_access(enterprise_id)
        if denied:
            return denied
        if (request.data or {}).get("confirm_create") is not True:
            return Response(
                general_message(400, "credential_key_confirmation_required", "请确认生成并启用凭据加密密钥"),
                status=400,
            )
        try:
            _, body = region_api.get_agent_plugin_encryption_status(enterprise_id, region_name, self.user)
        except Exception:
            logger.warning(
                "agent credential encryption status unavailable enterprise_id=%s region_name=%s",
                enterprise_id,
                region_name,
            )
            return Response(
                general_message(503, "agent_encryption_status_unavailable", "无法确认 AI 助手加密状态，请稍后重试"),
                status=503,
            )

        try:
            agent_status = body.get("data") if isinstance(body, dict) else None
            if not isinstance(agent_status, dict) or not agent_status.get("status"):
                raise ServiceHandleException(
                    msg="agent_encryption_status_unavailable",
                    msg_show="无法确认 AI 助手加密状态，请稍后重试",
                    status_code=503,
                )
            if agent_status.get("status") == "recovery_required":
                raise ServiceHandleException(
                    msg="credential_key_recovery_required",
                    msg_show="检测到历史密文无法解密，请恢复原加密密钥",
                    status_code=412,
                )
            result = platform_plugin_service.ensure_agent_credential_encryption_key(
                enterprise_id, region_name, self.user, agent_status)
            return Response(general_message(200, "success", "加密密钥已处理", bean=result), status=200)
        except ServiceHandleException as exc:
            return Response(general_message(exc.status_code, exc.msg, exc.msg_show), status=exc.status_code)
        except Exception:
            logger.exception("ensure agent credential encryption key failed")
            return Response(
                general_message(503, "agent_encryption_status_unavailable", "无法确认 AI 助手加密状态，请稍后重试"),
                status=503,
            )
