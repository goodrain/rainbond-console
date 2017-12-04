# -*- coding: utf8 -*-
import logging

from base_view import ShareBaseView
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from share.models.main import *
from www.models.main import *
from www.services import enterprise_svc, user_svc
from datetime import datetime as dt
from share.manager.region_provier import RegionProviderManager, RegionBo
import datetime as clzdt
import calendar
import time
from decimal import Decimal
import json
import MySQLdb

logger = logging.getLogger('default')

PRICE_BASE = {
    "memory": {
        "depreciation": Decimal(1.2),
        "used_profit": Decimal(4),
        "package_profit": Decimal(2),
    },
    "disk": {
        "depreciation": Decimal(1.2),
        "used_profit": Decimal(4),
        "package_profit": Decimal(2),
    },
    "net": {
        "depreciation": Decimal(1.0),
        "used_profit": Decimal(1),
        "package_profit": Decimal(1),
    },
}


class RegionProviderView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        if self.provider.status == 0:
            return TemplateResponse(request, "share/region_provider_register.html", self.get_context())
        else:
            return self.redirect_to("/share/region/")

    def post(self, request, *args, **kwargs):
        region_provider = get_object_or_404(RegionProvider, pk=request.POST.get("provider_id"))
        region_provider.provider_name = request.POST.get("provider_name", None) or region_provider.provider_name
        region_provider.enter_name = request.POST.get("enter_name", None) or region_provider.enter_name
        # 处理照片上传
        region_provider.business_prove = request.POST.get("business_prove", None) or region_provider.business_prove
        region_provider.status = 1
        region_provider.save()
        return self.redirect_to("/share/region/")


class RegionOverviewView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        if self.provider.status == 0:
            return TemplateResponse(request, "share/region_provider_register.html", self.get_context())
        else:
            return TemplateResponse(request, "share/region_overview.html", self.get_context())


class RegionResourcePriceView(ShareBaseView):
    def get(self, request, *args, **kwargs):
        provider = self.provider.provider_name

        provider_price_list = list(RegionResourceProviderPrice.objects.filter(provider=provider))
        if not provider_price_list:
            return TemplateResponse(request, "share/region_resource_price.html", self.get_context())

        region_name_map = {x.region: x for x in provider_price_list}
        region = request.GET.get("region", "None")
        if region in region_name_map:
            region_price = region_name_map.get(region)
        else:
            region_price = provider_price_list[0]

        region_info = dict()
        region_info["region"] = region_price.region
        region_info["memory_price"] = region_price.memory_price
        region_info["disk_price"] = region_price.disk_price
        region_info["net_price"] = region_price.net_price

        try:
            saler_price = RegionResourceSalesPrice.objects.get(provider=provider, region=region_price.region)
            region_info["trial_memory_price"] = saler_price.memory_price
            region_info["trial_disk_price"] = saler_price.disk_price
            region_info["trial_net_price"] = saler_price.net_price

            region_info["trial_package_memory_price"] = saler_price.memory_package_price
            region_info["trial_package_disk_price"] = saler_price.disk_package_price
            region_info["trial_package_net_price"] = saler_price.net_package_price
        except Exception:
            region_info["trial_memory_price"] = Decimal(0.0000)
            region_info["trial_disk_price"] = Decimal(0.0000)
            region_info["trial_net_price"] = Decimal(0.0000)
            region_info["trial_package_memory_price"] = Decimal(0.0000)
            region_info["trial_package_disk_price"] = Decimal(0.0000)
            region_info["trial_package_net_price"] = Decimal(0.0000)

        context = self.get_context()
        context.update({
            "region_name_list": list(region_name_map.keys()),
            "region": region_info
        })
        return TemplateResponse(request, "share/region_resource_price.html", context)

    def post(self, request, *args, **kwargs):
        region = request.POST.get("region", None)
        memory_price = request.POST.get("memory_price", None)
        disk_price = request.POST.get("disk_price", None)
        net_price = request.POST.get("net_price", None)

        provider = self.provider.provider_name
        try:
            provider_price = RegionResourceProviderPrice.objects.get(provider=provider, region=region)
        except Exception:
            provider_price = RegionResourceProviderPrice()
            provider_price.region = region
            provider_price.provider = provider

        provider_price.memory_price = Decimal(memory_price) or provider_price.memory_price
        provider_price.disk_price = Decimal(disk_price) or provider_price.disk_price
        provider_price.net_price = Decimal(net_price) or provider_price.net_price
        provider_price.save()

        # 发布这个价格, 根据数据中心定价按照一定的规则生成平台零售价
        trial_price_list = list(RegionResourceSalesPrice.objects.filter(region=region))
        if trial_price_list:
            for trial_price in trial_price_list:
                trial_price.memory_price, trial_price.memory_package_price = self.get_trial_price("memory",
                                                                                                  provider_price.memory_price)
                trial_price.disk_price, trial_price.disk_package_price = self.get_trial_price("disk",
                                                                                              provider_price.disk_price)
                trial_price.net_price, trial_price.net_package_price = self.get_trial_price("net",
                                                                                            provider_price.net_price)
                trial_price.save()
        else:
            self.save_region_resource_sales_price(provider_price, "goodrain", "goodrain")

        return self.redirect_to("/share/region/price/?region={}".format(region))

    def save_region_resource_sales_price(self, provider_price, saler, saler_channel):
        trial_price = RegionResourceSalesPrice()
        trial_price.region = provider_price.region
        trial_price.provider = provider_price.provider
        trial_price.saler = saler
        trial_price.saler_channel = saler_channel
        trial_price.memory_price, trial_price.memory_package_price = self.get_trial_price("memory",
                                                                                          provider_price.memory_price)
        trial_price.disk_price, trial_price.disk_package_price = self.get_trial_price("disk", provider_price.disk_price)
        trial_price.net_price, trial_price.net_package_price = self.get_trial_price("net", provider_price.net_price)
        trial_price.save()

    @staticmethod
    def get_trial_price(resource, provider_base_price):
        depreciation_rate = PRICE_BASE.get(resource).get("depreciation")
        used_profit_rate = PRICE_BASE.get(resource).get("used_profit")
        package_profit_rate = PRICE_BASE.get(resource).get("package_profit")
        used_trial_price = provider_base_price * depreciation_rate * used_profit_rate
        package_trial_price = provider_base_price * depreciation_rate * package_profit_rate

        return used_trial_price, package_trial_price


