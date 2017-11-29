# -*- coding: utf8 -*-
import datetime
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from share.manager.region_provier import RegionProviderManager
from www.models import TenantRegionPayModel, ServiceAttachInfo, ServiceFeeBill
from www.models.activity import TenantActivity
from www.models.main import TenantServiceInfo
from www.region import RegionInfo
from www.utils import sn
from www.views import AuthedView, LeftSideBarMixin, JsonResponse

logger = logging.getLogger('default')
rpmManager = RegionProviderManager()


class Recharging(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        context["myFinanceRecharge"] = "active"
        context["myFinanceStatus"] = "active"

        context["tenant"] = self.tenant

        return TemplateResponse(self.request, "www/recharge.html", context)


class AccountBill(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        try:
            user_id = self.user.pk
            # context["tenantFeeBill"] = tenantFeeBill
            context["myFinanceBill"] = "active"
            context["myFinanceStatus"] = "active"
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/account_bill.html", context)


class Account(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        context["myFinanceAccount"] = "active"
        context["myFinanceStatus"] = "active"
        return TemplateResponse(self.request, "www/tradedetails.html", context)


class PayModelView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenant"] = self.tenant
        context["tenantName"] = self.tenantName
        context["region_name"] = self.response_region
        context["myPayModelstatus"] = "active"
        context["myFinanceStatus"] = "active"
        context["memoryList"] = [1, 2, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500,
                                 600, 700, 1000]
        context["diskList"] = [0, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        context["netList"] = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        context["periodList"] = [(1, "1月"), (2, "2月"), (3, "3月"), (4, "4月"), (5, "5月"), (6, "6月"), (7, "7月"), (8, "8月"),
                                 (9, "9月"), (12, "1年"), (24, "2年")]
        tenantBuyPayModels = TenantRegionPayModel.objects.filter(tenant_id=self.tenant.tenant_id)
        context["tenantBuyPayModels"] = tenantBuyPayModels
        RegionMap = {}
        for item in RegionInfo.region_list:
            if item["enable"]:
                RegionMap[item["name"]] = item["label"]
        ta_num = TenantActivity.objects.filter(tenant_id=self.tenant.tenant_id).count()
        if ta_num > 0:
            RegionMap.clear()
            RegionMap["xunda-bj"] = u'\u8fc5\u8fbe\u4e91[\u5317\u4eac]'
        PeriodMap = {"hour": u"小时", "month": u"月", "year": u"年"}
        context["RegionMap"] = RegionMap
        context["PeriodMap"] = PeriodMap
        context["REGION_FEE_RULE"] = settings.REGION_FEE_RULE
        return TemplateResponse(self.request, "www/paymodel.html", context)


class AssistantView(LeftSideBarMixin, AuthedView):
    """获取云帮自助授权信息"""

    def get(self, request, *args, **kwargs):
        context = self.get_context()
        enterprise = sn.instance.cloud_assistant
        context["enterprise"] = enterprise

        return TemplateResponse(self.request, "www/ser.html", context)


class RegionsServiceCostView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context["myServiceCost"] = "active"
        context["myFinanceStatus"] = "active"
        return TemplateResponse(self.request, "www/service_cost.html", context)


class ServiceBatchRenewView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js','www/js/jquery.cookie.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context["batchRenew"] = "active"
        context["myFinanceStatus"] = "active"
        # now = datetime.datetime.now()
        # tenant_id = self.tenant.tenant_id

        # regionBo = rpmManager.get_work_region_by_name(self.response_region)
        # pre_paid_memory_price = regionBo.memory_package_price
        # pre_paid_disk_price = regionBo.disk_package_price
        #
        # service_list = TenantServiceInfo.objects.filter(tenant_id=tenant_id,
        #                                                 service_region=self.response_region).values("service_id",
        #                                                                                             "service_cname")
        # service_id_list = [elem["service_id"] for elem in service_list]
        # id_name_map = {elem["service_id"]: elem["service_cname"] for elem in service_list}
        # attach_info_list = ServiceAttachInfo.objects.filter(service_id__in=service_id_list)
        # # 内存预付费
        # prepay_memory = Q(memory_pay_method="prepaid")
        # # 磁盘预付费
        # prepay_disk = Q(disk_pay_method="prepaid")
        # # 内存后付费
        # postpay_memory = Q(memory_pay_method="postpaid")
        # # 磁盘后付费
        # postpay_disk = Q(disk_pay_method="postpaid")
        # # 付费期内
        # during_payment = Q(buy_end_time__gt=now)
        # # 包月期间应用
        # prepay_services = attach_info_list.filter((prepay_memory | prepay_disk) & during_payment)
        # # 非包月应用
        # postpay_services = attach_info_list.filter(postpay_memory & postpay_disk)
        #
        # prepay_services = list(prepay_services)
        # service_unit_fee_map = {}
        # for ps in prepay_services:
        #     need_money = Decimal(0)
        #     if ps.memory_pay_method == "prepaid":
        #         memory_fee = (int(ps.min_memory) * int(ps.min_node)) / 1024.0 * float(pre_paid_memory_price)
        #         need_money += Decimal(memory_fee)
        #     if ps.disk_pay_method == "prepaid":
        #         disk_fee = ps.disk / 1024.0 * float(pre_paid_disk_price)
        #         need_money += Decimal(disk_fee)
        #     service_unit_fee_map[ps.service_id] = need_money
        # context["service_unit_fee_map"] = service_unit_fee_map
        # context["prepay_services"] = list(prepay_services)
        # context["postpay_services"] = list(postpay_services)
        # context["id_name_map"] = id_name_map
        # context["cur_balance"] = self.tenant.balance
        return TemplateResponse(self.request, "www/batch_renewal.html", context)

    @never_cache
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        result = {}
        sid = None
        try:
            regionBo = rpmManager.get_work_region_by_name(self.response_region)
            pre_paid_memory_price = regionBo.memory_package_price
            pre_paid_disk_price = regionBo.disk_package_price

            json_data = request.POST.get("data", "")
            if not json_data:
                result["ok"] = False
                result["status"] = "params_error"
                result['msg'] = "参数错误"
                return JsonResponse(result, status=400)

            data = json.loads(json_data)
            id_extendTime_map = {elem["service_id"]:elem["month_num"] for elem in data}
            service_id_list = id_extendTime_map.keys()
            renew_attach_infos = ServiceAttachInfo.objects.filter(service_id__in=service_id_list)
            renew_attach_infos = list(renew_attach_infos)
            total_money = Decimal(0)
            create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bills = []
            for ps in renew_attach_infos:
                renew_money = Decimal(0)
                if ps.memory_pay_method == "prepaid":
                    memory_fee = (int(ps.min_memory) * int(ps.min_node)) / 1024.0 * float(pre_paid_memory_price)
                    renew_money += Decimal(memory_fee)
                if ps.disk_pay_method == "prepaid":
                    disk_fee = ps.disk / 1024.0 * float(pre_paid_disk_price)
                    renew_money += Decimal(disk_fee)
                extend_time = id_extendTime_map.get(ps.service_id)
                service_renew_money = renew_money * 24 * int(extend_time) * 30

                bill = ServiceFeeBill(tenant_id=self.tenant.tenant_id,
                                      service_id=ps.service_id,
                                      prepaid_money=service_renew_money,
                                      pay_status="payed",
                                      cost_type="renew",
                                      node_memory=ps.min_memory,
                                      node_num=ps.min_node,
                                      disk=ps.disk,
                                      buy_period=int(extend_time)*24*30,
                                      create_time=create_time,
                                      pay_time=create_time)
                bills.append(bill)
                total_money += service_renew_money
            total_money = Decimal(str(round(total_money, 2)))
            # 如果钱不够
            if total_money > self.tenant.balance:
                result["ok"] = False
                result["status"] = "not_enough"
                result['msg'] = "账户余额不足以批量续费"
                return JsonResponse(result, status=200)
            sid = transaction.savepoint()
            ServiceFeeBill.objects.bulk_create(bills)
            for ps in renew_attach_infos:
                extend_time = int(id_extendTime_map.get(ps.service_id))
                ps.buy_end_time = ps.buy_end_time + datetime.timedelta(
                    days=extend_time * 30)
                ps.save()
            self.tenant.balance -= total_money
            self.tenant.save()
            transaction.savepoint_commit(sid)
            result["ok"] = True
            result["status"] = "success"
            result['msg'] = "续费成功"

        except Exception as e:
            if sid:
                transaction.savepoint_rollback(sid)
            logger.exception(e)
            result["ok"] = False
            result["status"] = "internal_erro"
            result['msg'] = "系统异常"

        return JsonResponse(result, status=200)
