# -*- coding: utf8 -*-

from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from console.views.base import EnterpriseAdminView
from console.services.ability_service import rbd_ability_service
from www.utils.return_message import general_message
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient


class RainbondAbilityLView(EnterpriseAdminView):
    def get(self, request: Request, enterprise_id: str, region_name: str, *args: Any, **kwargs: Any) -> Response:
        abilities = rbd_ability_service.list_abilities(enterprise_id, region_name)
        return Response(general_message(200, "success", "查询成功", list=abilities))


class RainbondAbilityRUDView(EnterpriseAdminView):
    def put(self, request: Request, enterprise_id: str, region_name: str, ability_id: str, *args: Any,
            **kwargs: Any) -> Response:
        k8s_object = request.data["object"] if request.data.get("object") else {}
        try:
            ability = rbd_ability_service.update_ability(enterprise_id, region_name, ability_id, k8s_object)
        except RegionApiBaseHttpClient.CallApiError as exc:
            message = exc.body.get("msg")
            return Response(general_message(400, message, message), status=400)
        return Response(general_message(200, "success", "查询成功", bean=ability))

    def get(self, request: Request, enterprise_id: str, region_name: str, ability_id: str, *args: Any,
            **kwargs: Any) -> Response:
        try:
            ability = rbd_ability_service.get_ability(enterprise_id, region_name, ability_id)
        except RegionApiBaseHttpClient.CallApiError as exc:
            message = exc.body.get("msg")
            return Response(general_message(400, message, message), status=400)
        return Response(general_message(200, "success", "查询成功", bean=ability))
