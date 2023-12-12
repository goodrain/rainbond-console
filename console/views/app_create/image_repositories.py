import logging

from django.views.decorators.cache import never_cache

from console.views.base import RegionTenantHeaderView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message
from rest_framework.response import Response

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class TenantImageRepositories(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        res, body = region_api.get_tenant_image_repositories(self.region_name, self.tenant_name, self.tenant.namespace)
        result = general_message(200, "success", "请求成功", list=body.get("list", []))
        return Response(result, status=result["code"])


class TenantImageTags(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        repository = request.GET.get("repository", None)
        res, body = region_api.get_tenant_image_tags(self.region_name, self.tenant_name, repository)
        result = general_message(200, "success", "请求成功", list=body.get("list", []))
        return Response(result, status=result["code"])
