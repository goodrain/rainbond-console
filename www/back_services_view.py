# -*- coding: utf8 -*-
import datetime
import logging

from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from share.manager.region_provier import RegionProviderManager
from www.apiclient.regionapi import RegionInvokeApi
from www.app_http import AppServiceApi
from www.decorator import perm_required
from www.models import (ServiceInfo, TenantServiceInfo, TenantServiceAuth, TenantServiceRelation, ServiceExtendMethod,
                        AppServiceVolume, ServiceGroupRelation, ServiceCreateStep,
                        TenantServiceVolume)
from www.models.main import ServiceAttachInfo, ServiceFeeBill, TenantServiceEnvVar, ServiceEvent
from www.monitorservice.monitorhook import MonitorHook
from www.region import RegionInfo
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService,  \
    AppCreateService, ServiceAttachInfoManage
from www.utils import sn
from www.utils.crypt import make_uuid
from www.views import AuthedView, LeftSideBarMixin, CopyPortAndEnvMixin
from www.services import tenant_svc

logger = logging.getLogger('default')

baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
appClient = AppServiceApi()
rpmManager = RegionProviderManager()
appCreateService = AppCreateService()
region_api = RegionInvokeApi()
attach_info_mamage = ServiceAttachInfoManage()


class ServiceMarket(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/service-market.js',
            'www/js/jquery.cookie.js')
        return media


class ServiceMarketDeploy(LeftSideBarMixin, AuthedView, CopyPortAndEnvMixin):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        choose_region = request.GET.get("region", None)
        if choose_region is not None:
            self.response_region = choose_region
        context = self.get_context()
        try:
            service_key = request.GET.get("service_key", "")
            if service_key == "":
                return self.redirect_to('/apps/{0}/service/'.format(self.tenant.tenant_name))

            app_version = request.GET.get("app_version", "")
            context["createApp"] = "active"

            serviceObj = None
            # 获取已发布服务的信息
            if app_version:
                try:
                    serviceObj = ServiceInfo.objects.get(service_key=service_key, version=app_version)
                except ServiceInfo.DoesNotExist:
                    pass
            else:
                service_list = ServiceInfo.objects.filter(service_key=service_key)
                if len(service_list) > 0:
                    serviceObj = list(service_list)[0]
                    app_version = serviceObj.version
            if serviceObj is None:
                # 没有服务模板,需要下载模板
                code, base_info, dep_map, error_msg = baseService.download_service_info(service_key, app_version)
                if code == 500:
                    logger.error(error_msg)
                    return self.redirect_to('/apps/{0}/service/'.format(self.tenant.tenant_name))
                else:
                    serviceObj = base_info
            # 获取对应扩展数
            app_min_memory = 128
            app_max_memory = 65536
            sem = None
            try:
                sem = ServiceExtendMethod.objects.get(service_key=service_key, app_version=app_version)
            except ServiceExtendMethod.DoesNotExist:
                pass
            if sem:
                app_min_memory = sem.min_memory
                app_max_memory = sem.max_memory

            context["app_min_memory"] = app_min_memory
            context["app_max_memory"] = app_max_memory
            context["service"] = serviceObj
            context["tenantName"] = self.tenantName
            context["service_key"] = service_key
            context["app_version"] = app_version
            context["service_name"] = serviceObj.service_name
            context["min_memory"] = serviceObj.min_memory
            context["service_category"] = serviceObj.service_type

            regionBo = rpmManager.get_work_region_by_name(self.response_region)
            context['pre_paid_memory_price'] = regionBo.memory_package_price
            context['post_paid_memory_price'] = regionBo.memory_trial_price
            context['pre_paid_disk_price'] = regionBo.disk_package_price
            context['post_paid_disk_price'] = regionBo.disk_trial_price
            context['post_paid_net_price'] = regionBo.net_trial_price
            # 是否为免费租户
            context['is_tenant_free'] = (self.tenant.pay_type == "free")

            context['cloud_assistant'] = sn.instance.cloud_assistant
            context["is_private"] = sn.instance.is_private()
            # 判断云帮是否为公有云
            context["is_public_clound"] = (sn.instance.cloud_assistant == "goodrain" and (not sn.instance.is_private()))

        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/back_service_create_step_1.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        tenant_id = self.tenant.tenant_id
        service_id = make_uuid(tenant_id)
        service_alias = "gr" + service_id[-6:]
        result = {}
        try:
            success = tenant_svc.init_for_region(self.response_region, self.tenantName, tenant_id, self.user)
            if not success:
                result["status"] = "failure"
                return JsonResponse(result, status=200)

            service_key = request.POST.get("service_key", None)
            if service_key is None:
                result["status"] = "notexist"
                return JsonResponse(result, status=200)
            app_version = request.POST.get("app_version", None)
            if app_version is None:
                result["status"] = "notexist"
                return JsonResponse(result, status=200)

            service_cname = request.POST.get("create_app_name", None)
            if service_cname is None:
                result["status"] = "empty"
                return JsonResponse(result, status=200)

            service = None

            if app_version:
                try:
                    service = ServiceInfo.objects.get(service_key=service_key, version=app_version)
                except ServiceInfo.DoesNotExist:
                    pass
            else:
                service_list = ServiceInfo.objects.filter(service_key=service_key)
                if len(service_list) > 0:
                    service = list(service_list)[0]
                    app_version = service.version
            if service is None:
                result["status"] = "notexist"
                return JsonResponse(result, status=200)

            # calculate resource
            min_cpu = baseService.calculate_service_cpu(self.response_region, service.min_memory)
            service.min_cpu = min_cpu
            tempService = TenantServiceInfo()
            tempService.min_memory = service.min_memory
            tempService.service_region = self.response_region
            tempService.min_node = service.min_node
            diffMemory = service.min_node * service.min_memory
            rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, tempService, diffMemory, False)
            if not flag:
                if rt_type == "memory":
                    result["status"] = "over_memory"
                    result["tenant_type"] = self.tenant.pay_type
                else:
                    result["status"] = "over_money"
                return JsonResponse(result, status=200)

            pre_paid_period = int(request.POST.get("pre_paid_period", 0))
            disk = int(request.POST.get("disk_num", 0)) * 1024

            # create console service
            newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service_cname, service,
                                                          self.user.pk, region=self.response_region)

            sai = attach_info_mamage.create_service_attach_info(newTenantService,
                                                                newTenantService.min_memory * newTenantService.min_node,
                                                                0)
            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # 创建预付费订单
            if sai.pre_paid_money > 0:
                ServiceFeeBill.objects.create(tenant_id=tenant_id, service_id=service_id,
                                              prepaid_money=sai.pre_paid_money, pay_status="unpayed",
                                              cost_type="first_create", node_memory=newTenantService.min_memory,
                                              node_num=newTenantService.min_node,
                                              disk=disk, buy_period=pre_paid_period * 24 * 30, create_time=create_time,
                                              pay_time=create_time)

            group_id = request.POST.get("select_group_id", "")
            # 创建关系
            if group_id != "":
                group_id = int(group_id)
                if group_id > 0:
                    ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                                                        tenant_id=self.tenant.tenant_id,
                                                        region_name=self.response_region)

            monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)
            result["status"] = "success"
            result["service_id"] = service_id
            result["service_alias"] = service_alias
            # 添加安装步骤记录
            ServiceCreateStep.objects.create(tenant_id=tenant_id,
                                             service_id=service_id,
                                             app_step=11)
        except Exception as e:
            logger.exception(e)
            # tempTenantService = TenantServiceInfo.objects.filter(service_id=service_id)[0]
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service_id).delete()
            ServiceGroupRelation.objects.filter(service_id=service_id).delete()
            ServiceAttachInfo.objects.filter(service_id=service_id).delete()
            # monitorhook.serviceMonitor(self.user.nick_name, tempTenantService, 'create_service_error', False)
            result["status"] = "failure"
        return JsonResponse(result, status=200)


