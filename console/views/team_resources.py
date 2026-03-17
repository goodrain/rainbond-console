# -*- coding: utf-8 -*-
from rest_framework.response import Response

from console.views.base import TenantHeaderView
from www.utils.return_message import general_message
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class NsResourceTypesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        res, data = region_api.get_tenant_ns_resource_types(region_name, team_name)
        return Response(general_message(200, "success", "OK", bean=data))


class NsResourcesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_tenant_ns_resources(region_name, team_name, params=params)
        return Response(general_message(200, "success", "OK", bean=data))

    def post(self, request, team_name, region_name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.post_tenant_ns_resource(region_name, team_name, request.body, params=params)
        return Response(general_message(200, "success", "OK", bean=data))


class NsResourceDetailView(TenantHeaderView):
    def get(self, request, team_name, region_name, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_tenant_ns_resource(region_name, team_name, name, params=params)
        return Response(general_message(200, "success", "OK", bean=data))

    def delete(self, request, team_name, region_name, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        region_api.delete_tenant_ns_resource(region_name, team_name, name, params=params)
        return Response(general_message(200, "success", "删除成功"))


class HelmReleasesView(TenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        res, data = region_api.get_tenant_helm_releases(region_name, team_name)
        return Response(general_message(200, "success", "OK", bean=data))

    def post(self, request, team_name, region_name, *args, **kwargs):
        import json
        body = json.loads(request.body)
        res, data = region_api.install_tenant_helm_release(region_name, team_name, body)
        return Response(general_message(200, "success", "安装成功", bean=data))


class HelmReleaseDetailView(TenantHeaderView):
    def delete(self, request, team_name, region_name, release_name, *args, **kwargs):
        region_api.uninstall_tenant_helm_release(region_name, team_name, release_name)
        return Response(general_message(200, "success", "卸载成功"))
