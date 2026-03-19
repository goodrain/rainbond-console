# -*- coding: utf-8 -*-
from django.http.response import StreamingHttpResponse
from rest_framework.response import Response

from console.services.app_actions import ws_service
from console.views.base import TenantHeaderView
from www.utils.return_message import general_message
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class NsResourceTypesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        res, data = region_api.get_tenant_ns_resource_types(region_name, team_name)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class NsResourcesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_tenant_ns_resources(region_name, team_name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))

    def post(self, request, team_name, region_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.post_tenant_ns_resource(region_name, team_name, request.body, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class NsResourceDetailView(TenantHeaderView):
    def get(self, request, team_name, region_name, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_tenant_ns_resource(region_name, team_name, name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))

    def put(self, request, team_name, region_name, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.put_tenant_ns_resource(region_name, team_name, name, request.body, params=params)
        return Response(general_message(200, "success", "更新成功", bean=data.get("bean")))

    def delete(self, request, team_name, region_name, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        region_api.delete_tenant_ns_resource(region_name, team_name, name, params=params)
        return Response(general_message(200, "success", "删除成功"))


class HelmReleasesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        res, data = region_api.get_tenant_helm_releases(region_name, team_name)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))

    def post(self, request, team_name, region_name, *args, **kwargs):
        body = request.data or {}
        res, data = region_api.install_tenant_helm_release(region_name, team_name, body)
        return Response(general_message(200, "success", "安装成功", bean=data.get("bean")))


class HelmReleaseDetailView(TenantHeaderView):
    def delete(self, request, team_name, region_name, release_name, *args, **kwargs):
        region_api.uninstall_tenant_helm_release(region_name, team_name, release_name)
        return Response(general_message(200, "success", "卸载成功"))


class ResourceCenterWorkloadDetailView(TenantHeaderView):
    def get(self, request, team_name, region_name, resource, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_resource_center_workload_detail(region_name, team_name, resource, name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class ResourceCenterPodDetailView(TenantHeaderView):
    def get(self, request, team_name, region_name, pod_name, *args, **kwargs):
        res, data = region_api.get_resource_center_pod_detail(region_name, team_name, pod_name)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class ResourceCenterEventsView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_resource_center_events(region_name, team_name, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))


class ResourceCenterPodLogsView(TenantHeaderView):
    def get(self, request, team_name, region_name, pod_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        stream = region_api.get_resource_center_pod_log(region_name, team_name, pod_name, params=params)
        response = StreamingHttpResponse(stream.stream(1024), content_type="text/event-stream")
        response['Content-Encoding'] = 'identity'
        return response


class ResourceCenterWSInfoView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        bean = {
            "event_websocket_url": ws_service.get_event_log_ws(request, region_name),
            "namespace": self.tenant.namespace or self.tenant.tenant_name,
            "tenant_name": self.tenant.tenant_name,
        }
        return Response(general_message(200, "success", "OK", bean=bean))
