# -*- coding: utf8 -*-
import uuid
import hashlib
import datetime
import time
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.core.paginator import Paginator
from django.http.response import HttpResponse
from www.views import AuthedView, LeftSideBarMixin
from www.models import TenantFeeBill, TenantRegionPayModel
from www.region import RegionInfo
from django.conf import settings
from www.utils import sn

from goodrain_web.tools import JuncheePaginator

import logging
logger = logging.getLogger('default')



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
            context["tenantFeeBill"] = tenantFeeBill
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
        context["memoryList"] = [1, 2, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 600, 700, 1000]
        context["diskList"] = [0, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        context["netList"] = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
        context["periodList"] = [(1, "1月"), (2, "2月"), (3, "3月"), (4, "4月"), (5, "5月"), (6, "6月"), (7, "7月"), (8, "8月"), (9, "9月"), (12, "1年"), (24, "2年")]
        tenantBuyPayModels = TenantRegionPayModel.objects.filter(tenant_id=self.tenant.tenant_id)
        context["tenantBuyPayModels"] = tenantBuyPayModels
        RegionMap = {}
        for item in RegionInfo.region_list:
            if item["enable"]:
                RegionMap[item["name"]] = item["label"]
        PeriodMap = {"hour":u"小时", "month":u"月", "year":u"年"}
        context["RegionMap"] = RegionMap
        context["PeriodMap"] = PeriodMap        
        context["REGION_FEE_RULE"] = settings.REGION_FEE_RULE   
        return TemplateResponse(self.request, "www/paymodel.html", context)


class AssistantView(LeftSideBarMixin, AuthedView):
    """获取云帮自助授权信息"""
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        enterprise = sn.instance.cloud_assistant
        context["enterprise"]=enterprise

        return TemplateResponse(self.request, "www/ser.html", context)