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
from www.models import TenantFeeBill, TenantConsume
from www.tenantservice.baseservice import BaseTenantService

from goodrain_web.tools import JuncheePaginator

from www.inflexdb.inflexdbservice import InflexdbService
import logging
logger = logging.getLogger('default')
        
class Recharging(AuthedView):
    
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 
            'www/js/jquery.scrollTo.min.js')
        return media
    
    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        baseService = BaseTenantService()
        tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
        context["tenantServiceList"] = tenantServiceList
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        context["myFinanceRecharge"] = "active"
        context["myFinanceStatus"] = "active"
        
        context["tenant"] = self.tenant
        
        return TemplateResponse(self.request, "www/recharge.html", context)
            
class AccountBill(AuthedView):

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
            context["tenantFeeBill"] = tenantFeeBill
            context["myFinanceBill"] = "active"
            context["myFinanceStatus"] = "active"
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/account_bill.html", context)
            
class Account(AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 
            'www/js/jquery.scrollTo.min.js')
        return media
    
    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        baseService = BaseTenantService()
        tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user.pk, self.tenant.tenant_id)
        context["tenantServiceList"] = tenantServiceList
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        context["myFinanceAccount"] = "active"
        context["myFinanceStatus"] = "active"
        return TemplateResponse(self.request, "www/tradedetails.html", context)
