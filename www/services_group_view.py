# -*- coding: utf8 -*-
import logging
import json

from django.http.response import JsonResponse
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.http import Http404

from www.models.main import TenantRegionPayModel, ServiceGroup, ServiceGroupRelation
from www.views import BaseView, AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import (Users, ServiceInfo, TenantRegionInfo, TenantServiceInfo,
                        ServiceDomain, PermRelService, PermRelTenant,
                        TenantServiceRelation, TenantServicesPort, TenantServiceEnv,
                        TenantServiceEnvVar, TenantServiceMountRelation,
                        ServiceExtendMethod, TenantServiceVolume)
from www.region import RegionInfo
from service_http import RegionServiceApi
from django.conf import settings
from goodrain_web.custom_config import custom_config
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, \
    CodeRepositoriesService
from www.monitorservice.monitorhook import MonitorHook
from www.utils.url import get_redirect_url
from www.utils.md5Util import md5fun

logger = logging.getLogger('default')
regionClient = RegionServiceApi()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
codeRepositoriesService = CodeRepositoriesService()


class MyTenantService(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(MyTenantService, self).get_media() + self.vendor(
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    def get_service_group_relation(self):
        try:
            service_list = ServiceGroupRelation.objects.all()
            data = {}
            for service in service_list:
                data[service.service_id] = service.group_id
            return data
        except Exception, e:
            logger.error(e)

    def get_service_group(self):
        try:
            group_list = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.tenant.region)
            data = {}
            for group in group_list:
                data[group.ID] = group.group_name
            return data
        except Exception, e:
            logger.error(e)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        try:
            tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region)
            service_group_relation = self.get_service_group_relation()
            groups = self.get_service_group()
            for tenantService in tenantServiceList:
                group_id = service_group_relation.get(tenantService.service_id, None)
                if group_id is not None:
                    group_name = groups.get(group_id)
                    tenantService.group_name = group_name
                    tenantService.group_id = group_id
                else:
                    tenantService.group_name = "未分组"
                    tenantService.group_id = -1
            context["tenantServiceList"] = tenantServiceList
            context["myAppStatus"] = "active"
            context["totalFlow"] = 0
            context["totalAppNumber"] = len(tenantServiceList)
            context["tenantName"] = self.tenantName
            totalNum = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).count()
            context["totalNum"] = totalNum
            context["curTenant"] = self.tenant
            context["tenant_balance"] = self.tenant.balance
            # params for prompt
            context["pay_type"] = self.tenant.pay_type
            context["expired"] = tenantAccountService.isExpired(self.tenant)
            context["expired_time"] = self.tenant.expired_time
            status = tenantAccountService.get_monthly_payment(self.tenant, self.tenant.region)
            context["monthly_payment_status"] = status
            groups = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.tenant.region)
            context["groups"] = list(groups)
            if status != 0:
                payModellist = TenantRegionPayModel.objects.filter(tenant_id=self.tenant.tenant_id,
                                                                   region_name=self.tenant.region).order_by(
                    "-buy_end_time")
                context["buy_end_time"] = payModellist[0].buy_end_time

            if self.tenant_region.service_status == 0:
                logger.debug("tenant.pause", "unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.unpause(self.response_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()
            elif self.tenant_region.service_status == 3:
                logger.debug("tenant.pause", "system unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.systemUnpause(self.response_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()
        except Exception as e:
            print e
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_app.html", context)



