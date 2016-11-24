# -*- coding: utf8 -*-
import logging
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.http import JsonResponse

from www.app_http import AppServiceApi
from www.views import BaseView, AuthedView, LeftSideBarMixin, CopyPortAndEnvMixin
from www.decorator import perm_required
from www.models import ServiceInfo, TenantServicesPort, TenantServiceInfo, TenantServiceRelation, TenantServiceEnv, TenantServiceAuth
from service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, CodeRepositoriesService, TenantRegionService
from www.utils.language import is_redirect
from www.monitorservice.monitorhook import MonitorHook
from www.utils.crypt import make_uuid
from django.conf import settings
from www.servicetype import ServiceType
from www.utils import sn

logger = logging.getLogger('default')

regionClient = RegionServiceApi()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
tenantUsedResource = TenantUsedResource()
baseService = BaseTenantService()
codeRepositoriesService = CodeRepositoriesService()
tenantRegionService = TenantRegionService()
appClient = AppServiceApi()

class CreateServiceEntranceView(LeftSideBarMixin, AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/css/style.css', 'www/css/style-responsive.css', 'www/js/jquery.cookie.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/respond.min.js')
        return media

    @never_cache
    @perm_required('create_service')
    def get(self, request, *args, **kwargs):
        choose_region = request.GET.get("region", None)
        if choose_region is not None:
            self.response_region = choose_region
        context = self.get_context()
        context["createApp"] = "active"
        try:
            # 云市最新的应用
            res, resp = appClient.getRemoteServices(key="newest", limit=5)
            if res.status == 200:
                service_list = json.loads(resp.data)
                context["service_list"] = service_list

        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_one.html", context)