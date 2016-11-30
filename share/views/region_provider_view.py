# -*- coding: utf8 -*-
import logging

from base_view import ShareBaseView
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from share.models.main import *
from datetime import datetime as dt
import datetime as clzdt
import calendar
import time
from decimal import Decimal
import json
import MySQLdb


logger = logging.getLogger('default')


class RegionOverviewView(ShareBaseView):
    def get(self, request, *args, **kwargs):
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
                trial_price.memory_price, trial_price.memory_package_price = self.get_trial_price(provider_price.memory_price)
                trial_price.disk_price, trial_price.disk_package_price = self.get_trial_price(provider_price.disk_price)
                trial_price.net_price, trial_price.net_package_price = self.get_trial_price(provider_price.net_price)
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
        trial_price.memory_price, trial_price.memory_package_price = self.get_trial_price(provider_price.memory_price)
        trial_price.disk_price, trial_price.disk_package_price = self.get_trial_price(provider_price.disk_price)
        trial_price.net_price, trial_price.net_package_price = self.get_trial_price(provider_price.net_price)
        trial_price.save()

    @staticmethod
    def get_trial_price(provider_base_price):
        depreciation_rate = Decimal(1.1)
        used_profit_rate = Decimal(6)
        package_profit_rate = Decimal(2)
        used_trial_price = provider_base_price * depreciation_rate * used_profit_rate
        package_trial_price = provider_base_price * depreciation_rate * package_profit_rate

        return used_trial_price, package_trial_price


