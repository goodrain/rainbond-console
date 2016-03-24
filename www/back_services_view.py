# -*- coding: utf8 -*-
import json
from addict import Dict
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse
from www.views import AuthedView, LeftSideBarMixin, CopyPortAndEnvMixin
from www.decorator import perm_required
from www.models import (ServiceInfo, TenantRegionInfo, TenantServiceInfo, TenantServiceAuth, TenantServiceRelation, AppServiceInfo,
                        App, AppUsing, AppServicesPort, AppServiceEnvVar, TenantServicesPort, TenantServiceEnvVar)
from service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService
from www.monitorservice.monitorhook import MonitorHook
from www.utils.crypt import make_uuid

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()


class ServiceMarket(LeftSideBarMixin, AuthedView):

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/back-service-create.js')
        return media

    @never_cache
    @perm_required('tenant_access')
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            if self.user.is_sys_admin or "app_publish" in self.user.actions:
                cacheServiceList = ServiceInfo.objects.all()
            else:
                cacheServiceList = ServiceInfo.objects.filter(status="published")
            context["cacheServiceList"] = cacheServiceList
            context["serviceMarketStatus"] = "active"
            context["tenantName"] = self.tenantName
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
        if not bool(serviceObj.dependecy):
            return {}
        else:
            tenant_id = self.tenant.tenant_id
            dependecy_keys = serviceObj.dependecy.split(',')
            deployTenantServices = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_key__in=dependecy_keys, service_region=self.response_region)
            dependecy_services = dict((el, []) for el in dependecy_keys)
            for s in deployTenantServices:
                dependecy_services[s.service_key].append(s)
            return dependecy_services

    def parse_dependency_service(self, dependency_service):
        new_services = []
        exist_t_services = []
        for string in dependency_service:
            service_alias, service_key = string.split('.', 1)
            if service_alias == '__new__':
                new_s = ServiceInfo.objects.get(service_key=service_key)
                new_services.append(new_s)
            else:
                exist_t_s = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id, service_alias=service_alias)
                exist_t_services.append(exist_t_s)

        return new_services, exist_t_services

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

            context["serviceMarketStatus"] = "active"

            serviceObj = ServiceInfo.objects.get(service_key=service_key)
            context["service"] = serviceObj
            context["dependecy_services"] = self.find_dependecy_services(serviceObj)
            context["tenantName"] = self.tenantName
            context["service_key"] = service_key
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/back_service_create_step_1.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        service_alias = ""
        tenant_id = self.tenant.tenant_id
        service_id = make_uuid(tenant_id)
        result = {}
        try:
            if tenantAccountService.isOwnedMoney(self.tenant, self.response_region):
                result["status"] = "owed"
                return JsonResponse(result, status=200)

            service_key = request.POST.get("service_key", None)
            if service_key is None:
                result["status"] = "notexist"
                return JsonResponse(result, status=200)

            service_alias = request.POST.get("create_service_name", None)
            if service_alias is None:
                result["status"] = "empty"
                return JsonResponse(result, status=200)

            service_alias = service_alias.lower()
            num = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_alias=service_alias).count()
            if num > 0:
                result["status"] = "exist"
                return JsonResponse(result, status=200)

            service = ServiceInfo.objects.get(service_key=service_key)
            service_memory = request.POST.get("service_memory", "")
            if service_memory != "":
                cm = int(service_memory)
                if cm >= 128:
                    ccpu = int(cm / 128) * 20
                    service.min_cpu = ccpu
                    service.min_memory = cm
            logger.debug(service.min_memory)

            dependency_service = request.POST.getlist("dependency_service")
            logger.debug(dependency_service)
            new_services, exist_t_services = self.parse_dependency_service(dependency_service)

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
                        depTenantService = baseService.create_service(
                            dep_service_id, tenant_id, dep_service.service_key + "_" + service_alias, dep_service, self.user.pk, region=self.response_region)
                        monitorhook.serviceMonitor(self.user.nick_name, depTenantService, 'create_service', True)
                        self.copy_port_and_env(dep_service, depTenantService)
                        baseService.create_region_service(depTenantService, self.tenantName, self.response_region, self.user.nick_name)
                        monitorhook.serviceMonitor(self.user.nick_name, depTenantService, 'init_region_service', True)
                        # baseService.create_service_env(tenant_id, dep_service_id, self.response_region)
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
                service_id, tenant_id, service_alias, service, self.user.pk, region=self.response_region)

            if service.category == 'app_publish':
                newTenantService = self.update_app_service(service, newTenantService)

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

    def update_app_service(self, service, newTenantService):
        with transaction.atomic():
            appversion = AppServiceInfo.objects.defer('change_log').get(service_key=service.service_key, app_version=service.version, update_version=service.update_version)
            appversion.deploy_num += 1
            appversion.view_num += 1
            appversion.save(update_fields=['deploy_num', 'view_num'])

        try:
            app = App.objects.get(service_key=service.service_key)
        except App.DoesNotExist:
            pass
        else:
            app_use, created = AppUsing.objects.get_or_create(app_id=app.pk, user_id=self.user.pk)
            app_use.install_count = app_use.install_count + 1
            app_use.save()

        newTenantService, update_fields = self.copy_properties(appversion, newTenantService)
        newTenantService.save(update_fields=update_fields)
        return newTenantService

    def copy_properties(self, copy_from, to):
        update_fields = []
        for field in ('deploy_version', 'update_version', 'cmd', 'setting', 'image', 'dependecy', 'env', 'service_type'):
            if hasattr(to, field) and hasattr(copy_from, field):
                to_value = getattr(to, field)
                from_value = getattr(copy_from, field)
                if to_value != from_value:
                    setattr(to, field, from_value)
                    update_fields.append(field)
        return to, update_fields


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
        for env in envs:
            source_env = AppServiceEnvVar.objects.get(service_key=s.service_key, app_version=s.version,
                                                      update_version=s.update_version, attr_name=env.attr_name)
            baseService.saveServiceEnvVar(s.tenant_id, s.service_id, source_env.container_port, source_env.name,
                                          env.attr_name, env.attr_value, source_env.is_change, source_env.scope)

        for sys_env in AppServiceEnvVar.objects.filter(service_key=s.service_key, app_version=s.version,
                                                       update_version=s.update_version, container_port__lt=0):
            baseService.saveServiceEnvVar(s.tenant_id, s.service_id, sys_env.container_port, sys_env.name,
                                          sys_env.attr_name, sys_env.attr_value, sys_env.is_change, sys_env.scope)

    def copy_ports(self, source_service):
        if self.service.category in ("app_publish", "app_sys_publish"):
            AppPorts = AppServicesPort.objects.filter(service_key=self.service.service_key, app_version=self.service.version, update_version=self.service.update_version)
        else:
            AppPorts = AppServicesPort.objects.filter(service_key=self.service.service_key)
        baseService = BaseTenantService()
        for port in AppPorts:
            baseService.addServicePort(self.service, source_service.is_init_accout, container_port=port.container_port, protocol=port.protocol, port_alias=port.port_alias,
                                       is_inner_service=port.is_inner_service, is_outer_service=port.is_outer_service)

    def get(self, request, *args, **kwargs):
        context = self.get_context()
        envs = AppServiceEnvVar.objects.filter(service_key=self.service.service_key, app_version=self.service.version, update_version=self.service.update_version, container_port=0)
        if envs:
            context['envs'] = envs
            return TemplateResponse(request, 'www/back_service_create_step_2.html', context)
        else:
            source_service = ServiceInfo.objects.get(service_key=self.service.service_key)
            self.copy_envs(source_service, [])
            self.copy_ports(source_service)
            baseService.create_region_service(self.service, self.tenantName, self.response_region, self.user.nick_name)
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'init_region_service', True)
            return self.redirect_to('/apps/{}/{}/detail/'.format(self.tenantName, self.serviceAlias))

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            data = Dict(data)
            source_service = ServiceInfo.objects.get(service_key=self.service.service_key)
            self.copy_envs(source_service, data.envs)
            self.copy_ports(source_service)
            # create region tenantservice
            baseService.create_region_service(self.service, self.tenantName, self.response_region, self.user.nick_name)
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'init_region_service', True)

        except Exception, e:
            logger.exception("service.create", e)
            return JsonResponse({"success": False, "info": u"内部错误"}, status=500)

        next_url = '/apps/{}/{}/detail/'.format(self.tenantName, self.serviceAlias)
        return JsonResponse({"success": True, "next_url": next_url}, status=200)
