# -*- coding: utf8 -*-
from django.http import JsonResponse

from share.manager.region_provier import RegionProviderManager
from www.views.base import BaseView

rpmManager = RegionProviderManager()


class PriceDetailView(BaseView):
    """各个数据中心价格详情,返回json格式数据"""

    def get(self, request, *args, **kwargs):
        result = {}
        try:
            region_fee_fule = rpmManager.get_region_fee_rule()
            result["ok"] = True
            result["data"] = region_fee_fule
        except Exception as e:
            result["ok"] = False
            pass
        return JsonResponse(result, status=200)
