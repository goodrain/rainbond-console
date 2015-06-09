# -*- coding: utf8 -*-
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required
from www.models import TenantFeeBill, TenantPaymentNotify,TenantRecharge, TenantConsume



import logging
from django.template.defaultfilters import length
logger = logging.getLogger('default')

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
                recharges = TenantRecharge.objects.filter(tenant_id=self.tenant.tenant_id, time__range=(startTime, endTime))
            else:
                recharges = TenantRecharge.objects.filter(tenant_id=self.tenant.tenant_id)                                          
            paginator = JuncheePaginator(recharges, int(per_page))
            tenantRecharges = paginator.page(int(page))
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
        context["date_scope"] = date_scope
        try:
            tenant_id = self.tenant.tenant_id
            diffDay = int(date_scope)
            if diffDay > 0:
                end = datetime.datetime.now()
                endTime = end.strftime("%Y-%m-%d %H:%M:%S")
                start = datetime.date.today() - datetime.timedelta(days=int(date_scope))
                startTime = start.strftime('%Y-%m-%d') + " 00:00:00"
                recharges = TenantConsume.objects.filter(tenant_id=self.tenant.tenant_id, time__range=(startTime, endTime))
            else:
                recharges = TenantConsume.objects.filter(tenant_id=self.tenant.tenant_id)                                          
            paginator = JuncheePaginator(recharges, int(per_page))
            tenantConsumes = paginator.page(int(page))
            context["tenantConsumes"] = tenantConsumes
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/tradedetails-list.html", context)