class RegionResourceConsumeView(ShareBaseView):
    """数据中心消费统计报表"""

    def get(self, request, *args, **kwargs):
        if not self.regions:
            return self.redirect_to("/share/")

        region = request.GET.get("region")
        if region not in self.regions:
            region = self.regions.keys()[0]

        querymonth = request.GET.get("date", None)
        logger.info("input: {}, region:{}".format(querymonth, region))

        if querymonth:
            month_date = dt.strptime(querymonth, "%Y-%m")
        else:
            now = dt.now()
            month_date = dt(now.year, now.month, 1, 0, 0, 0) - clzdt.timedelta(days=1)

        querymonth = month_date.strftime("%Y-%m")
        now = dt.now()
        if month_date.year == now.year and month_date.month == now.month:
            context = self.get_context()
            context.update({
                "region": region,
                "report": False,
                "query_month": month_date.strftime("%Y-%m"),
            })
            return TemplateResponse(request, "share/region_resource_consume.html", context)

        provider_name = self.provider.provider_name
        record_list = list(
            RegionResourceProviderSettle.objects.filter(provider=provider_name, region=region, date=querymonth))
        if record_list:
            record = record_list[0]
            context = self.get_context()
            context.update({
                "region": record.region,
                "report": True,
                "total_used_tenant": record.used_tenant,
                "total_tenant_memory": round(record.used_memory / 1024.0, 4),
                "total_tenant_disk": round(record.used_memory / 1024.0, 4),
                "total_tenant_net": round(record.used_net / 1024.0, 4),

                "total_package_tenant": record.package_tenant,
                "total_package_day": record.package_day,
                "total_over_memory": round(record.package_memory / 1024, 4),
                "total_over_disk": round(record.package_disk / 1024, 4),
                "total_over_net": round(record.package_net / 1024, 4),

                "query_month": month_date.strftime("%Y-%m"),
            })
            return TemplateResponse(request, "share/region_resource_consume.html", context)

        start_date = dt(month_date.year, month_date.month, 1, 0, 0, 0)
        last_day = calendar.monthrange(month_date.year, month_date.month)[1]
        end_date = dt(month_date.year, month_date.month, last_day, 0, 0, 0) + clzdt.timedelta(
            days=1)

        logger.info("query from {} to {}".format(start_date, end_date))
        start_timestamp = int(time.mktime(start_date.timetuple()))
        end_timestamp = int(time.mktime(end_date.timetuple()))

        conn = MySQLConn()
        datas = conn.fetch_all("""
                        SELECT tenant_id, statistics_time, SUM(memory) as memory, SUM(disk) as disk, SUM(net) as net
                        FROM region_resource_consume
                        WHERE region='{}' and statistics_time > {} and statistics_time <= {}
                        group by tenant_id, statistics_time
                    """.format(region, start_timestamp, end_timestamp))
        if not datas:
            return TemplateResponse(request, "share/region_resource_consume.html", self.get_context())

        logger.info("date len : {}".format(len(datas)))
        package_pay_mode = self.get_pacakge_pay_model(region, start_date, end_date)
        logger.info("model len : {}".format(len(package_pay_mode)))
        logger.info(package_pay_mode)

        tenant_consume = dict()
        for tenant_id, statistics_time, memory, disk, net in datas:
            if tenant_id not in tenant_consume:
                init_data = dict()
                init_data["tenant_id"] = tenant_id
                init_data["memory"] = 0
                init_data["disk"] = 0
                init_data["net"] = 0
                init_data["fee"] = 0
                init_data["over_memory"] = 0
                init_data["over_disk"] = 0
                init_data["over_net"] = 0
                init_data["over_fee"] = 0
                init_data["package_day"] = 0
                init_data["real_money"] = Decimal(0)
                init_data["package_money"] = Decimal(0)
                tenant_consume[tenant_id] = init_data

            # 如果这是一个包月用户
            data = tenant_consume[tenant_id]
            if tenant_id in package_pay_mode:
                over_memory, over_disk, over_net = self.cal_pay_month_data(tenant_id, region, statistics_time,
                                                                           package_pay_mode, int(memory),
                                                                           int(disk), int(net))
                data["over_memory"] += over_memory
                data["over_disk"] += over_disk
                data["over_net"] += over_net
            else:
                data["memory"] += int(memory)
                data["disk"] += int(disk)
                data["net"] += int(net)

        # 计算每个租户的费用
        region_sales_price = get_object_or_404(RegionResourceSalesPrice, region=region)
        for tenant_id, consume_detail in tenant_consume.items():
            # 全部按需费用
            consume_detail["fee"] = self.calculate_fee(consume_detail["memory"], consume_detail["disk"],
                                                       consume_detail["net"], region_sales_price)
            consume_detail["over_fee"] = self.calculate_fee(consume_detail["over_memory"], consume_detail["over_disk"],
                                                            consume_detail["over_net"], region_sales_price)
            consume_detail["real_money"] = consume_detail["fee"] + consume_detail["over_fee"]
            # 包月费用
            package_fee, package_day = self.cal_pay_month_fee(tenant_id, region, package_pay_mode, start_date, end_date)
            consume_detail["package_money"] = Decimal.from_float(package_fee)
            consume_detail["package_day"] = package_day

        # 关联租户名称
        # tenant_id_list = []
        # for tenant_id in tenant_consume.keys():
        #     tenant_id_list.append("'{}'".format(tenant_id))
        # tenant_id_str = ",".join(tenant_id_list)
        # conn = MySQLConn()
        # tenant_names = conn.fetch_all("""
        #                     SELECT tenant_id, tenant_name FROM tenant_info WHERE tenant_id in ({})
        #                 """.format(tenant_id_str))
        # tenant_name_map = {tenant_id: tenant_name for tenant_id, tenant_name in tenant_names}
        # for tenant_id, consume_detail in tenant_consume.items():
        #     consume_detail["tenant_name"] = tenant_name_map.get(tenant_id)

        # 统计所有租户的总消耗
        total_tenant_memory = 0
        total_tenant_net = 0
        total_tenant_disk = 0

        total_over_memory = 0
        total_over_net = 0
        total_over_disk = 0
        total_package_day = 0

        total_real_money = Decimal(0)
        total_package_money = Decimal(0)

        for tenant_id, consume_detail in tenant_consume.items():
            total_tenant_memory += consume_detail["memory"]
            total_tenant_disk += consume_detail["disk"]
            total_tenant_net += consume_detail["net"]

            total_over_memory += consume_detail["over_memory"]
            total_over_disk += consume_detail["over_disk"]
            total_over_net += consume_detail["over_net"]
            total_package_day += consume_detail["package_day"]

            total_real_money += consume_detail["real_money"]
            total_package_money += consume_detail["package_money"]
            logger.debug(consume_detail)

        total_money = total_package_money + total_real_money

        record = RegionResourceProviderSettle()
        record.date = querymonth
        record.provider = provider_name
        record.region = region
        record.used_tenant = len(tenant_consume)
        record.used_memory = total_tenant_memory
        record.used_disk = total_tenant_disk
        record.used_net = total_tenant_net
        record.package_tenant = len(package_pay_mode)
        record.package_day = total_package_day
        record.package_memory = total_over_memory
        record.package_disk = total_over_disk
        record.package_net = total_over_net
        record.save()

        context = self.get_context()
        context.update({
            "region": region,
            "report": True,
            "total_used_tenant": len(tenant_consume),
            "total_tenant_memory": round(total_tenant_memory / 1024.0, 4),
            "total_tenant_disk": round(total_tenant_disk / 1024.0, 4),
            "total_tenant_net": round(total_tenant_net / 1024.0, 4),

            "total_package_tenant": len(package_pay_mode),
            "total_package_day": total_package_day,
            "total_over_memory": round(total_over_memory / 1024, 4),
            "total_over_disk": round(total_over_disk / 1024, 4),
            "total_over_net": round(total_over_net / 1024, 4),

            "query_month": month_date.strftime("%Y-%m"),
        })
        return TemplateResponse(request, "share/region_resource_consume.html", context)

    # 获得在统计周期内包月付费记录
    def get_pacakge_pay_model(self, region_name, static_start_date, static_end_date):
        conn = MySQLConn()
        pay_model_data = conn.fetch_all("""
                select  tenant_id, buy_start_time, buy_end_time, buy_money, buy_memory, buy_disk, buy_net
                from    tenant_region_pay_model
                where   region_name = '{}'
            """.format(region_name))

        data = dict()
        for tenant_id, buy_start_time, buy_end_time, buy_money, buy_memory, buy_disk, buy_net in pay_model_data:
            if buy_start_time >= static_end_date or buy_end_time <= static_start_date:
                continue

            if tenant_id not in data:
                data[tenant_id] = []

            temdata = dict()
            temdata["buy_money"] = buy_money
            temdata["buy_memory"] = buy_memory
            temdata["buy_disk"] = buy_disk
            temdata["buy_net"] = buy_net
            temdata["buy_start_time"] = buy_start_time
            temdata["buy_end_time"] = buy_end_time

            data[tenant_id].append(temdata)
        return data

    def cal_pay_month_data(self, tenant_id, region, end_time, package_pay_mode, region_cost_memory, region_cost_disk,
                           region_cost_net):
        real_memory = region_cost_memory
        real_net = region_cost_net
        real_disk = region_cost_disk

        if tenant_id in package_pay_mode:
            buy_disk = 0
            buy_net = 0
            buy_memory = 0
            tenant_model_data = package_pay_mode.get(tenant_id)
            for model_data in tenant_model_data:
                buy_start_timestamp = int(time.mktime(model_data["buy_start_time"].timetuple()))
                buy_end_timestamp = int(time.mktime(model_data["buy_end_time"].timetuple()))
                if buy_start_timestamp < end_time < buy_end_timestamp:
                    buy_disk += model_data["buy_disk"]
                    buy_net += model_data["buy_net"]
                    buy_memory += model_data["buy_memory"]

            buy_disk *= 1024
            real_disk = region_cost_disk - buy_disk if region_cost_disk > buy_disk else 0

            buy_net *= 1024
            real_net = region_cost_net - buy_net if region_cost_net > buy_net else 0

            buy_memory *= 1024
            real_memory = region_cost_memory - buy_memory if region_cost_memory > buy_memory else 0

            # logger.info("{} at {}".format(tenant_id, end_time))
            # logger.info("memory: {:>8} - {:>8} = {:>8}".format(region_cost_memory, buy_memory, over_memory))
            # logger.info("disk  : {:>8} - {:>8} = {:>8}".format(region_cost_disk, buy_disk, over_disk))
            # logger.info("net   : {:>8} - {:>8} = {:>8}".format(region_cost_net, buy_net, over_net))

        logger.info("{} - {} Mem:{}, Disk:{}, Net:{}".format(tenant_id, end_time, real_memory, real_disk, real_net))
        return real_memory, real_disk, real_net

    def cal_pay_month_fee(self, tenant_id, region_name, package_pay_mode, static_start_date, static_end_date):
        if tenant_id not in package_pay_mode:
            return 0.00, 0

        real_cost_money = 0.00
        total_consume_days = 0
        for pay_mode in package_pay_mode.get(tenant_id):
            buy_start_date = pay_mode['buy_start_time']
            buy_end_date = pay_mode['buy_end_time']
            buy_money = pay_mode['buy_money']
            logger.info("{}: [{} - {}], cost:{}".format(tenant_id, buy_start_date, buy_end_date, buy_money))

            single_price = float(str(buy_money)) / (buy_end_date - buy_start_date).days
            consume_days = 0
            if buy_end_date <= static_start_date or buy_start_date >= static_end_date:
                continue

            # 购买周期完全包含统计周期
            if buy_start_date <= static_start_date and buy_end_date >= static_end_date:
                consume_days = (static_end_date - static_start_date).days
            # 购买周期完全在统计周期之内, 则以天计算
            elif buy_start_date > static_start_date and buy_end_date < static_end_date:
                consume_days = (buy_end_date - buy_start_date).days
            elif buy_start_date <= static_start_date and buy_end_date < static_end_date:
                consume_days = (buy_end_date - static_start_date).days
            elif buy_start_date > static_start_date and buy_end_date >= static_end_date:
                consume_days = (static_end_date - buy_start_date).days
            package_cost = single_price * consume_days

            real_cost_money += package_cost
            total_consume_days += consume_days

            logger.info("{} * {} = {}, total = {}".format(single_price, consume_days, package_cost, real_cost_money))

        return round(real_cost_money, 2), total_consume_days

    def calculate_fee(self, region_total_memory, region_total_disk, region_total_net, region_sales_price):
        total_money = Decimal(0)
        try:
            memory_fee = region_sales_price.memory_price * Decimal.from_float(region_total_memory / 1024.0)
            disk_fee = region_sales_price.disk_price * Decimal.from_float(region_total_disk / 1024.0)
            net_fee = region_sales_price.net_price * Decimal.from_float(region_total_net / 1024.0)

            total_money = memory_fee + disk_fee + net_fee
        except Exception as e:
            logger.exception("", e)

        return total_money


