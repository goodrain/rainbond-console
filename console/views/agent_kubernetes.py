# -*- coding: utf-8 -*-
import json
import logging
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.exception.main import ServiceHandleException
from console.views.base import JWTAuthApiView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class AgentKubernetesBootstrapView(JWTAuthApiView):
    """Generate an agent-owned kubeconfig on a target Rainbond region."""

    def post(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        if not self.is_enterprise_admin:
            return Response(general_message(403, "forbidden", "无权限生成 Kubernetes 凭据"), status=403)
        if enterprise_id != self.user.enterprise_id:
            return Response(general_message(403, "forbidden", "无权限操作该企业"), status=403)

        payload = dict(request.data or {})
        payload.setdefault("region_name", region_name)
        payload.setdefault("context_id", region_name)
        payload.setdefault("service_account", "rainbond-agent")

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
