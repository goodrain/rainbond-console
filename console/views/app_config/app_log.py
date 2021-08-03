# -*- coding: utf8 -*-
from django.http.response import StreamingHttpResponse

from console.views.app_config.base import AppBaseView
from console.services.app_config.component_logs import component_log_service


class ComponentLogView(AppBaseView):
    def get(self, request, *args, **kwargs):
        pod_name = request.GET.get("pod_name")
        container_name = request.GET.get("container_name")
        stream = component_log_service.get_component_log_stream(self.tenant_name, self.region_name, pod_name, container_name)
        response = StreamingHttpResponse(stream, content_type="text/plain")
        # disabled the GZipMiddleware on this call by inserting a fake header into the StreamingHttpResponse
        response['Content-Encoding'] = 'identity'
        return response
