# -*- coding: utf-8 -*-
import json
from typing import Any, Optional

from rest_framework.request import Request
from rest_framework.response import Response

from console.models.main import ConsoleSysConfig
from console.views.base import EnterpriseAdminView
from www.utils.return_message import general_message
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()

_STORAGE_CONFIG_KEY = "default_storage_class_{region}"


class PlatformResourceTypesView(EnterpriseAdminView):
    def get(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        res, data = region_api.get_cluster_resource(region, "platform-resources/types")
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class PlatformResourcesView(EnterpriseAdminView):
    def get(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_cluster_resource(region, "platform-resources", params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]

    def post(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.post_cluster_resource(region, "platform-resources", request.body, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class PlatformResourceDetailView(EnterpriseAdminView):
    def get(self, request: Request, eid: str, region: str, name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.get_cluster_resource(region, "platform-resources/{}".format(name), params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]

    def put(self, request: Request, eid: str, region: str, name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        res, data = region_api.put_cluster_resource(region, "platform-resources/{}".format(name), request.body, params=params)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]

    def delete(self, request: Request, eid: str, region: str, name: str, *args: Any, **kwargs: Any) -> Response:
        params = {k: v for k, v in request.GET.items()}
        region_api.delete_cluster_resource(region, "platform-resources/{}".format(name), params=params)
        return Response(general_message(200, "success", "删除成功"))


class StorageClassesView(EnterpriseAdminView):
    def get(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        res, data = region_api.get_cluster_resource(region, "storageclasses")
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]

    def post(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        res, data = region_api.post_cluster_resource(region, "storageclasses", request.body)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class StorageClassDetailView(EnterpriseAdminView):
    def delete(self, request: Request, eid: str, region: str, name: str, *args: Any, **kwargs: Any) -> Response:
        region_api.delete_cluster_resource(region, "storageclasses/{}".format(name))
        return Response(general_message(200, "success", "删除成功"))


class PersistentVolumesView(EnterpriseAdminView):
    def get(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        res, data = region_api.get_cluster_resource(region, "persistentvolumes")
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]

    def post(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        res, data = region_api.post_cluster_resource(region, "persistentvolumes", request.body)
        return Response(general_message(200, "success", "OK", bean=data.get("bean")))  # type: ignore[union-attr]


class PersistentVolumeDetailView(EnterpriseAdminView):
    def delete(self, request: Request, eid: str, region: str, name: str, *args: Any, **kwargs: Any) -> Response:
        region_api.delete_cluster_resource(region, "persistentvolumes/{}".format(name))
        return Response(general_message(200, "success", "删除成功"))


class StorageConfigView(EnterpriseAdminView):
    """
    GET  — 返回当前集群的应用市场默认存储类配置，附带该 StorageClass 的 K8s 详情
    PUT  — 更新默认存储类，持久化到 ConsoleSysConfig
    """

    def _config_key(self, region: str) -> str:
        return _STORAGE_CONFIG_KEY.format(region=region)

    def _get_sc_detail(self, region: str, sc_name: str) -> Optional[dict]:
        """从 K8s 实时获取指定 StorageClass 的详情，失败时返回 None"""
        try:
            res, data = region_api.get_cluster_resource(region, "storageclasses")
            sc_list = (data.get("bean") or {}).get("list", [])  # type: ignore[union-attr]
            for sc in sc_list:
                if sc.get("name") == sc_name:
                    return sc
        except Exception:
            pass
        return None

    def get(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        key = self._config_key(region)
        cfg = ConsoleSysConfig.objects.filter(key=key, enterprise_id=eid).first()
        default_sc = cfg.value if cfg else None

        sc_detail = self._get_sc_detail(region, default_sc) if default_sc else None

        bean = {
            "default_storage_class": default_sc,
            "storage_class_detail": sc_detail,
        }
        return Response(general_message(200, "success", "OK", bean=bean))

    def put(self, request: Request, eid: str, region: str, *args: Any, **kwargs: Any) -> Response:
        try:
            body = json.loads(request.body)
        except (ValueError, TypeError):
            body = request.data
        sc_name = body.get("default_storage_class", "")
        if not sc_name:
            return Response(general_message(400, "bad_request", "default_storage_class 不能为空"), status=400)

        key = self._config_key(region)
        ConsoleSysConfig.objects.update_or_create(
            key=key,
            enterprise_id=eid,
            defaults={
                "value": sc_name,
                "type": "string",
                "desc": "应用市场默认存储类 (region={})".format(region),
                "enable": True,
            },
        )
        return Response(general_message(200, "success", "更新成功", bean={"default_storage_class": sc_name}))