class RegionResourceConsumeView(ShareBaseView):
    """数据中心消费统计报表"""
    RULE = '''
        {
            "aws-jp-1":{
                "company":{"disk":0.0236994219653179,"net":1.286127167630058,"memory_money":0.692,"disk_money":0.0164,"net_money":0.89}
            },
            "ali-sh":{
                "company":{"disk":0.0594202898550725,"net":2.898550724637681,"memory_money":0.276,"disk_money":0.0164,"net_money":0.8}
            },
            "xunda-bj":{
                "company":{"disk":0.05967741935483871,"net":3.2258064516129035,"memory_money":0.248,"disk_money":0.0148,"net_money":0.8}
            }
        }
        '''

    def get(self, request, *args, **kwargs):
        querymonth = request.GET.get("date", None)
        if querymonth:
            month_date = dt.strptime(querymonth, "%Y-%m")
        else:
            now = dt.now()
            month_date = dt(now.year, now.month, 1, 0, 0, 0) - clzdt.timedelta(days=1)

        region = request.GET.get("region", "xunda-bj")
        logger.info("input: {}, region:{}".format(querymonth, region))

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
        pay_mode = self.get_pay_model(region)
        logger.info("model len : {}".format(len(pay_mode)))
        logger.info(pay_mode)

        tenant_consume = {}
        for tenant_id, statistics_time, memory, disk, net in datas:
            if tenant_id not in tenant_consume:
                init_data = dict()
                init_data["tenant_id"] = tenant_id
                init_data["memory"] = 0
                init_data["disk"] = 0
                init_data["net"] = 0
                init_data["real_money"] = 0.00
                init_data["package_money"] = 0.00
                tenant_consume[tenant_id] = init_data

            fee_memory, fee_disk, fee_net = self.cal_pay_month_data(tenant_id, region, statistics_time, pay_mode, int(memory),
                                                              int(disk), int(net))

            data = tenant_consume[tenant_id]
            data["memory"] += fee_memory
            data["disk"] += fee_disk
            data["net"] += fee_net

        # 计算每个租户的费用
        region_sales_price = get_object_or_404(RegionResourceSalesPrice, region=region)
        for tenant_id, consume_detail in tenant_consume.items():
            # 全部按需费用
            consume_detail["real_money"] = self.calculate_fee(consume_detail["memory"],
                                                              consume_detail["disk"],
                                                              consume_detail["net"],
                                                              region_sales_price)
            # 包月费用
            consume_detail["package_money"] = self.cal_pay_month_fee(tenant_id, region, pay_mode, start_date, end_date)

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

        total_real_money = Decimal(0)
        total_package_money = Decimal(0)

        for tenant_id, consume_detail in tenant_consume.items():
            total_tenant_memory += consume_detail["memory"]
            total_tenant_disk += consume_detail["disk"]
            total_tenant_net += consume_detail["net"]

            total_real_money += consume_detail["real_money"]
            total_package_money += consume_detail["package_money"]

        total_money = total_package_money + total_real_money
        context = self.get_context()
        context.update({
            "region": region,
            "total_tenant_memory": int(total_tenant_memory),
            "total_tenant_disk": int(total_tenant_disk),
            "total_tenant_net": int(total_tenant_net),
            "total_real_money": total_real_money.quantize(Decimal('0.00')),
            "total_package_money": total_package_money.quantize(Decimal('0.00')),
            "total_money": total_money,
            "query_month": month_date.strftime("%Y-%m"),
        })
        return TemplateResponse(request, "share/region_resource_consume.html", context)

    def get_pay_model(self, region_name):
        conn = MySQLConn()
        pay_model_data = conn.fetch_all("""
                select tenant_id, buy_memory, buy_disk, buy_net, buy_start_time, buy_end_time
                from tenant_region_pay_model
                where region_name = '{}'
            """.format(region_name))

        data = {}
        for tenant_id, buy_memory, buy_disk, buy_net, buy_start_time, buy_end_time in pay_model_data:
            if tenant_id not in data:
                data[tenant_id] = []

            temdata = dict()
            temdata["buy_memory"] = buy_memory
            temdata["buy_disk"] = buy_disk
            temdata["buy_net"] = buy_net
            temdata["buy_start_time"] = buy_start_time
            temdata["buy_end_time"] = buy_end_time
            data[tenant_id].append(temdata)
        return data

    def cal_pay_month_data(self, tenant_id, region, end_time, payModelData, region_cost_memory, region_cost_disk,
                           region_cost_net):
        real_memory = region_cost_memory
        real_net = region_cost_net
        real_disk = region_cost_disk

        if tenant_id in payModelData:
            buy_disk = 0
            buy_net = 0
            buy_memory = 0
            tenant_model_data = payModelData.get(tenant_id)
            for model_data in tenant_model_data:
                buy_start_timestamp = int(time.mktime(model_data["buy_start_time"].timetuple()))
                buy_end_timestamp = int(time.mktime(model_data["buy_end_time"].timetuple()))
                if buy_start_timestamp < end_time < buy_end_timestamp:
                    buy_disk += model_data["buy_disk"]
                    buy_net += model_data["buy_net"]
                    buy_memory += model_data["buy_memory"]

            buy_disk = float(buy_disk * 1024)
            if region_cost_disk > buy_disk:
                real_disk = region_cost_disk - buy_disk

            buy_net = float(buy_net * 1024)
            if region_cost_net > buy_net:
                real_net = region_cost_net - buy_net

            buy_memory = float(buy_memory * 1024)
            if region_cost_memory > buy_memory:
                real_memory = region_cost_memory - buy_memory
            # logger.info("{} at {}".format(tenant_id, end_time))
            # logger.info("memory: {:>8} - {:>8} = {:>8}".format(region_cost_memory, buy_memory, over_memory))
            # logger.info("disk  : {:>8} - {:>8} = {:>8}".format(region_cost_disk, buy_disk, over_disk))
            # logger.info("net   : {:>8} - {:>8} = {:>8}".format(region_cost_net, buy_net, over_net))


        logger.info("{} - {} used Mem:{}, Disk:{}, Net:{}".format(tenant_id, end_time, real_memory, real_disk, real_net))
        return int(round(real_memory, 0)), int(round(real_disk, 0)), int(round(real_net, 0))

    def cal_pay_month_fee(self, tenant_id, region_name, pay_mode, static_start_date, static_end_date):
        if tenant_id not in pay_mode:
            return 0.00

        conn = MySQLConn()
        pay_model_data = conn.fetch_all("""
                    select tenant_id, region_name, pay_model, buy_period, buy_start_time, buy_end_time, buy_money
                    from tenant_region_pay_model
                    where region_name = '{}' and tenant_id = '{}'
                """.format(region_name, tenant_id))

        if not pay_model_data:
            return 0.00

        real_cost_money = 0.00
        for tenant_id, region_name, pay_model, buy_period, buy_start_time, buy_end_time, buy_money in pay_model_data:
            buy_start_date = buy_start_time
            buy_end_date = buy_end_time
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
            logger.info("{} * {} = {}, total = {}".format(single_price, consume_days, package_cost, real_cost_money))

        return round(real_cost_money, 2)

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