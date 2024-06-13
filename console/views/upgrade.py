from django.views.decorators.cache import never_cache

from console.views.base import JWTAuthApiView
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.region_repo import region_repo
from www.utils.return_message import general_message
from rest_framework.response import Response

region_api = RegionInvokeApi()


class UpgradeView(JWTAuthApiView):
    @never_cache
    def post(self, request, *args, **kwargs):
        regions = region_repo.get_all_regions()
        body = {}
        for region in regions:
            resp = region_api.upgrade_region(region.region_name, request.data)
            body[region.region_name] = resp
        result = general_message(200, "success", "请求成功", bean=body)
        return Response(result, status=200)