class RegionResourceSettleView(ShareBaseView):
    region_provider_manager = RegionProviderManager()

    def get(self, request, *args, **kwargs):
        querymonth = request.GET.get("date", None)
        if querymonth:
            month_date = dt.strptime(querymonth, "%Y-%m")
        else:
            now = dt.now()
            month_date = dt(now.year, now.month, 1, 0, 0, 0) - clzdt.timedelta(days=1)
        querymonth = month_date.strftime("%Y-%m")

        start_date = dt(month_date.year, month_date.month, 1, 0, 0, 0)
        last_day = calendar.monthrange(month_date.year, month_date.month)[1]
        end_date = dt(month_date.year, month_date.month, last_day, 0, 0, 0) + clzdt.timedelta(
            days=1)
        logger.info("query from {} to {}".format(start_date, end_date))

        provider = self.provider.provider_name
        provider_settle_list = list(RegionResourceProviderSettle.objects.filter(provider=provider, date=querymonth))

        region_settle_list = []
        for provider_settle in provider_settle_list:
            total_memory = provider_settle.used_memory + provider_settle.package_memory
            total_net = provider_settle.used_net + provider_settle.package_net
            total_disk = provider_settle.used_disk + provider_settle.package_disk

            total_resource_fee = self.cal_region_resource_fee(provider_settle.region, total_memory, total_disk,
                                                              total_net)
            total_package_fee = self.cal_region_pacakge_fee(provider_settle.region, start_date, end_date)

            total_fee = total_resource_fee + total_package_fee

            partner_rate = Decimal(0.5)
            settle_fee = total_fee * partner_rate

            region_settle = dict()
            region_settle["region"] = provider_settle.region
            region_settle["total_memory"] = total_memory / 1024
            region_settle["total_net"] = total_net / 1024
            region_settle["total_disk"] = total_disk / 1024
            region_settle["total_resource_fee"] = total_resource_fee.quantize(Decimal('0.00'))
            region_settle["total_package_fee"] = total_package_fee.quantize(Decimal('0.00'))
            region_settle["total_fee"] = total_fee.quantize(Decimal('0.00'))
            region_settle["partner_rate"] = partner_rate
            region_settle["settle_fee"] = settle_fee.quantize(Decimal('0.00'))
            region_settle_list.append(region_settle)

        context = self.get_context()
        context.update({
            "region_settle_list": region_settle_list,
            "query_month": querymonth,
        })
        return TemplateResponse(request, "share/region_resource_settle.html", context)

    def cal_region_resource_fee(self, region_name, memroy, disk, net):
        total_fee = Decimal(0)
        try:
            region_sales_price = self.region_provider_manager.get_work_region_by_name(region_name)
            memory_fee = region_sales_price.memory_price * Decimal.from_float(memroy / 1024.0)
            disk_fee = region_sales_price.disk_price * Decimal.from_float(disk / 1024.0)
            net_fee = region_sales_price.net_price * Decimal.from_float(net / 1024.0)

            total_fee = memory_fee + disk_fee + net_fee
        except Exception as e:
            logger.exception("", e)

        return total_fee

    def cal_region_pacakge_fee(self, region_name, static_start_date, static_end_date):
        conn = MySQLConn()
        pay_model_data = conn.fetch_all("""
                    select  tenant_id, buy_start_time, buy_end_time, buy_money
                    from    tenant_region_pay_model
                    where   region_name = '{}'
                """.format(region_name))

        real_cost_money = 0.00
        for tenant_id, buy_start_time, buy_end_time, buy_money in pay_model_data:
            buy_start_date = buy_start_time
            buy_end_date = buy_end_time

            logger.info("{}: [{} - {}], cost:{}".format(tenant_id, buy_start_date, buy_end_date, buy_money))

            if buy_start_date >= static_end_date or buy_end_date <= static_start_date:
                continue

            single_price = float(str(buy_money)) / (buy_end_date - buy_start_date).days
            consume_days = 0
            if buy_end_date <= static_start_date or buy_start_date >= static_end_date:
                continue

            # 购买周期完全包含统计周期
            if buy_start_date <= static_start_date and buy_end_date >= static_end_date:
                consume_days = (static_end_date - static_start_date).days
            # 购买周期完全在统计周期之内, 则以天计算
            elif buy_start_date > static_start_date and buy_end_date < static_end_date:
                consume_days = (buy_end_date - buy_start_date).days
            elif buy_start_date <= static_start_date and buy_end_date < static_end_date:
                consume_days = (buy_end_date - static_start_date).days
            elif buy_start_date > static_start_date and buy_end_date >= static_end_date:
                consume_days = (static_end_date - buy_start_date).days
            package_cost = single_price * consume_days

            real_cost_money += package_cost
            logger.info("{} * {} = {}, total = {}".format(single_price, consume_days, package_cost, real_cost_money))

        return Decimal.from_float(real_cost_money)


