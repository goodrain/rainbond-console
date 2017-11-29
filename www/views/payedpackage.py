# -*- coding: utf8 -*-
import logging

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse
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
        selected = request.GET.get("selected", "")
        context["selected"] = selected
        return TemplateResponse(self.request, "www/account/packageselect.html", context)
        
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            current_select = request.POST.get('current_select', "free")
            logger.debug(current_select)
            if self.tenant.pay_type != "unpay":
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
        return TemplateResponse(self.request, "www/account/packageupgrade.html", context)
        
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            current_select = request.POST.get('current_select', "free")
            if self.tenant.pay_type != "unpay":
                if current_select != "free" and (current_select == "personal" or current_select == "company"):
                    self.tenant.pay_type = 'payed'
                    self.tenant.pay_level = current_select
                    self.tenant.save()
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result, status=200)
