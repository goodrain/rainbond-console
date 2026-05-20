# -*- coding: utf8 -*-
from console.services.agent_access_service import agent_access_service
from console.views.base import JWTAuthApiView
from rest_framework.response import Response
from www.utils.return_message import general_message


class AgentAccessView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        access = agent_access_service.get_agent_access(self.user)
        return Response(general_message(200, "success", "查询成功", bean=access), status=200)
