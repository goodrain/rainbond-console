# -*- coding: utf8 -*-
import json
from addict import Dict
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse
from www.views import AuthedView, LeftSideBarMixin, CopyPortAndEnvMixin
from www.decorator import perm_required
from www.models import (ServiceInfo, TenantServiceInfo, TenantServiceAuth, TenantServiceRelation,
                        AppServicePort, AppServiceEnv, AppServiceRelation, ServiceExtendMethod,
                        AppServiceVolume, AppService, ServiceGroupRelation)
from service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, TenantRegionService
from www.monitorservice.monitorhook import MonitorHook
from www.utils.crypt import make_uuid
from www.app_http import AppServiceApi
from www.region import RegionInfo
from django.db.models import Q, Count

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
appClient = AppServiceApi()
tenantRegionService = TenantRegionService()


class ServiceMarket(LeftSideBarMixin, AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/back-service-create.js',
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
                cacheServiceList = ServiceInfo.objects.filter(status="published")
                context["cacheServiceList"] = cacheServiceList
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
            elif fr == "private":
                # 私有市场
                service_list = AppService.objects.filter(tenant_id=self.tenant.tenant_id) \
                    .exclude(service_key='application') \
                    .exclude(service_key='redis', app_version='2.8.20_51501') \
                    .exclude(service_key='wordpress', app_version='4.2.4')
                # 团队共享
                tenant_service_list = [x for x in service_list if x.status == "private"]
                # 云帮共享
                assistant_service_list = [x for x in service_list if x.status != "private" and not x.dest_ys]
                # 云市共享
                cloud_service_list = [x for x in service_list if x.status != "private" and x.dest_ys]
                context["tenant_service_list"] = tenant_service_list
                context["assistant_service_list"] = assistant_service_list
                context["cloud_service_list"] = cloud_service_list
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
                res, resp = appClient.getRemoteServices(key="newest", limit=18)
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
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/back-service-create.js')
        return media

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

    def parse_dependency_service(self, dependency_service):
        new_services = []
        exist_t_services = []
        exist_new_services = []
        for string in dependency_service:
            if string != "":
                service_alias, service_key, app_version = string.split(':', 2)
                if service_alias == '__new__':
                    if ServiceInfo.objects.filter(service_key=service_key, version=app_version).count() > 0:
                        new_s = ServiceInfo.objects.get(service_key=service_key, version=app_version)
                        new_services.append(new_s)
                    else:
                        exist_new_services.append(service_key)
                else:
                    exist_t_s = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id, service_alias=service_alias)
                    exist_t_services.append(exist_t_s)

        return new_services, exist_t_services, exist_new_services

    def memory_choices(self):
        memory_dict = {}
        memory_dict["128"] = '128M'
        memory_dict["256"] = '256M'
        memory_dict["512"] = '512M'
        memory_dict["1024"] = '1G'
        memory_dict["2048"] = '2G'
        memory_dict["4096"] = '4G'
        memory_dict["8192"] = '8G'
        memory_dict["16384"] = '16G'
        memory_dict["32768"] = '32G'
        memory_dict["65536"] = '64G'
        return memory_dict

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
                # 没有服务模版，需要下载模版
                code, base_info, dep_map, error_msg = baseService.download_service_info(service_key, app_version)
                if code == 500:
                    logger.error(error_msg)
                    return self.redirect_to('/apps/{0}/service/'.format(self.tenant.tenant_name))
                else:
                    serviceObj = base_info

            context["service"] = serviceObj
            dependecy_services, dependecy_info, dependecy_version = self.find_dependecy_services(serviceObj)
            context["dependecy_services"] = dependecy_services
            context["dependecy_info"] = dependecy_info
            context["dependecy_version"] = dependecy_version
            context["tenantName"] = self.tenantName
            context["service_key"] = service_key
            context["app_version"] = app_version
            context["service_name"] = serviceObj.service_name
            sem = ServiceExtendMethod.objects.get(service_key=serviceObj.service_key, app_version=serviceObj.version)
            memoryList = []
            num = 1
            memoryList.append(str(sem.min_memory))
            next_memory = sem.min_memory * pow(2, num)
            while(next_memory <= sem.max_memory):
                memoryList.append(str(next_memory))
                num = num + 1
                next_memory = sem.min_memory * pow(2, num)

            context["memoryList"] = memoryList
            context["memorydict"] = self.memory_choices()
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/back_service_create_step_1.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        tenant_id = self.tenant.tenant_id
        service_id = make_uuid(tenant_id)
        service_alias = "gr"+service_id[-6:]
        result = {}
        try:
            # judge region tenant is init
            success = tenantRegionService.init_for_region(self.response_region, self.tenantName, tenant_id, self.user)
            if not success:
                result["status"] = "failure"
                return JsonResponse(result, status=200)

            if tenantAccountService.isOwnedMoney(self.tenant, self.response_region):
                result["status"] = "owed"
                return JsonResponse(result, status=200)

            if tenantAccountService.isExpired(self.tenant,self.service):
                result["status"] = "expired"
                return JsonResponse(result, status=200)

            service_key = request.POST.get("service_key", None)
            if service_key is None:
                result["status"] = "notexist"
                return JsonResponse(result, status=200)
            app_version = request.POST.get("app_version", None)
            if app_version is None:
                result["status"] = "notexist"
                return JsonResponse(result, status=200)

            service_cname = request.POST.get("create_service_name", None)
            if service_cname is None:
                result["status"] = "empty"
                return JsonResponse(result, status=200)

            # num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_cname=service_cname).count()
            # if num > 0:
            #     result["status"] = "exist"
            #     return JsonResponse(result, status=200)

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

            service_memory = request.POST.get("service_memory", "")
            if service_memory != "":
                cm = int(service_memory)
                if cm >= 128:
                    ccpu = int(cm / 128) * 20
                    service.min_cpu = ccpu
                    service.min_memory = cm

            dependency_service = request.POST.getlist("dependency_service")
            logger.debug(dependency_service)
            new_services, exist_t_services, exist_new_services = self.parse_dependency_service(dependency_service)

            if len(exist_new_services) > 0:
                result["status"] = "depend_service_notexit"
                return JsonResponse(result, status=200)

            if new_services:
                new_required_memory = reduce(lambda x, y: x + y, [s.min_memory for s in new_services])
            else:
                new_required_memory = 0

            # calculate resource
            tempService = TenantServiceInfo()
            tempService.min_memory = service.min_memory
            tempService.service_region = self.response_region
            tempService.min_node = service.min_node
            diffMemory = new_required_memory + service.min_memory
            rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, tempService, diffMemory, False)
            if not flag:
                if rt_type == "memory":
                    result["status"] = "over_memory"
                else:
                    result["status"] = "over_money"
                return JsonResponse(result, status=200)
            # create new service
            if new_services:
                for dep_service in new_services:
                    try:
                        dep_service_id = make_uuid(dep_service.service_key)
                        dep_service_alias="gr"+dep_service_id[-6:]
                        depTenantService = baseService.create_service(
                            dep_service_id, tenant_id, dep_service_alias, dep_service.service_name.lower() + "_" + service_cname, dep_service, self.user.pk, region=self.response_region)
                        monitorhook.serviceMonitor(self.user.nick_name, depTenantService, 'create_service', True)
                        self.copy_port_and_env(dep_service, depTenantService)
                        baseService.create_region_service(depTenantService, self.tenantName, self.response_region, self.user.nick_name)
                        monitorhook.serviceMonitor(self.user.nick_name, depTenantService, 'init_region_service', True)
                        baseService.create_service_dependency(tenant_id, service_id, dep_service_id, self.response_region)
                    except Exception as e:
                        logger.exception(e)

            # exist service dependency
            if exist_t_services:
                for t_service in exist_t_services:
                    try:
                        baseService.create_service_dependency(tenant_id, service_id, t_service.service_id, self.response_region)
                    except Exception as e:
                        logger.exception(e)

            # create console service
            newTenantService = baseService.create_service(
                service_id, tenant_id, service_alias, service_cname, service, self.user.pk, region=self.response_region)

            group_id = request.POST.get("select_group_id", "")
            # 创建关系
            if group_id != "":
                group_id = int(group_id)
                if group_id > 0:
                    ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                                                        tenant_id=self.tenant.tenant_id, region_name=self.response_region)

            monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)
            result["status"] = "success"
            result["service_id"] = service_id
            result["service_alias"] = service_alias
        except Exception as e:
            logger.exception(e)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service_id).delete()
            result["status"] = "failure"
        return JsonResponse(result, status=200)


