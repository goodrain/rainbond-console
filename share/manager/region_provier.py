# -*- coding: utf8 -*-

from share.models.main import *
from decimal import Decimal
from django.conf import settings
from www.region import RegionInfo


class RegionBo(object):
    name = ""
    show_name = ""
    provider_name = ""

    memory_price = Decimal(0)
    memory_trial_price = Decimal(0)
    memory_package_price = Decimal(0)

    disk_price = Decimal(0)
    disk_trial_price = Decimal(0)
    disk_package_price = Decimal(0)

    net_price = Decimal(0)
    net_trial_price = Decimal(0)
    net_package_price = Decimal(0)

    def get_memory_price(self):
        return self.memory_price, self.memory_trial_price, self.memory_package_price

    def get_net_price(self):
        return self.net_price, self.net_trial_price, self.net_package_price

    def get_disk_price(self):
        return self.disk_price, self.disk_trial_price, self.disk_package_price


class RegionSetting(object):
    def __init__(self, region_name, region_properties):
        self.region_name = region_name
        self.properties_dict = {p.key: p for p in region_properties}
        self.setting = {p.key: p.value for p in region_properties}

    def get_stream_domain_url(self):
        return self.setting.get("STREAM_DOMAIN_URL", "")

    def set_stream_domain_url(self, domain_url):
        self._update_property("STREAM_DOMAIN_URL", domain_url)

    def get_wild_domains(self):
        return self.setting.get("WILD_DOMAINS", "")

    def get_wild_ports(self):
        return self.setting.get("WILD_PORTS", "")

    def get_http_proxy(self):
        return self.setting.get("HTTP_PROXY_TYPE", ""), self.setting.get("HTTP_PROXY_TYPE_HOST", ""), self.setting.get("HTTP_PROXY_TYPE_PORT", "")

    def get_region_service_api(self):
        return self.setting.get("REGION_SERVICE_API_URL", ""), self.setting.get("REGION_SERVICE_API_APITYPE", ""), self.setting.get(
            "REGION_SERVICE_API_REGION_NAME", "")

    def get_websocket_url(self):
        return self.setting.get("WEBSOCKET_URL", "")

    def get_regions(self):
        return self.setting.get("REGIONS_NAME", ""), self.setting.get("REGIONS_LABEL", ""), self.setting.get("REGIONS_ENABLE", "")

    def get_log_domain(self):
        return self.setting.get("LOG_DOMAIN", "")

    def get_docker_wss_url(self):
        return self.setting.get("DOCKER_WSS_URL", "")

    def _update_property(self, key, value):
        self.setting.update({
            key: value
        })
        property = self.properties_dict.get(key)
        property.value = value
        property.save()

class RegionProviderManager(object):
    def __init__(self):
        pass

    def get_work_regions(self):
        work_region_list = list()

        regions = Region.objects.filter(work_status="work")
        for region in regions:
            region_bo = self._load_region_bo(region)
            work_region_list.append(region_bo)

        return work_region_list

    def get_work_region_by_name(self, region_name):
        regions = Region.objects.filter(work_status="work", name=region_name)
        if not regions:
            region_bo = RegionBo()
            region_bo.name = region_name
            region_bo.show_name = region_name
            region_bo.provider_name = "self"

        else:
            region = regions[0]
            region_bo = self._load_region_bo(region)

        return region_bo

    def _load_region_bo(self, region):
        region_bo = RegionBo()

        region_bo.name = region.name
        region_bo.show_name = region.show_name
        region_bo.provider_name = region.provider_name

        try:
            base_price = RegionResourceProviderPrice.objects.get(region=region.name)
            region_bo.memory_price = base_price.memory_price
            region_bo.disk_price = base_price.disk_price
            region_bo.net_price = base_price.net_price
        except RegionResourceProviderPrice.DoesNotExist:
            pass

        try:
            trial_price = RegionResourceSalesPrice.objects.get(region=region.name)
            region_bo.memory_trial_price = trial_price.memory_price
            region_bo.memory_package_price = trial_price.memory_package_price
            region_bo.disk_trial_price = trial_price.disk_price
            region_bo.disk_package_price = trial_price.disk_package_price
            region_bo.net_package_price = trial_price.net_package_price
            region_bo.net_trial_price = trial_price.net_package_price
        except RegionResourceSalesPrice.DoesNotExist:
            pass

        return region_bo

    def get_region_fee_rule(self):
        work_regions = self.get_work_regions()
        if work_regions:
            region_fee_rule = dict()
            for region in work_regions:
                fee_rule = dict()
                fee_rule['memory_money'] = region.memory_price.__float__()
                fee_rule['disk_money'] = region.disk_price.__float__()
                fee_rule['net_money'] = region.net_price.__float__()

                region_fee_rule[region.name] = fee_rule
            return region_fee_rule
        else:
            return settings.REGION_FEE_RULE

    def get_region_fee_rule_by_name(self, region_name):
        work_region = self.get_work_region_by_name(region_name)
        if work_region:
            fee_rule = dict()
            fee_rule['memory_money'] = work_region.memory_price.__float__()
            fee_rule['disk_money'] = work_region.disk_price.__float__()
            fee_rule['net_money'] = work_region.net_price.__float__()
            return fee_rule
        else:
            return settings.REGION_FEE_RULE[region_name]

    def get_work_region_name_pair(self):
        work_regions = Region.objects.filter(work_status="work").value_list("name", "show_name")
        if work_regions:
            return {name: show_name for name, show_name in work_regions}
        else:
            region_map = {}
            for item in RegionInfo.region_list:
                if item["enable"]:
                    region_map[item["name"]] = item["label"]
            return region_map

    def compute_region_pay_package_price(self, region_name, buy_memory, buy_disk, buy_net, period, pay_model):
        pay_fee = 0
        hour_of_month = 24 * 30

        fee_rule = self.get_region_fee_rule_by_name(region_name)
        if fee_rule:
            one1 = float(fee_rule["memory_money"]) * int(buy_memory)
            one2 = float(fee_rule["disk_money"]) * int(buy_disk)
            one3 = float(fee_rule["net_money"]) * int(buy_net)
            hour_fee = one1 + one2

            if pay_model == "year":
                profit_rate = 1.5
            else:
                profit_rate = 2

            pay_fee = hour_fee * hour_of_month * period * profit_rate + one3

        return pay_fee

    def is_work_region(self, region_name):
        return region_name in self.get_work_region_name_pair()

    def get_region_setting(self, region_name):
        region_properties = RegionProperty.objects.filter(region=region_name)
        return RegionSetting(region_properties)
