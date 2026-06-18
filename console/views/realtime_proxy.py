# -*- coding: utf-8 -*-
from typing import Any

from django.http import HttpRequest, HttpResponseBase
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from console.utils.realtime_proxy import proxy_http_request, proxy_websocket_request


@method_decorator(csrf_exempt, name="dispatch")
class RegionRealtimeProxyView(View):
    http_method_names = ["get", "post", "put", "delete", "head", "options", "patch"]

    @method_decorator(never_cache)
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if self._is_websocket_request(request):
            return proxy_websocket_request(request, kwargs.get("region_name"), kwargs.get("proxy_path", ""))
        return proxy_http_request(request, kwargs.get("region_name"), kwargs.get("proxy_path", ""))

    @staticmethod
    def _is_websocket_request(request: HttpRequest) -> bool:
        if getattr(request, "environ", {}).get("wsgi.websocket") or request.META.get("wsgi.websocket"):
            return True
        return request.META.get("HTTP_UPGRADE", "").lower() == "websocket"
