# -*- coding: utf-8 -*-
from rest_framework.response import Response

from console.views.base import EnterpriseAdminView
from goodrain_web.tools import general_message
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


def _encode_params(params):
    return "&".join("{}={}".format(k, v) for k, v in params.items())


class PlatformResourceTypesView(EnterpriseAdminView):
    def get(self, request, eid, region, *args, **kwargs):
        res, data = region_api.get_cluster_resource(region, "platform-resources/types")
        return Response(general_message(200, "success", "OK", bean=data))


class PlatformResourcesView(EnterpriseAdminView):
    def get(self, request, eid, region, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_cluster_resource(region, "platform-resources", params=params)
        return Response(general_message(200, "success", "OK", bean=data))

    def post(self, request, eid, region, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.post_cluster_resource(region, "platform-resources", request.body, params=params)
        return Response(general_message(200, "success", "OK", bean=data))


class PlatformResourceDetailView(EnterpriseAdminView):
    def get(self, request, eid, region, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_cluster_resource(region, "platform-resources/{}".format(name), params=params)
        return Response(general_message(200, "success", "OK", bean=data))

    def delete(self, request, eid, region, name, *args, **kwargs):
        params = {k: v for k, v in request.GET.items()}
        region_api.delete_cluster_resource(region, "platform-resources/{}".format(name), params=params)
        return Response(general_message(200, "success", "删除成功"))


class StorageClassesView(EnterpriseAdminView):
    def get(self, request, eid, region, *args, **kwargs):
        res, data = region_api.get_cluster_resource(region, "storageclasses")
        return Response(general_message(200, "success", "OK", bean=data))

    def post(self, request, eid, region, *args, **kwargs):
        res, data = region_api.post_cluster_resource(region, "storageclasses", request.body)
        return Response(general_message(200, "success", "OK", bean=data))


class StorageClassDetailView(EnterpriseAdminView):
    def delete(self, request, eid, region, name, *args, **kwargs):
        region_api.delete_cluster_resource(region, "storageclasses/{}".format(name))
        return Response(general_message(200, "success", "删除成功"))


class PersistentVolumesView(EnterpriseAdminView):
    def get(self, request, eid, region, *args, **kwargs):
        res, data = region_api.get_cluster_resource(region, "persistentvolumes")
        return Response(general_message(200, "success", "OK", bean=data))

    def post(self, request, eid, region, *args, **kwargs):
        res, data = region_api.post_cluster_resource(region, "persistentvolumes", request.body)
        return Response(general_message(200, "success", "OK", bean=data))


class PersistentVolumeDetailView(EnterpriseAdminView):
    def delete(self, request, eid, region, name, *args, **kwargs):
        region_api.delete_cluster_resource(region, "persistentvolumes/{}".format(name))
        return Response(general_message(200, "success", "删除成功"))
