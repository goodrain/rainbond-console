# -*- coding: utf8 -*-
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.services.rainskills_access_service import rainskills_access_service
from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message


class RainSkillsAccessView(JWTAuthApiView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        access = rainskills_access_service.get_rainskills_access(self.user)
        return Response(general_message(200, "success", "查询成功", bean=access), status=200)
