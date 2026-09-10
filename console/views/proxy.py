# -*- coding: utf8 -*-
import logging
from typing import Any

from django.views import View
from console.utils.cache_decorators import never_cache

from rest_framework.request import Request
from rest_framework.response import Response

from console.repositories.region_app import region_app_repo
from www.apiclient.regionapi import RegionInvokeApi

from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class ProxySSEView(View):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Any:
        path = request.get_full_path().replace("/console/sse", "")
        # NOTE: GET params are Optional[str] but region API expects str (systemic mismatch; backlog).
        return region_api.sse_proxy(request.GET.get("region_name"), path)  # type: ignore[arg-type]


class ProxyPassView(JWTAuthApiView):
    def sync_stream_port(self, request):
        if "/routes/tcp" not in request.path:
            return
        service_id = request.GET.get("service_id")
        container_port = request.GET.get("port")
        if not service_id or not container_port:
            return
        from console.repositories.app import service_repo
        from console.repositories.app_config import port_repo
        from console.repositories.region_repo import region_repo
        from console.services.app_config import port_service
        from www.models.main import Tenants
        service = service_repo.get_service_by_service_id(service_id)
        if not service or service.service_region != request.GET.get("region_name"):
            return
        tenant = Tenants.objects.get(tenant_id=service.tenant_id)
        if "/gateway/" + tenant.tenant_name + "/routes/tcp" not in request.path:
            return
        port = port_repo.get_service_port_by_port(tenant.tenant_id, service_id, int(container_port))
        if port:
            region = region_repo.get_region_by_region_name(service.service_region)
            port_service.sync_external_bindings(tenant, service, region, port)

    @never_cache
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        path = request.get_full_path().replace("/console", "")
        app_id = request.GET.get("appID")
        region_name = request.GET.get("region_name")
        if app_id and "routes/tcp?" in path:
            region_app_id = region_app_repo.get_region_app_id(region_name, app_id)  # type: ignore[arg-type]
            path = path.replace("appID=" + str(app_id), "appID=" + region_app_id) + "&intID=" + str(app_id)
        resp = region_api.post_proxy(request.GET.get("region_name"), path, request.data)  # type: ignore[arg-type]
        self.sync_stream_port(request)
        # NOTE: region API result may be None; indexing it is a latent risk (backlog).
        result = general_message(200, "success", "请求成功", bean=resp['bean'], list=resp['list'])  # type: ignore[index]
        return Response(result, status=result["code"])

    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        path = request.get_full_path().replace("/console", "")
        resp = region_api.get_proxy(
            request.GET.get("region_name"), path, app_id=request.GET.get("appID"))  # type: ignore[arg-type]
        result = general_message(200, "success", "请求成功", bean=resp['bean'], list=resp['list'])  # type: ignore[index]
        return Response(result, status=result["code"])

    @never_cache
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        path = request.get_full_path().replace("/console", "")
        resp = region_api.delete_proxy(request.GET.get("region_name"), path)  # type: ignore[arg-type]
        self.sync_stream_port(request)
        result = general_message(200, "success", "请求成功", bean=resp['bean'], list=resp['list'])  # type: ignore[index]
        return Response(result, status=result["code"])
