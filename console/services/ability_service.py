# -*- coding: utf8 -*-
import logging
from typing import Any, Dict, List

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class RainbondAbilityService(object):
    def list_abilities(self, enterprise_id: str, region_name: str) -> List[Any]:
        _, body = region_api.list_abilities(enterprise_id, region_name)
        abilities = body.get("list", [])  # type: ignore[union-attr]  # NOTE: body may be None if region call fails; caller handles it
        return abilities

    def get_ability(self, enterprise_id: str, region_name: str, ability_id: str) -> Dict[str, Any]:
        _, body = region_api.get_ability(enterprise_id, region_name, ability_id)
        ability = body.get("bean", {})  # type: ignore[union-attr]  # NOTE: body may be None if region call fails; caller handles it
        return ability

    def update_ability(self, enterprise_id: str, region_name: str, ability_id: str, k8s_object: Any) -> Any:
        body = {"object": k8s_object}  # type: ignore[assignment]  # NOTE: intentionally shadowed by region_api tuple unpack below
        _, body = region_api.update_ability(enterprise_id, region_name, ability_id, body)
        return body


rbd_ability_service = RainbondAbilityService()