class MySQLConn:
    def __init__(self):
        self.mysql_info = {}
        self.mysql_info["host"] = "127.0.0.1"
        self.mysql_info["port"] = 3307
        self.mysql_info["user"] = "writer"
        self.mysql_info["passwd"] = "a5bzkEP3bjc"
        self.mysql_info["db"] = "goodrain"

    def get_connection(self):
        return MySQLdb.connect(host=self.mysql_info["host"], port=self.mysql_info["port"],
                               user=self.mysql_info["user"], passwd=self.mysql_info["passwd"],
                               db=self.mysql_info["db"])

    def close_connection(self, cur, connection):
        if cur:
            cur.close()
        if connection:
            connection.close()

    def insert_batch(self, sql, args):
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.executemany(sql, args)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.exception("", e)
        finally:
            self.close_connection(cur, conn)

    def fetch_all(self, sql):
        data = None
        try:
            logger.info(sql)
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(sql)
            data = cur.fetchall()
        except Exception as e:
            logger.exception("", e)
        finally:
            self.close_connection(cur, conn)
        return data

    def fetch_one(self, sql):
        data = None
        try:
            logger.info(sql)
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(sql)
            data = cur.fetchone()
        except Exception as e:
            logger.exception("", e)
        finally:
            self.close_connection(cur, conn)
        return data


