# -*- coding: utf8 -*-

from rest_framework.response import Response
from openapi.views.base import BaseAPIView
from share.manager.region_provier import *
import logging

region_provider_manager = RegionProviderManager()


class RegionPriceQueryView(BaseAPIView):
    allowed_methods = ('GET',)

    def get(self, request, *args, **kwargs):

        work_regions = region_provider_manager.get_work_regions()

        region_price_list = list()
        for work_region in work_regions:
            region_price = dict()
            region_price['name'] = work_region.name
            region_price['show_name'] = work_region.show_name
            region_price['memory_price'] = work_region.memory_price.__float__()
            region_price['memory_trial_price'] = work_region.memory_trial_price.__float__()
            region_price['memory_package_price'] = work_region.memory_package_price.__float__()
            region_price['net_price'] = work_region.net_price.__float__()
            region_price['net_trial_price'] = work_region.net_trial_price.__float__()
            region_price['net_package_price'] = work_region.net_package_price.__float__()
            region_price['disk_price'] = work_region.disk_price.__float__()
            region_price['disk_trial_price'] = work_region.disk_trial_price.__float__()
            region_price['disk_package_price'] = work_region.disk_package_price.__float__()

            region_price_list.append({work_region.name: region_price})

        return Response(status=200, data={"success": True, "msg": u"ok", "region_price_list": region_price_list})


