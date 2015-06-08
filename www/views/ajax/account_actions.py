# -*- coding: utf8 -*-
import datetime
import json

from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required
from www.models import TenantFeeBill, TenantPaymentNotify



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

class AccountQuery(AuthedView):
    @perm_required('tenant_account')
    def post(self, request, *args, **kwargs):
        try:
            tenant_id = self.tenant.tenant_id
            action = request.POST["action"]
        except Exception as e:
            logger.exception(e)
        
        
  
class AccountNotify(AuthedView):
    @perm_required('tenant_account')
    def post(self, request, *args, **kwargs):
        try:
            tenant_id = self.tenant.tenant_id
            action = request.POST["action"]
        except Exception as e:
            logger.exception(e)      
        
class ChargingRule(AuthedView):
    @perm_required('tenant_account')
    def post(self, request, *args, **kwargs):
        try:
            tenant_id = self.tenant.tenant_id
            action = request.POST["action"]
        except Exception as e:
            logger.exception(e)   
        