class TeamDataFix(ShareBaseView):
    """
    处理云帮领域模型从 团队-用户模型 变更到 企业-团队-用户 模型的数据一致性处理
    """

    def get(self, request, *args, **kwargs):
        if request.GET.get('all'):
            tenants = Tenants.objects.all()
        else:
            tenants = Tenants.objects.filter(tenant_id=request.GET.get('tenant_id'))

        logger.info('prpared tenant: %s' % tenants.count())
        # 将数据库中现有的租户信息作为团队复制一份到团队表中
        for tenant in tenants:
            logger.info('-' * 30)
            logger.info('tenant_ID: %s' % tenant.ID)
            logger.info('tenant_id: %s' % tenant.tenant_id)
            logger.info('tenant_name: %s' % tenant.tenant_name)

            if tenant.enterprise_id:
                logger.info('tenant enterprise existed, ignore.')
                continue

            try:
                enterprise = TenantEnterprise.objects.get(enterprise_id=tenant.tenant_id)
            except TenantEnterprise.DoesNotExist:
                enterprise = TenantEnterprise()
                enterprise.enterprise_id = tenant.tenant_id
                enterprise.enterprise_name = tenant.tenant_name
                enterprise.enterprise_alias = tenant.tenant_name
                enterprise.is_active = 1
                enterprise.save()
                logger.info('create enterprise: %s' % enterprise.ID)

            # 将之前的团队权限表中填充团队id信息
            perms = PermRelTenant.objects.filter(tenant_id=tenant.ID, enterprise_id=0)
            for perm in perms:
                perm.enterprise_id = enterprise.ID
                perm.save()
                logger.info('update tenant_perms.enterprise_id: %s' % enterprise.ID)

            # 将之前开通的数据中心信息冗余一份到tenant_region新增字段中
            tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, enterprise_id='')
            for tr in tenant_regions:
                tr.enterprise_id = enterprise.enterprise_id
                tr.region_tenant_name = tenant.tenant_name
                tr.region_tenant_id = tenant.tenant_id
                tr.region_scope = 'public'
                tr.save()
                logger.info('update tenant_region[%s]: %s' % (tr.region_name, tr.enterprise_id))

            # 将tenant关联到企业
            tenant.enterprise_id = enterprise.enterprise_id
            tenant.save()
            logger.info('update tenant.enterprise_id: %s' % enterprise.enterprise_id)

        return JsonResponse(data={'message': 'ok'})


class TeamCreate(ShareBaseView):
    """
    处理云帮领域模型从 团队-用户模型 变更到 企业-团队-用户 模型的数据一致性处理
    """

    def get(self, request, *args, **kwargs):
        user_id = request.GET.get('uid')
        tenant_name = request.GET.get('tenant_name')
        region_names = request.GET.get('region')
        enterprise_id = request.GET.get('eid')
        action = request.GET.get('action')
        if action == 'del':
            user_svc.delete_tenant(user_id)
            return JsonResponse(data={'message': 'ok'})
        else:
            regions = region_names.split(',') if region_names else []
            try:
                tenant = enterprise_svc.create_and_init_tenant(user_id, tenant_name, regions, enterprise_id)
                return JsonResponse(data={'message': 'ok', 'data': tenant.to_dict()})
            except Exception as e:
                logger.exception(e)
                return JsonResponse(data={'message': e.message})
