# -*- coding: utf8 -*-
from django.http.response import StreamingHttpResponse

from console.views.app_config.base import AppBaseView
from console.services.app_config.component_logs import component_log_service
from console.exception.main import AbortRequest


class ComponentLogView(AppBaseView):
    def get(self, request, *args, **kwargs):
        pod_name = request.GET.get("pod_name")
        if not pod_name:
            raise AbortRequest("the field 'pod_name' is required")
        container_name = request.GET.get("container_name")
        if not container_name:
            raise AbortRequest("the field 'container_name' is required")
        follow = True if request.GET.get("follow") == "true" else False
        stream = component_log_service.get_component_log_stream(self.tenant_name, self.region_name, self.service.service_alias,
                                                                pod_name, container_name, follow)
        response = StreamingHttpResponse(stream, content_type="text/plain")
        # disabled the GZipMiddleware on this call by inserting a fake header into the StreamingHttpResponse
        response['Content-Encoding'] = 'identity'
        return response
