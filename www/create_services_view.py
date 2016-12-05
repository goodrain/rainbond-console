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
from www.models import  AppService
from django.db.models import Q,Count

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
        context["is_private"] = sn.instance.is_private()
        context["cloud_assistant"] = sn.instance.cloud_assistant
        fr = request.GET.get("fr", None)
        if fr is None:
            # 如果为公有云,会有分享的选项 private
            if not sn.instance.is_private() and sn.instance.cloud_assistant == "goodrain":
                fr = "private"
            else:
                fr = "deploy"
        if fr not in ("private","deploy","hot","new"):
            fr = "private"
        context["fr"] = fr
        try:
            # # 云市最新的应用
            # res, resp = appClient.getRemoteServices(key="newest", limit=5)
            # if res.status == 200:
            #     service_list = json.loads(resp.data)
            #     context["service_list"] = service_list

            if fr == "private":
                # 私有市场
                service_list = AppService.objects.filter(tenant_id=self.tenant.tenant_id) \
                    .exclude(service_key='application') \
                    .exclude(service_key='redis', app_version='2.8.20_51501') \
                    .exclude(service_key='wordpress', app_version='4.2.4')[:11]
                # # 团队共享
                # tenant_service_list = [x for x in service_list if x.status == "private"]
                # # 云帮共享
                # assistant_service_list = [x for x in service_list if x.status != "private" and not x.dest_ys]
                # # 云市共享
                # cloud_service_list = [x for x in service_list if x.status != "private" and x.dest_ys]
                # context["tenant_service_list"] = tenant_service_list
                # context["assistant_service_list"] = assistant_service_list
                # context["cloud_service_list"] = cloud_service_list
                context["service_list"] = [x for x in service_list]
            elif fr == "deploy":
                # 当前租户最新部署的应用
                tenant_id = self.tenant.tenant_id
                tenant_service_list = TenantServiceInfo.objects.filter(tenant_id=tenant_id).exclude(service_key='application').order_by("-ID")
                service_key_query = []
                tenant_service_query = None
                for tenant_service in tenant_service_list:
                    if tenant_service.service_key == 'redis' and tenant_service.version == '2.8.20_51501':
                        continue
                    if tenant_service.service_key == 'wordpress' and tenant_service.version == '4.2.4':
                        continue
                    tmp_key = '{0}_{1}'.format(tenant_service.service_key, tenant_service.version)
                    if tmp_key in service_key_query:
                        continue
                    service_key_query.append(tmp_key)
                    if len(service_key_query) > 18:
                        break
                    if tenant_service_query is None:
                        tenant_service_query = (Q(service_key=tenant_service.service_key) & Q(version=tenant_service.version))
                    else:
                        tenant_service_query = tenant_service_query | (Q(service_key=tenant_service.service_key) & Q(version=tenant_service.version))
                if len(service_key_query) > 0:
                    service_list = ServiceInfo.objects.filter(tenant_service_query)
                    context["service_list"] = service_list[:11]
            elif fr == "hot":
                # 当前云帮部署最多应用
                tenant_service_list = TenantServiceInfo.objects.values('service_key', 'version') \
                    .exclude(service_key='application') \
                    .annotate(Count('ID')).order_by("-ID__count")
                service_key_query = []
                tenant_service_query = None
                for tenant_service in tenant_service_list:
                    if tenant_service.get("service_key") == 'redis' and tenant_service.get("version") == '2.8.20_51501':
                        continue
                    if tenant_service.get("service_key") == 'wordpress' and tenant_service.get("version") == '4.2.4':
                        continue
                    tmp_key = '{0}_{1}'.format(tenant_service.get("service_key"), tenant_service.get("version"))
                    if tmp_key in service_key_query:
                        continue
                    service_key_query.append(tmp_key)
                    if len(service_key_query) > 18:
                        break
                    if tenant_service_query is None:
                        tenant_service_query = (Q(service_key=tenant_service.get("service_key")) & Q(version=tenant_service.get("version")))
                    else:
                        tenant_service_query = tenant_service_query | (Q(service_key=tenant_service.get("service_key")) & Q(version=tenant_service.get("version")))
                if len(service_key_query) > 0:
                    service_list = ServiceInfo.objects.filter(tenant_service_query)
                    context["service_list"] = service_list[:11]
            elif fr == "new":
                # 云市最新的应用
                res, resp = appClient.getRemoteServices(key="newest", limit=11)
                if res.status == 200:
                    service_list = json.loads(resp.data)
                    context["service_list"] = service_list
                else:
                    logger.error("service market query newest failed!")
                    logger.error(res, resp)


        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/app_create_step_one.html", context)