class ServiceDeploySettingView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/gr/basic.js', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media

    def copy_volumes(self, tenant_service, source_service):
        volumes = AppServiceVolume.objects.filter(service_key=source_service.service_key, app_version=source_service.version)
        for volume in volumes:
            baseService.add_volume_with_type(tenant_service, volume.volume_path, TenantServiceVolume.SHARE, make_uuid()[:7])
        if tenant_service.volume_mount_path:
            if not AppServiceVolume.objects.filter(service_key=source_service.service_key,
                                                   app_version=source_service.version,
                                                   volume_path=tenant_service.volume_mount_path):
                baseService.add_volume_with_type(tenant_service, tenant_service.volume_mount_path,
                                                 TenantServiceVolume.SHARE, make_uuid()[:7])

    def set_tenant_default_env(self, envs, outer_ports):
        for env in envs:
            if env.attr_name == 'SITE_URL':
                if self.cookie_region in RegionInfo.valid_regions():
                    port = RegionInfo.region_port(self.cookie_region)
                    domain = RegionInfo.region_domain(self.cookie_region)
                    env.options = 'direct_copy'
                    if len(outer_ports) > 0:
                        env.attr_value = 'http://{}.{}.{}{}:{}'.format(outer_ports[0].container_port, self.serviceAlias, self.tenantName, domain, port)
                    logger.debug("SITE_URL = {} options = {}".format(env.attr_value, env.options))
            elif env.attr_name == 'TRUSTED_DOMAIN':
                if self.cookie_region in RegionInfo.valid_regions():
                    port = RegionInfo.region_port(self.cookie_region)
                    domain = RegionInfo.region_domain(self.cookie_region)
                    env.options = 'direct_copy'
                    if len(outer_ports) > 0:
                        env.attr_value = '{}.{}.{}{}:{}'.format(outer_ports[0].container_port, self.serviceAlias, self.tenantName, domain, port)
                    logger.debug("TRUSTED_DOMAIN = {} options = {}".format(env.attr_value, env.options))

    def saveAdapterEnv(self, service):
        num = TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="GD_ADAPTER").count()
        if num < 1:
            attr = {"tenant_id": service.tenant_id, "service_id": service.service_id, "name": "GD_ADAPTER",
                    "attr_name": "GD_ADAPTER", "attr_value": "true", "is_change": False, "scope": "inner", "container_port": -1}
            TenantServiceEnvVar.objects.create(**attr)
            attr.update({"env_name": "GD_ADAPTER", "env_value": "true"})
            region_api.add_service_env(service.service_region,self.tenantName,service.service_alias,attr)

    def create_service_event(self, service, tenant, action):
        event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                             tenant_id=tenant.tenant_id, type="{0}".format(action),
                             deploy_version=service.deploy_version,
                             old_deploy_version=service.deploy_version,
                             user_name=self.user.nick_name, start_time=datetime.datetime.now())
        event.save()
        return event
