# -*- coding: utf-8 -*-
from typing import Any

from console.services.deploy_preflight_service import deploy_preflight_service
from console.utils.cache_decorators import never_cache
from console.views.base import RegionTenantHeaderView
from rest_framework.request import Request
from rest_framework.response import Response
from www.utils.return_message import general_message


class DeployPreflightView(RegionTenantHeaderView):
    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        deploy_type = request.data.get("deploy_type", "")
        payload = request.data.get("payload") or {}
        preflight = deploy_preflight_service.run(self.tenant, self.region, deploy_type, payload, self.user)
        return Response(general_message(200, "success", "检测完成", bean=preflight), status=200)
