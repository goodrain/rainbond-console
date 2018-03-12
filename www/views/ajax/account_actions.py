# -*- coding: utf8 -*-
import datetime
import logging
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.http import JsonResponse
from django.template.response import TemplateResponse

from goodrain_web.tools import JuncheePaginator
from www.decorator import perm_required
from www.models import TenantFeeBill, TenantRecharge, TenantConsume, TenantRegionPayModel, Tenants, \
    ServiceConsume, TenantServiceInfo
from www.monitorservice.monitorhook import MonitorHook
from www.region import RegionInfo
from www.views import AuthedView

logger = logging.getLogger('default')
monitorhook = MonitorHook()

RechargeTypeMap = {"alipay": u"支付宝", "100send50": u"充100送10", "weixin100": u"微信注册送100", "rechargesend": u"充多少送多少", "offline": u"线下汇款"}


class AccountBill(AuthedView):

    @perm_required('tenant_account')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            tenant_id = self.tenant.tenant_id
            bill_title = request.POST["bill_title"]
            bill_type = request.POST["bill_type"]
            bill_address = request.POST["bill_address"]
            bill_phone = request.POST["bill_phone"]
            bill_money = request.POST["bill_money"]
            if bill_money is None or bill_money == "":
                data["status"] = "moneyError"
            tenantFeeBill = TenantFeeBill()
            tenantFeeBill.tenant_id = tenant_id
            tenantFeeBill.bill_title = bill_title
            tenantFeeBill.bill_type = bill_type
            tenantFeeBill.bill_address = bill_address
            tenantFeeBill.bill_phone = bill_phone
            tenantFeeBill.money = float(bill_money)
            tenantFeeBill.status = "approved"
            tenantFeeBill.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tenantFeeBill.save()
            data["status"] = "success"
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return JsonResponse(data, status=500)


class AccountRecharging(AuthedView):

    @perm_required('tenant_account')
    def post(self, request, *args, **kwargs):
        try:
            tenant_id = self.tenant.tenant_id
            action = request.POST["action"]
        except Exception as e:
            logger.exception(e)

    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        date_scope = request.GET.get("datescope", "7")
        per_page = request.GET.get("perpage", "10")
        page = request.GET.get("page", "1")
        context["date_scope"] = date_scope
        context["curpage"] = page
        context["per_page"] = per_page
        try:
            tenant_id = self.tenant.tenant_id
            diffDay = int(date_scope)
            if diffDay > 0:
                end = datetime.datetime.now()
                endTime = end.strftime("%Y-%m-%d %H:%M:%S")
                start = datetime.date.today() - datetime.timedelta(days=int(date_scope))
                startTime = start.strftime('%Y-%m-%d') + " 00:00:00"
                recharges = TenantRecharge.objects.filter(tenant_id=self.tenant.tenant_id, time__range=(startTime, endTime)).order_by("-time")
            else:
                recharges = TenantRecharge.objects.filter(tenant_id=self.tenant.tenant_id).order_by("-time")
            paginator = JuncheePaginator(recharges, int(per_page))
            tenantRecharges = paginator.page(int(page))
            context["rechargeTypeMap"] = RechargeTypeMap
            context["tenantRecharges"] = tenantRecharges
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/recharge-list.html", context)


class AccountQuery(AuthedView):

    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        date_scope = request.GET.get("datescope", "1")
        per_page = request.GET.get("perpage", "24")
        page = request.GET.get("page", "1")
        context["datescope"] = date_scope
        context["per_page"] = per_page
        try:
            tenant_id = self.tenant.tenant_id
            diffDay = int(date_scope)
            if diffDay > 0:
                end = datetime.datetime.now()
                endTime = end.strftime("%Y-%m-%d %H:%M:%S")
                start = datetime.date.today() - datetime.timedelta(days=int(date_scope))
                startTime = start.strftime('%Y-%m-%d') + " 00:00:00"
                recharges = TenantConsume.objects.filter(tenant_id=self.tenant.tenant_id, time__range=(startTime, endTime)).order_by("-ID")
            else:
                recharges = TenantConsume.objects.filter(tenant_id=self.tenant.tenant_id)
            paginator = JuncheePaginator(recharges, int(per_page))
            tenantConsumes = paginator.page(int(page))
            context["tenantConsumes"] = tenantConsumes
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/tradedetails-list.html", context)


