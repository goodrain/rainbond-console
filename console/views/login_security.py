# -*- coding: utf-8 -*-
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.exception.main import NoPermissionsError
from console.serializers.login_security import LoginSecurityConfigSerializer
from console.services.login_security_service import login_security_config_service
from console.views.base import EnterpriseAdminView
from www.utils.return_message import general_message


class LoginSecurityConfigView(EnterpriseAdminView):
    def _check_admin(self, enterprise_id: str) -> None:
        if self.user.enterprise_id != enterprise_id or not self.is_enterprise_admin:
            raise NoPermissionsError

    def get(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        self._check_admin(enterprise_id)
        config = login_security_config_service.get_config()
        return Response(general_message(200, "success", "查询成功", bean=config), status=200)

    def put(self, request: Request, enterprise_id: str, *args: Any, **kwargs: Any) -> Response:
        self._check_admin(enterprise_id)
        serializer = LoginSecurityConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        config = login_security_config_service.update_config(**serializer.validated_data)
        return Response(general_message(200, "success", "更新成功", bean=config), status=200)
