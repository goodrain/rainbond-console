import logging
from typing import Any

from console.utils.cache_decorators import never_cache

from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message
from rest_framework.request import Request
from rest_framework.response import Response

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class TenantImageRepositories(RegionTenantHeaderView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        res, body = region_api.get_tenant_image_repositories(self.region_name, self.tenant_name, self.tenant.namespace)
        # NOTE: regionapi may return None; backlog
        result = general_message(200, "success", "请求成功", list=body.get("list", []))  # type: ignore[union-attr]
        return Response(result, status=result["code"])


class TenantImageTags(RegionTenantHeaderView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        repository = request.GET.get("repository", None)
        res, body = region_api.get_tenant_image_tags(self.region_name, self.tenant_name, repository)  # type: ignore[arg-type]
        result = general_message(200, "success", "请求成功", list=body.get("list", []))  # type: ignore[union-attr]
        return Response(result, status=result["code"])