class PayModelInfo(AuthedView):

    @perm_required('tenant_account')
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            tenant_id = self.tenant.tenant_id
            region_name = request.POST["region_name"]
            buy_memory = request.POST["buy_memory"]
            buy_disk = request.POST["buy_disk"]
            buy_net = 0
            buy_period = request.POST["buy_period"]
            action = request.POST["action"]
            regions = RegionInfo.region_names()
            period = int(buy_period)
            pay_model = "month"
            if period > 0 and regions.index(region_name) >= 0:
                feerule = settings.REGION_FEE_RULE[region_name]
                logger.debug(feerule)
                one1 = float(feerule["memory_money"]) * int(buy_memory)
                one2 = float(feerule["disk_money"]) * int(buy_disk)
                one3 = float(feerule["net_money"]) * int(buy_net)
                onehour = one1 + one2
                buy_money = 0
                tmp_perod = period
                if period >= 12:
                    pay_model = "year"
                    buy_money = onehour * 24 * period * 1.5 * 30 + one3
                    tmp_perod = period / 12
                else:
                    buy_money = onehour * 24 * period * 2 * 30 + one3

                needTotalMoney = round(buy_money, 2)
                logger.debug(needTotalMoney)
                tenant = Tenants.objects.get(tenant_id=tenant_id)
                if tenant.balance > needTotalMoney:
                    tenant.balance = tenant.balance - Decimal(needTotalMoney)
                    tenant.save()
                    logger.debug(tenant_id + "cost money" + str(needTotalMoney))
                    TenantConsume(tenant_id=tenant_id, total_memory=int(buy_memory) * int(buy_period),
                                  cost_money=needTotalMoney, payed_money=needTotalMoney, pay_status='payed').save()
                    
                    statTime = datetime.datetime.now() + datetime.timedelta(hours=1)
                    endTime = datetime.datetime.now() + relativedelta(months=int(buy_period))
                    if action=="append":
                        trpms= TenantRegionPayModel.objects.filter(tenant_id=tenant_id).order_by('-ID')[:1]
                        if len(trpms) > 0:
                            trpm = trpms[0]
                            statTime = trpm.buy_end_time + datetime.timedelta(hours=1)
                            endTime = trpm.buy_end_time + relativedelta(months=int(buy_period))
                            
                    start_time = statTime.strftime("%Y-%m-%d %H:00:00")
                    end_time = endTime.strftime("%Y-%m-%d %H:00:00")
                    data = {}
                    data["tenant_id"] = tenant_id
                    data["region_name"] = region_name
                    data["pay_model"] = pay_model
                    data["buy_period"] = tmp_perod
                    data["buy_memory"] = buy_memory
                    data["buy_disk"] = buy_disk
                    data["buy_net"] = buy_net
                    data["buy_start_time"] = start_time
                    data["buy_end_time"] = end_time
                    data["buy_money"] = buy_money
                    data["create_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    TenantRegionPayModel(**data).save()
                    result["status"] = "success"
                    monitorhook.buyPayModelMonitor(self.tenant, self.user, 'buy_pay_model')
                else:
                    result["status"] = "nomoney"
            else:
                result["status"] = "par"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result, status=200)


class RegionServiceConsumeView(AuthedView):
    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        query_day = request.GET.get("query_day", None)
        cookie_region = self.request.COOKIES.get('region', None)
        response_region = self.tenant.region if cookie_region is None else cookie_region
        now = datetime.datetime.now()
        try:
            if query_day:
                query_day += " 00:00:00"
                logger.debug("tenant {0} query consume records,query day is {1}".format(self.tenantName, query_day))
            else:
                query_day = now.strftime("%Y-%m-%d 00:00:00")

            start_time = datetime.datetime.strptime(query_day, "%Y-%m-%d 00:00:00")
            end_time_str = (start_time + datetime.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
            start_time_str = start_time.strftime("%Y-%m-%d 00:00:00")

            service_consume_list = ServiceConsume.objects.filter(tenant_id=self.tenant.tenant_id,
                                                                 region=response_region,
                                                                 time__range=(start_time_str, end_time_str))
            time_list = service_consume_list.values_list("time", flat=True).distinct()
            result_map = {}
            total_money = Decimal(0.00)
            for time_val in time_list[1:25]:
                current_hour_total_money = Decimal(0.00)
                for service_consume in service_consume_list:
                    if service_consume.time == time_val:
                        if TenantServiceInfo.objects.filter(service_id=service_consume.service_id).exists():
                            current_hour_total_money += service_consume.pay_money
                result_map[time_val] = current_hour_total_money
                total_money += current_hour_total_money

            result = sorted(result_map.iteritems(),reverse=True)
            context["length"] = len(result)
            context["result_map"] = result
            context["total_money"] = total_money

        except Exception as e:
            logger.error(e)

        return TemplateResponse(self.request, "www/region_service_consume.html", context)


class RegionServiceDetailConsumeView(AuthedView):
    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        time = request.GET.get("time")
        cookie_region = self.request.COOKIES.get('region', None)
        response_region = self.tenant.region if cookie_region is None else cookie_region
        result = {}
        try:
            logger.debug("query time "+time)
            if not time:
                return JsonResponse({"ok": False}, status=200)
            consume_list = ServiceConsume.objects.filter(tenant_id=self.tenant.tenant_id, region=response_region,
                                                         time=time).values_list("service_id", "pay_money")
            result_map = {}
            for key, value in consume_list:
                service = None
                try:
                    service = TenantServiceInfo.objects.get(service_id=key)
                except TenantServiceInfo.DoesNotExist:
                    pass
                if service:
                    service_cname = service.service_cname
                    result_map[service.service_alias] = (service_cname,value,time)
            # ["service_id":(service_cname,pay_money,time)]
            result["data"] = result_map
            result["ok"] = True
        except Exception as e:
            result["ok"] = False
            logger.error(e)
        return JsonResponse(result, status=200)
