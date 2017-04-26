# -*- coding: utf8 -*-
import json
from decimal import Decimal

from addict import Dict
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse

from share.manager.region_provier import RegionProviderManager
from www.models.main import ServiceAttachInfo, ServiceFeeBill
from www.views import AuthedView, LeftSideBarMixin, CopyPortAndEnvMixin, Http404
from www.decorator import perm_required
from www.models import (ServiceInfo, TenantServiceInfo, TenantServiceAuth, TenantServiceRelation,
                        AppServicePort, AppServiceEnv, AppServiceRelation, ServiceExtendMethod,
                        AppServiceVolume, AppService, ServiceGroupRelation, ServiceCreateStep, AppServiceGroup)
from service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, \
    TenantRegionService, \
    AppCreateService
from www.monitorservice.monitorhook import MonitorHook
from www.utils.crypt import make_uuid
from www.app_http import AppServiceApi
from www.region import RegionInfo
from django.db.models import Q, Count
from www.utils import sn

import logging
import datetime
from dateutil.relativedelta import relativedelta

logger = logging.getLogger('default')

regionClient = RegionServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
appClient = AppServiceApi()
tenantRegionService = TenantRegionService()
rpmManager = RegionProviderManager()
appCreateService = AppCreateService()


class GroupServiceDeployView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        group_key = request.GET.get("group_key", None)
        group_version = request.GET.get("group_version", None)
        try:
            context = self.get_context()
            app_groups = AppServiceGroup.objects.filter(group_share_id=group_key, group_version=group_version)
            if len(app_groups) > 1:
                logger.error("group for group_key:{0} and group_version:{1} is more than one ! ".format(group_key,
                                                                                                        group_version))
            elif len(app_groups) == 0:
                app_groups = AppServiceGroup.objects.filter(group_share_id=group_key).order_by("-update_time")
                if len(app_groups) == 0:
                    return Http404
                elif len(app_groups) == 1:
                    group_version = app_groups[0].group_version
            else:
                logger("install group apps! group_key {0} group_version {1}".format(group_key,group_version))

            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
        except Exception as e:
            logger.exception(e)
        return self.redirect_to("/apps/{0}/group-deploy/step1/?group_key={1}&group_version={2}".format(self.tenantName,group_key,group_version))


class GroupServiceDeployStep1(LeftSideBarMixin, AuthedView):
    """组应用创建第一步,填写组信息"""

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):

        context = self.get_context()
        try:
            get_params = request.GET.dict
            logger.debug('-'*78)
            logger.debug(dir(get_params))
            logger.debug('-'*78)

            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/group/group_app_create_step_1.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            pass
        except Exception as e:
            logger.exception(e)
        data.update({"success": True, "code": 200})
        return JsonResponse(data, status=200)


class GroupServiceDeployStep2(LeftSideBarMixin, AuthedView):
    """组应用创建第二步,应用内存信息"""

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/group/group_app_create_step_2.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            pass
        except Exception as e:
            logger.exception(e)
        data.update({"success": True, "code": 200})
        return JsonResponse(data, status=200)


class GroupServiceDeployStep3(LeftSideBarMixin, AuthedView):
    """组应用创建第三步,应用相关设置"""

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/group/group_app_create_step_3.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            pass
        except Exception as e:
            logger.exception(e)
        data.update({"success": True, "code": 200})
        return JsonResponse(data, status=200)
