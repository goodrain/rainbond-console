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
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, \
    CodeRepositoriesService
from www.monitorservice.monitorhook import MonitorHook

logger = logging.getLogger('default')
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



    def check_region(self):
        region = self.request.GET.get('region', None)
        if region is not None:
            if region in RegionInfo.region_names():
                if region == 'aws-bj-1' and self.tenant.region != 'aws-bj-1':
                    raise Http404
                self.response_region = region
            else:
                raise Http404

        try:
            t_region, created = TenantRegionInfo.objects.get_or_create(tenant_id=self.tenant.tenant_id, region_name=self.response_region)
            self.tenant_region = t_region
        except Exception, e:
            logger.error(e)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        self.check_region()
        context = self.get_context()
        try:
            gid = request.GET.get("gid", "-1")
            if gid !="-1" and ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, ID=gid).count() < 1:
                 return self.redirect_to('/apps/{0}/myservice/?gid=-1'.format(self.tenant.tenant_name))
            
            if gid.strip() != "" and gid != '-1':
                service_id_list = ServiceGroupRelation.objects.filter(group_id=gid).values("service_id")
                # service_list = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id, service_region=self.response_region, service_origin="assistant", service_id__in=service_id_list)
                service_list = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id,
                                                                service_region=self.response_region,
                                                                service_id__in=service_id_list)
            else:
                service_id_list = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region).values("service_id")
                # service_list = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id, service_origin="assistant", service_region=self.response_region).exclude(service_id__in=service_id_list)
                service_list = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id,
                                                                service_region=self.response_region).exclude(
                    service_id__in=service_id_list)

            sgrs = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region)

            serviceGroupIdMap = {}
            for sgr in sgrs:
                serviceGroupIdMap[sgr.service_id] = sgr.group_id

            serviceGroupNameMap = {}
            group_list = context["groupList"]
            group_name = u"未分组"
            group_id = -1
            for group in group_list:
                serviceGroupNameMap[group.ID] = group.group_name
                if group.ID == int(gid):
                    group_name = group.group_name
                    group_id = group.ID
            context["group_id"] = int(gid)
            context["tenantServiceList"] = service_list
            context["serviceGroupNameMap"] = serviceGroupNameMap
            context["serviceGroupIdMap"] = serviceGroupIdMap
            context["tenantName"] = self.tenantName
            context["curTenant"] = self.tenant
            context["myAppStatus"] = "active"
            context["group_name"] = group_name
            context["group_id"] = group_id
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_app.html", context)



