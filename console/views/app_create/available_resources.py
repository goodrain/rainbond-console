# -*- coding: utf-8 -*-
from typing import Any

from console.services.available_resources_service import available_resources_service
from console.utils.cache_decorators import never_cache
from console.views.base import RegionTenantHeaderView
from rest_framework.request import Request
from rest_framework.response import Response
from www.utils.return_message import general_message


class AvailableResourcesView(RegionTenantHeaderView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        resources = available_resources_service.get_available_resources(self.tenant, self.region)
        return Response(general_message(200, "success", "查询成功", bean=resources), status=200)
