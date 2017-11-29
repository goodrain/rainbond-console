# -*- coding: utf8 -*-
from django.http import JsonResponse

from share.manager.region_provier import RegionProviderManager
from www.views.base import BaseView

rpmManager = RegionProviderManager()
region_fee_rule = {}


class PriceDetailView(BaseView):
    """各个数据中心价格详情,返回json格式数据"""

    def get(self, request, *args, **kwargs):
        result = {}
        try:
            if not region_fee_rule or request.GET.get('reflush'):
                work_regions = rpmManager.get_work_regions()
                if work_regions:
                    load_region_fee_rule = dict()
                    for region in work_regions:
                        fee_rule = dict()
                        fee_rule['trial'] = {
                            'memory_money': region.memory_trial_price.__float__(),
                            'disk_money': region.disk_trial_price.__float__(),
                            'net_money': region.net_trial_price.__float__()
                        }
                        fee_rule['package'] = {
                            'memory_money': region.memory_package_price.__float__(),
                            'disk_money': region.disk_package_price.__float__(),
                            'net_money': region.net_package_price.__float__()
                        }
                        load_region_fee_rule[region.name] = fee_rule
                    region_fee_rule.clear()
                    region_fee_rule.update(load_region_fee_rule)

            result["ok"] = True
            result["data"] = region_fee_rule
        except Exception as e:
            result["ok"] = False
            pass
        return JsonResponse(result, status=200)
