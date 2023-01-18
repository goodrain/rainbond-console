# -*- coding: utf8 -*-
import logging

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class RainbondAbilityService(object):
    def list_abilities(self, enterprise_id, region_name):
        _, body = region_api.list_abilities(enterprise_id, region_name)
        abilities = body.get("list", [])
        return abilities

    def get_ability(self, enterprise_id, region_name, ability_id):
        _, body = region_api.get_ability(enterprise_id, region_name, ability_id)
        ability = body.get("bean", {})
        return ability

    def update_ability(self, enterprise_id, region_name, ability_id, k8s_object):
        body = {"object": k8s_object}
        _, body = region_api.update_ability(enterprise_id, region_name, ability_id, body)
        return body


rbd_ability_service = RainbondAbilityService()
