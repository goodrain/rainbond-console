# -*- coding: utf-8 -*-
"""Authorized same-origin noVNC assets and one component's binary VNC socket."""
from urllib.parse import urlparse

import requests
from django.http import Http404, HttpResponse, StreamingHttpResponse
from rest_framework.exceptions import PermissionDenied

from console.utils.vm_vnc_proxy import (component_vnc_backend_path, component_vnc_prefix, get_vm_vnc_upstream,
                                        validate_static_path)
from console.views.app_config.base import AppBaseView


class ComponentVNCView(AppBaseView):
    http_method_names = ['get', 'head']
    parser_classes = ()

    def check_perms(self, request, *args, **kwargs):
        super().check_perms(request, *args, **kwargs)
        if not self.is_team_owner and not self.is_enterprise_admin:
            self.has_perms([300010])

    def initial(self, request, *args, **kwargs):
        self.perform_authentication(request)
        self.check_permissions(request)
        super().initial(request, *args, **kwargs)
        if (self.tenant.enterprise_id != self.user.enterprise_id or self.service.service_region != self.region_name
                or self.service.extend_method != 'vm'):
            raise PermissionDenied()
        if request.META.get('HTTP_SEC_FETCH_SITE') == 'cross-site':
            raise PermissionDenied()
        self.upstream = get_vm_vnc_upstream(self.service.service_region)
        if not self.upstream:
            raise Http404()
        self.backend_vnc_path = component_vnc_backend_path(self.tenant, self.service, self.app)

    def get(self, request, *args, **kwargs):
        path = kwargs.get('vnc_path', '')
        if path == 'websockify':
            return self._websocket(request)
        path = validate_static_path(path)
        if request.META.get('HTTP_UPGRADE', '').lower() == 'websocket':
            raise PermissionDenied()
        # noVNC's path query can only select the WS route authorized above.
        expected = component_vnc_prefix(self.tenant, self.service).lstrip('/') + 'websockify'
        if (set(request.GET) - {'path'} or len(request.GET.getlist('path')) > 1
                or request.GET.get('path', expected) != expected):
            raise PermissionDenied()
        try:
            response = requests.get(self.upstream + '/' + path, stream=True, timeout=(10, 30), allow_redirects=False)
        except requests.RequestException:
            return HttpResponse('VNC service unavailable', status=502)
        if response.status_code != 200:
            code = 404 if response.status_code == 404 else 502
            response.close()
            return HttpResponse('VNC resource unavailable', status=code)

        def chunks():
            try:
                yield from response.iter_content(chunk_size=65536)
            finally:
                response.close()

        result = StreamingHttpResponse(chunks(), content_type=response.headers.get('Content-Type', 'application/octet-stream'))
        result['Cache-Control'] = 'no-store'
        result['X-Frame-Options'] = 'SAMEORIGIN'
        result['X-Content-Type-Options'] = 'nosniff'
        result['Referrer-Policy'] = 'same-origin'
        return result

    def head(self, request, *args, **kwargs):
        if kwargs.get('vnc_path') == 'websockify':
            return HttpResponse(status=405)
        validate_static_path(kwargs.get('vnc_path', ''))
        return HttpResponse(status=200, headers={'Cache-Control': 'no-store'})

    def _websocket(self, request):
        # Cookie-authenticated VNC is interactive, so require an exact same-origin
        # browser handshake. Do not forward Console cookies or JWT to virtvnc.
        origin = request.META.get('HTTP_ORIGIN', '')
        parsed = urlparse(origin)
        expected_origin = urlparse(request.build_absolute_uri('/'))
        if (parsed.scheme, parsed.netloc) != (expected_origin.scheme, expected_origin.netloc):
            raise PermissionDenied()
        if request.GET:
            raise PermissionDenied()
        raw_request = request._request
        client_ws = getattr(raw_request, 'environ', {}).get('wsgi.websocket') or request.META.get('wsgi.websocket')
        if not client_ws:
            return HttpResponse('WebSocket upgrade required', status=400)
        from console.utils.vm_vnc_proxy_relay import relay_component_vnc
        return relay_component_vnc(client_ws, self.upstream, self.backend_vnc_path)
