import requests, os
from django.http import JsonResponse
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

    def get(self, request, region_name, *args, **kwargs):
        resp = region_api.list_upgrade_status(region_name)
        result = general_message(200, "success", "请求成功", list=resp.get("list", []))
        return Response(result, status=200)

def fetch_json_data():
    JSON_URL = os.getenv("VERSION_INFO_URL", "https://get.rainbond.com/upgrade-versions.json")
    try:
        response = requests.get(JSON_URL)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

class UpgradeVersionLView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        data = fetch_json_data()
        if data is None:
            return JsonResponse([], status=200, safe=False)
        versions = sorted([item["version"] for item in data], reverse=True)
        return JsonResponse(versions, safe=False)


class UpgradeVersionRView(JWTAuthApiView):
    def get(self, request, version, *args, **kwargs):
        data = fetch_json_data()
        if data is None:
            return JsonResponse({}, status=200, safe=False)
        version_detail = next((item["detail"] for item in data if item["version"] == version), None)
        return JsonResponse(version_detail or {}, status=200, safe=False)


class UpgradeVersionImagesView(JWTAuthApiView):
    def get(self, request, version, *args, **kwargs):
        data = fetch_json_data()
        if data is None:
            return JsonResponse({}, status=200, safe=False)
        images_info = next((item["images"] for item in data if item["version"] == version), None)
        return JsonResponse(images_info or {}, status=200, safe=False)
