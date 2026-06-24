import os
import re
from typing import Any, Tuple

import requests
from django.http import JsonResponse
from console.utils.cache_decorators import never_cache

from console.utils.offline import is_cloud_market_disabled
from console.views.base import JWTAuthApiView
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.region_repo import region_repo
from www.utils.return_message import general_message
from rest_framework.request import Request
from rest_framework.response import Response

region_api = RegionInvokeApi()
VERSION_INFO_TIMEOUT = 2
VERSION_NUMBER_PATTERN = re.compile(r"\d+")


def upgrade_version_sort_key(version: str) -> Tuple[Tuple[int, ...], str]:
    return tuple(int(part) for part in VERSION_NUMBER_PATTERN.findall(version)), version


class UpgradeView(JWTAuthApiView):
    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        regions = region_repo.get_all_regions()
        body: dict = {}
        for region in regions:
            resp = region_api.upgrade_region(region.region_name, request.data)
            body[region.region_name] = resp
        result = general_message(200, "success", "请求成功", bean=body)
        return Response(result, status=200)

    def get(self, request: Request, region_name: str, *args: Any, **kwargs: Any) -> Response:
        resp = region_api.list_upgrade_status(region_name)
        # NOTE: region API result may be None; .get access is a latent risk (backlog).
        result = general_message(200, "success", "请求成功", list=resp.get("list", []))  # type: ignore[union-attr]
        return Response(result, status=200)


def fetch_json_data() -> Any:
    if is_cloud_market_disabled():
        return None

    JSON_URL = os.getenv("VERSION_INFO_URL", "https://get.rainbond.com/upgrade-versions.json")
    try:
        response = requests.get(JSON_URL, timeout=VERSION_INFO_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


class UpgradeVersionLView(JWTAuthApiView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> JsonResponse:
        data = fetch_json_data()
        if data is None:
            return JsonResponse([], status=200, safe=False)
        versions = sorted([item["version"] for item in data], key=upgrade_version_sort_key, reverse=True)
        return JsonResponse(versions, safe=False)


class UpgradeVersionRView(JWTAuthApiView):
    def get(self, request: Request, version: str, *args: Any, **kwargs: Any) -> JsonResponse:
        data = fetch_json_data()
        if data is None:
            return JsonResponse({}, status=200, safe=False)
        version_detail = next((item["detail"] for item in data if item["version"] == version), None)
        return JsonResponse(version_detail or {}, status=200, safe=False)


class UpgradeVersionImagesView(JWTAuthApiView):
    def get(self, request: Request, version: str, *args: Any, **kwargs: Any) -> JsonResponse:
        data = fetch_json_data()
        if data is None:
            return JsonResponse({}, status=200, safe=False)
        images_info = next((item["images"] for item in data if item["version"] == version), None)
        return JsonResponse(images_info or {}, status=200, safe=False)
