# -*- coding: utf8 -*-
import datetime
import json
import logging

from django.db.models import Q, Count
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from share.manager.region_provier import RegionProviderManager
from www.apiclient.regionapi import RegionInvokeApi
from www.app_http import AppServiceApi
from www.decorator import perm_required
from www.models import (ServiceInfo, TenantServiceInfo, TenantServiceAuth, TenantServiceRelation,
                        AppServicePort, AppServiceEnv, AppServiceRelation, ServiceExtendMethod,
                        AppServiceVolume, AppService, ServiceGroupRelation, ServiceCreateStep, AppServiceGroup,
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

    @never_cache
    @perm_required('tenant_access')
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
            fr = request.GET.get("fr", "private")
            context["fr"] = fr
            if fr == "local":
                cacheGroupList = AppServiceGroup.objects.filter(is_success=True)
                context["cacheGroupList"] = cacheGroupList
                cacheServiceList = ServiceInfo.objects.filter(status="published", publish_type="single")
                context["cacheServiceList"] = cacheServiceList
                try:
                    appClient.timeout = 15
                    res, resp = appClient.getRemoteServices()
                    if res.status == 200:
                        appService = {}
                        appVersion = {}
                        appdata = json.loads(resp.data)
                        for appda in appdata:
                            appService[appda["service_key"] + "_" + appda["version"]] = appda["update_version"]
                            appVersion[appda["service_key"] + "_" + appda["version"]] = appda["version"]
                        context["appService"] = appService
                        context["appVersion"] = appVersion
                    else:
                        logger.error("query remote service failed")
                except Exception as e:
                    logger.exception(e)
            elif fr == "private":
                # 私有市场
                service_list = AppService.objects.filter(tenant_id=self.tenant.tenant_id) \
                    .exclude(service_key='application') \
                    .exclude(service_key='redis', app_version='2.8.20_51501') \
                    .exclude(service_key='wordpress', app_version='4.2.4')
                group_list = AppServiceGroup.objects.filter(is_success=True)
                # 团队共享
                tenant_service_list = [x for x in service_list if x.status == "private"]
                tenant_group_list = [x for x in group_list if x.tenant_id == self.tenant.tenant_id]
                # 云帮共享
                assistant_service_list = [x for x in service_list if x.status != "private" and not x.dest_ys]
                assistant_group_list = [x for x in group_list if not x.is_market]
                # 云市共享
                cloud_service_list = [x for x in service_list if x.status != "private" and x.dest_ys]
                cloud_group_list = [x for x in group_list if x.is_market]
                context["tenant_service_list"] = tenant_service_list
                context["assistant_service_list"] = assistant_service_list
                context["cloud_service_list"] = cloud_service_list

                context["assistant_group_list"] = assistant_group_list
                context["cloud_group_list"] = cloud_group_list
                context["tenant_group_list"] = tenant_group_list
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
                    context["service_list"] = service_list
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
                    context["service_list"] = service_list
            elif fr == "new":
                # 云市最新的应用
                # res, resp = appClient.getRemoteServices(key="newest", limit=18)
                res, resp = appClient.getPublishedGroupAndService(key="newest", limit=18)
                if res.status == 200:
                    service_list = json.loads(resp.data)
                    context["service_list"] = service_list
                else:
                    logger.error("service market query newest failed!")
                    logger.error(res, resp)

        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_market.html", context)


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

    def copy_envs(self, source_service, envs):
        s = self.service
        baseService = BaseTenantService()
        has_env = []
        for env in envs:
            source_env = AppServiceEnv.objects.get(service_key=s.service_key, app_version=s.version, attr_name=env.attr_name)
            baseService.saveServiceEnvVar(s.tenant_id, s.service_id, source_env.container_port, source_env.name,
                                          env.attr_name, env.attr_value, source_env.is_change, source_env.scope)
            has_env.append(env.attr_name)

        for sys_env in AppServiceEnv.objects.filter(service_key=s.service_key, app_version=s.version):
            if sys_env.attr_name not in has_env:
                baseService.saveServiceEnvVar(s.tenant_id, s.service_id, sys_env.container_port, sys_env.name,
                                              sys_env.attr_name, sys_env.attr_value, sys_env.is_change, sys_env.scope)

    def copy_ports(self, source_service):
        AppPorts = AppServicePort.objects.filter(service_key=self.service.service_key, app_version=self.service.version)
        baseService = BaseTenantService()
        for port in AppPorts:
            if not port.port_alias:
                port_alias = self.service.service_alias.upper() + str(port.container_port)
            else:
                port_alias = port.port_alias
            baseService.addServicePort(self.service, source_service.is_init_accout, container_port=port.container_port, protocol=port.protocol, port_alias=port_alias,
                                       is_inner_service=port.is_inner_service, is_outer_service=port.is_outer_service)

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

    def find_dependecy_services(self, serviceObj):
        asrlist = AppServiceRelation.objects.filter(service_key=serviceObj.service_key, app_version=serviceObj.version)
        dependecy_keys = []
        dependecy_info = {}
        dependecy_version = {}
        dependecy_services = {}
        if len(asrlist) > 0:
            for asr in asrlist:
                dependecy_keys.append(asr.dep_service_key)
                dependecy_info[asr.dep_service_key] = asr.dep_app_alias
                dependecy_version[asr.dep_service_key] = asr.dep_app_version

        if len(dependecy_keys) > 0:
            dependecy_services = dict((el, []) for el in dependecy_keys)
            tenant_id = self.tenant.tenant_id
            deployTenantServices = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_key__in=dependecy_keys, service_region=self.response_region, service_origin='assistant')
            if len(deployTenantServices) > 0:
                for s in deployTenantServices:
                    dependecy_services[s.service_key].append(s)
        return dependecy_services, dependecy_info, dependecy_version

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

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        choose_region = request.GET.get("region", None)
        if choose_region is not None:
            self.response_region = choose_region
        context = self.get_context()
        try:
            serviceObj = ServiceInfo.objects.get(service_key=self.service.service_key, version=self.service.version)
            dependecy_services, dependecy_info, dependecy_version = self.find_dependecy_services(serviceObj)

            context["service_min_memory"] = serviceObj.min_memory
            context["dependecy_services"] = dependecy_services
            context["dependecy_info"] = dependecy_info
            context["dependecy_version"] = dependecy_version
            context["tenantName"] = self.tenantName
            envs = AppServiceEnv.objects.filter(service_key=self.service.service_key,
                                                app_version=self.service.version,
                                                container_port=0,
                                                is_change=True)
            outer_ports = AppServicePort.objects.filter(service_key=self.service.service_key,
                                                        app_version=self.service.version,
                                                        is_outer_service=True,
                                                        protocol='http')

            self.set_tenant_default_env(envs, outer_ports)
            context["envs"] = envs
            context["outer_port"] = outer_ports
            context["service_alias"] = self.service.service_alias
            context["service"] = serviceObj

        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/back_service_create_step_3.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):

        dependency_services = json.loads(request.POST.get("dep_list", "[]"))
        envs = json.loads(request.POST.get("envs", ""))
        service_env = []
        for env in envs:
            s_env = AppServiceEnv()
            s_env.attr_name = env["attr_name"]
            s_env.attr_value = env["attr_value"]
            service_env.append(s_env)
        envs = service_env

        # 内存大小
        min_memory = int(request.POST.get("service_min_memory", 512))
        if min_memory < 128:
            min_memory *= 1024
        self.service.min_memory = min_memory
        cpu = baseService.calculate_service_cpu(self.response_region, min_memory)
        self.service.min_cpu = cpu

        rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, min_memory*self.service.min_node, False)
        if not flag:
            result = {}
            if rt_type == "memory":
                result["status"] = "over_memory"
                result["tenant_type"] = self.tenant.pay_type
            else:
                result["status"] = "over_money"
            return JsonResponse(result, status=200)

        self.service.save()

        result = {}
        try:

            exist_t_services = []
            for str in dependency_services:
                if str != "":
                    service_alias, service_key, app_version = str.split(":", 2)
                    if service_alias == "__no_dep_service__":
                        return JsonResponse({"status": "not_have_dep_service"}, status=200)
                    if ServiceInfo.objects.filter(service_key=service_key, version=app_version).count() == 0:
                        return JsonResponse({"status": "depend_service_notexsit"})
                    exist_t_s = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id, service_alias=service_alias)
                    exist_t_services.append(exist_t_s)

            source_service = ServiceInfo.objects.get(service_key=self.service.service_key, version=self.service.version)
            self.copy_envs(source_service, envs)
            self.copy_ports(source_service)
            # add volume
            self.copy_volumes(self.service, source_service)

            dep_sids = []
            tsrs = TenantServiceRelation.objects.filter(service_id=self.service.service_id)
            for tsr in tsrs:
                dep_sids.append(tsr.dep_service_id)
            
            baseService.create_region_service(self.service, self.tenantName, self.response_region, self.user.nick_name, dep_sids=json.dumps(dep_sids))
            
            # 根据已有服务创建依赖关系
            if exist_t_services:
                # self.saveAdapterEnv(self.service)
                for t_service in exist_t_services:
                    try:
                        baseService.create_service_dependency(self.tenant, self.service, t_service.service_id, self.response_region)
                    except Exception as e:
                        logger.exception(e)

            service_status = "stateless" if self.service.extend_method == "stateless" else "state"

            data = {}
            data["label_values"] = "无状态的应用" if service_status == "stateless" else "有状态的应用"
            data["enterprise_id"] = self.tenant.enterprise_id
            region_api.update_service_state_label(self.response_region, self.tenantName, self.serviceAlias, data)
            self.service.save()
            body = {}
            event = self.create_service_event(self.service, self.tenant, "deploy")
            kind = baseService.get_service_kind(self.service)
            body["event_id"] = event.event_id
            body["deploy_version"] = self.service.deploy_version
            body["operator"] = self.user.nick_name
            body["action"] = "upgrade"

            envs = {}
            buildEnvs = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, attr_name__in=(
                "COMPILE_ENV", "NO_CACHE", "DEBUG", "PROXY", "SBT_EXTRAS_OPTS"))
            for benv in buildEnvs:
                envs[benv.attr_name] = benv.attr_value
            body["envs"] = envs

            body["kind"] = kind
            body["enterprise_id"] = self.tenant.enterprise_id
            region_api.build_service(self.service.service_region, self.tenantName, self.serviceAlias, body)
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'init_region_service', True)

            result["status"] = "success"
            result["next_url"] = next_url = '/apps/{}/{}/detail/'.format(self.tenantName, self.serviceAlias)

            attach_info_mamage.update_attach_info_by_tenant(self.tenant, self.service)
            # 清理暂存步骤
            ServiceCreateStep.objects.filter(tenant_id=self.tenant.tenant_id,
                                             service_id=self.service.service_id,
                                             app_step=11).delete()
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result, status=200)