class ServiceDeployExtraView(LeftSideBarMixin, AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/gr/basic.js', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/back-service-create.js')
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
            baseService.addServicePort(self.service, source_service.is_init_accout, container_port=port.container_port, protocol=port.protocol, port_alias=port.port_alias,
                                       is_inner_service=port.is_inner_service, is_outer_service=port.is_outer_service)

    def copy_volumes(self, tenant_service, source_service):
        volumes = AppServiceVolume.objects.filter(service_key=source_service.service_key, app_version=source_service.version)
        for volume in volumes:
            baseService.add_volume_list(tenant_service, volume.volume_path)

    # add by tanm specify tenant app default env
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

    def get(self, request, *args, **kwargs):
        context = self.get_context()
        envs = AppServiceEnv.objects.filter(service_key=self.service.service_key, app_version=self.service.version, container_port=0, is_change=True)
        outer_ports = AppServicePort.objects.filter(service_key=self.service.service_key,
                                                    app_version=self.service.version,
                                                    is_outer_service=True,
                                                    protocol='http')
        if envs:
            # add by tanm
            self.set_tenant_default_env(envs, outer_ports)
            # add end
            context['envs'] = envs
            return TemplateResponse(request, 'www/back_service_create_step_2.html', context)
        else:
            source_service = ServiceInfo.objects.get(service_key=self.service.service_key, version=self.service.version)
            self.copy_envs(source_service, [])
            self.copy_ports(source_service)
            # add volume
            self.copy_volumes(self.service, source_service)

            dep_sids = []
            tsrs = TenantServiceRelation.objects.filter(service_id=self.service.service_id)
            for tsr in tsrs:
                dep_sids.append(tsr.dep_service_id)

            baseService.create_region_service(self.service, self.tenantName, self.response_region, self.user.nick_name, dep_sids=json.dumps(dep_sids))
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'init_region_service', True)
            return self.redirect_to('/apps/{}/{}/detail/'.format(self.tenantName, self.serviceAlias))

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            data = Dict(data)
            source_service = ServiceInfo.objects.get(service_key=self.service.service_key, version=self.service.version)
            self.copy_envs(source_service, data.envs)
            self.copy_ports(source_service)
            # add volume
            self.copy_volumes(self.service, source_service)
            # create region tenantservice
            dep_sids = []
            tsrs = TenantServiceRelation.objects.filter(service_id=self.service.service_id)
            for tsr in tsrs:
                dep_sids.append(tsr.dep_service_id)

            baseService.create_region_service(self.service, self.tenantName, self.response_region, self.user.nick_name, dep_sids=json.dumps(dep_sids))
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'init_region_service', True)

        except Exception, e:
            logger.exception("service.create", e)
            return JsonResponse({"success": False, "info": u"内部错误"}, status=500)

        next_url = '/apps/{}/{}/detail/'.format(self.tenantName, self.serviceAlias)
        return JsonResponse({"success": True, "next_url": next_url}, status=200)
