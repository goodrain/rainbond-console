# -*- coding: utf8 -*-
import logging

from base_view import ShareBaseView
from django.template.response import TemplateResponse
from share.models.main import *

logger = logging.getLogger('default')


class RegionOverviewView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/region_overview.html", self.get_context())


class RegionResourcePriceView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        provider = self.provider.provider_name
        region_price_list = list(RegionResourceProviderPrice.objects.filter(provider=provider))
        context = self.get_context()
        context.update({
            "region_price_list": region_price_list
        })
        return TemplateResponse(request, "share/region_resource_price.html", context)

    def post(self, request, *args, **kwargs):
        region = request.POSt.get("region", None)
        memory_price = request.POST.get("memory_price", None)
        disk_price = request.POST.get("disk_price", None)
        net_price = request.POSt.get("net_price", None)

        provider = self.provider.name

        provider_price = RegionResourceProviderPrice.objects.get(provider=provider, region=region)
        provider_price.memory_price = memory_price or provider_price.memory_price
        provider_price.disk_price = disk_price or provider_price.disk_price
        provider_price.net_price = net_price or provider_price.net_price
        provider_price.save()

        # 根据数据中心定价按照一定的规则生成平台零售价
        trial_price_list = list(RegionResourceSalesPrice.objects.filter(saler="goodrain"))
        if trial_price_list:
            for trial_price in trial_price_list:
                trial_price.memory_price, trial_price.memory_package_price = self.get_trial_price(
                    provider_price.memory_price)
                trial_price.disk_price, trial_price.disk_package_price = self.get_trial_price(provider_price.disk_price)
                trial_price.net_price, trial_price.net_package_price = self.get_trial_price(provider_price.net_price)

        else:
            self.save_region_resource_sales_price(provider_price, "goodrain", "appmarket")
            self.save_region_resource_sales_price(provider_price, "goodrain", "goodrain")

        return self.redirect_to("/region/price/")

    def save_region_resource_sales_price(self, provider_price, saler, saler_channel):
        trial_price = RegionResourceSalesPrice()
        trial_price.region = provider_price.region
        trial_price.provider = provider_price.provider
        trial_price.saler = saler
        trial_price.saler_channel = saler_channel
        trial_price.memory_price, trial_price.memory_package_price = self.get_trial_price(provider_price.memory_price)
        trial_price.disk_price, trial_price.disk_package_price = self.get_trial_price(provider_price.disk_price)
        trial_price.net_price, trial_price.net_package_price = self.get_trial_price(provider_price.net_price)
        trial_price.save()

    @staticmethod
    def get_trial_price(provider_base_price):

        used_trial_price = provider_base_price * 1.1 * 6
        package_trial_price = provider_base_price * 1.1 * 2

        return used_trial_price, package_trial_price


class RegionResourceConsumeView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/region_resource_consume.html", self.get_context())

    def post(self, request, *args, **kwargs):
        return TemplateResponse(request, "share/region_resource_consume.html", self.get_context())
