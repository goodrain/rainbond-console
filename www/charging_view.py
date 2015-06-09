# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import time
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.core.paginator import Paginator
from django.http.response import HttpResponse
from www.views import BaseView, AuthedView
from www.models import TenantFeeBill, TenantConsume, TenantAccount, TenantRecharge

#from goodrain_web.tools import JuncheePaginator

from www.inflexdb.inflexdbservice import InflexdbService
import logging
logger = logging.getLogger('default')

# 计费
class Charging(BaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        try:
            action = request.GET.get("action", "")
            if action == "statics":
                InflexdbService = InflexdbService()
                InflexdbService.serviceContainerMemoryStatics()
                InflexdbService.serviceContainerDiskStatics()
                InflexdbService.servicePodMemoryStatics()
                InflexdbService.serviceDiskStatics()
            elif action == "charging":
                pass
        except Exception as e:
            logger.exception(e)
        
class Recharging(AuthedView):
    
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/okooostyle.css')
        return media
    
    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        context["myAppStatus"] = "active"
        try:
            tenantAccount = TenantAccount.objects.get(tenant_id=self.tenant.tenant_id)
            context["tenantAccount"] = "tenantAccount"            
            start=datetime.date.today() - datetime.timedelta(days=7)
            startTime= start.strftime('%Y-%m-%d') + " 00:00:00"
            recharges = TenantRecharge.objects.filter(tenant_id=self.tenant.tenant_id, time__ge=startTime)
            #paginator = JuncheePaginator(recharges, 10)
            #tenantRecharges = paginator.page(1)
            context["tenantRecharges"]=tenantRecharges           
            context["curpage"]=10      
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/recharge.html", context)
            
class AccountBill(AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/okooostyle.css')
        return media
    
    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        try:
            user_id = self.user.pk
            context["tenantFeeBill"] = tenantFeeBill
            context["myAppStatus"] = "active"
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/account_bill.html", context)
            
class Account(AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/okooostyle.css')
        return media
    
    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        context["myAppStatus"] = "active"
        try:
            tenant_id = self.tenant.tenant_id
            curTime = time.strftime('%Y-%m-%d') + " 00:00:00"
            tenantConsumeList = TenantConsume.objects.filter(tenant_id=tenant_id, time__gte=curTime)
            context["tenantConsumeList"] = tenantConsumeList
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/tradedetails.html", context)
            
            
class ChargingRule(AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/okooostyle.css')
        return media
        
    @never_cache
    def get(self, request, *args, **kwargs):
        try:
            action = request.GET.get("action", "")
            if action == "statics":
                pass
            elif action == "charging":
                pass
        except Exception as e:
            logger.exception(e)
        
