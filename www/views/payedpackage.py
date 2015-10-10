# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from www.views import AuthedView
from django.conf import settings
logger = logging.getLogger('default')

class PackageSelectView(AuthedView):
    
    def get_media(self):
        media = super(PackageSelectView, self).get_media(
        ) + self.vendor('www/css/package-register.css', 'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js')
        return media
    
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        feerule = settings.REGION_RULE
        context["personal_money"] = feerule[self.tenant.region]["personal_month_money"]
        context["company_money"] = feerule[self.tenant.region]["company_month_money"]
        return TemplateResponse(self.request, "www/account/packageselect.html", context)
        
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            current_select = request.POST.get('current_select', "free")
            logger.debug(current_select)
            if current_select != "free" and (current_select == "personal" or current_select == "company"):
                self.tenant.pay_type = 'payed'
                self.tenant.pay_level = current_select
                self.tenant.save()
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result, status=200)
            
class PackageUpgradeView(AuthedView):
    
    def get_media(self):
        media = super(PackageUpgradeView, self).get_media(
        ) + self.vendor('www/css/package-upgrade.css', 'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js')
        return media
    
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context["tenant"] = self.tenant
        feerule = settings.REGION_RULE
        context["personal_money"] = feerule[self.tenant.region]["personal_month_money"]
        context["company_money"] = feerule[self.tenant.region]["company_month_money"]
        return TemplateResponse(self.request, "www/account/packageupgrade.html", context)
        
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            current_select = request.POST.get('current_select', "free")
            if current_select != "free" and (current_select == "personal" or current_select == "company"):
                self.tenant.pay_type = 'payed'
                self.tenant.pay_level = current_select
                self.tenant.save()
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result, status=200)
