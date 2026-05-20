# -*- coding: utf-8 -*-
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from console.exception.main import ServiceHandleException
from console.services.agent_llm_config_service import agent_llm_config_service
from console.services.auth.authentication import InternalTokenAuthentication
from console.views.base import EnterpriseAdminView
from www.utils.return_message import general_message


class AgentLLMConfigView(EnterpriseAdminView):

    def _ensure_enterprise_admin(self):
        if not self.is_enterprise_admin:
            return Response(general_message(403, "forbidden", "无权限操作 AI 助手配置"), status=403)
        return None

    def get(self, request, eid, *args, **kwargs):
        denied = self._ensure_enterprise_admin()
        if denied:
            return denied
        data = agent_llm_config_service.get_masked_config()
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)

    def put(self, request, eid, *args, **kwargs):
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


class AgentLLMRuntimeConfigView(APIView):
    authentication_classes = (InternalTokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def get(self, request, *args, **kwargs):
        data = agent_llm_config_service.get_runtime_config()
        return Response(general_message(200, "success", "获取成功", bean=data), status=200)
