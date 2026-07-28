# -*- coding: utf-8 -*-
from typing import Any

from console.services.deploy_preflight_service import deploy_preflight_service
from console.utils import perms_route_config as perms
from console.utils.cache_decorators import never_cache
from console.views.base import RegionTenantHeaderView
from rest_framework.request import Request
from rest_framework.response import Response
from www.utils.return_message import general_message


class DeployPreflightView(RegionTenantHeaderView):
    @staticmethod
    def _target_group_id(request: Request) -> Any:
        request_data = request.data
        if not isinstance(request_data, dict):
            return None
        group_id = request_data.get("group_id")
        if group_id:
            return group_id
        payload = request_data.get("payload") or {}
        if isinstance(payload, dict):
            return payload.get("group_id")
        return None

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        group_id = self._target_group_id(request)
        if group_id:
            try:
                self.perm_app_id = int(group_id)
            except (TypeError, ValueError):
                self.perm_app_id = -1
        else:
            kwargs["__message"] = perms.APP_CREATE_PERMS["__message"]
        super(DeployPreflightView, self).initial(request, *args, **kwargs)

    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        deploy_type = request.data.get("deploy_type", "")
        payload = request.data.get("payload") or {}
        preflight = deploy_preflight_service.run(self.tenant, self.region, deploy_type, payload, self.user)
        return Response(general_message(200, "success", "检测完成", bean=preflight), status=200)
