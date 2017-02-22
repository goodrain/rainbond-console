# -*- coding: utf8 -*-
from django.http import Http404
from www.service_http import RegionServiceApi
from www.models import PermRelTenant, Tenants, AppServicePort, AppServiceEnv, AppServiceVolume, ServiceGroup
from www.tenantservice.baseservice import BaseTenantService
from www.region import RegionInfo
from www.utils import sn
from www.models.activity import TenantActivity
import logging
logger = logging.getLogger('default')


class RegionOperateMixin(object):

    def init_for_region(self, region, tenant_name, tenant_id):
        api = RegionServiceApi()
        logger.info("account.register", "create tenant {0} with tenant_id {1} on region {2}".format(tenant_name, tenant_id, region))
        try:
            res, body = api.create_tenant(region, tenant_name, tenant_id)
            return True
        except api.CallApiError, e:
            logger.error("account.register", "create tenant {0} failed".format(tenant_name))
            logger.exception("account.register", e)
            return False


class LoginRedirectMixin(object):

    def redirect_view(self, request=None):
        user_id = request.user.pk if request is not None else self.user.pk
        tenants_has = PermRelTenant.objects.filter(user_id=user_id)

        if tenants_has:
            tenant_pk = tenants_has[0].tenant_id
            tenant = Tenants.objects.get(pk=tenant_pk)
            tenant_name = tenant.tenant_name
            return self.redirect_to('/apps/{0}/'.format(tenant_name))
        else:
            logger.error('account.login_error', 'user {0} with id {1} has no tenants to redirect login'.format(
                self.user.nick_name, self.user.pk))
            return Http404


class CopyPortAndEnvMixin(object):

    def copy_port_and_env(self, service, new_service):
        ports = AppServicePort.objects.filter(service_key=service.service_key, app_version=service.version)
        envs = AppServiceEnv.objects.filter(service_key=service.service_key, app_version=service.version)
        volumes = AppServiceVolume.objects.filter(service_key=service.service_key, app_version=service.version)
        baseService = BaseTenantService()
        for port in ports:
            baseService.addServicePort(new_service, service.is_init_accout, container_port=port.container_port, protocol=port.protocol, port_alias=port.port_alias,
                                       is_inner_service=port.is_inner_service, is_outer_service=port.is_outer_service)
        for env in envs:
            baseService.saveServiceEnvVar(new_service.tenant_id, new_service.service_id, env.container_port, env.name, env.attr_name, env.attr_value, env.is_change, env.scope)

        for volume in volumes:
            baseService.add_volume_list(new_service, volume.volume_path)


class LeftSideBarMixin(object):

    def __init__(self, *args, **kwargs):
        super(LeftSideBarMixin, self).__init__(*args, **kwargs)
        if hasattr(self, 'tenant') and hasattr(self, 'user'):
            pass
        else:
            raise ImportWarning(
                "LeftSideBarMixin should inherit before AuthedView")

        self.cookie_region = self.request.COOKIES.get('region', None)
        self.response_region = self.tenant.region if self.cookie_region is None else self.cookie_region
        self.cookie_tenant_name = self.request.COOKIES.get('tenant_name', None)
        self.response_tenant_name = self.tenant.tenant_name if self.cookie_tenant_name is None else self.cookie_tenant_name

    def update_response(self, response):
        if self.response_region != self.cookie_region:
            response.set_cookie('region', self.response_region)
        if self.response_tenant_name != self.cookie_tenant_name:
            response.set_cookie('tenant_name', self.response_tenant_name)
        return response

    def get_context(self):
        context = super(LeftSideBarMixin, self).get_context()
        context['tenantServiceList'] = self.get_service_list()
        context["groupList"] = self.get_group_list()
        context["tenant_list"] = self.get_user_tenant(self.user.pk)
        context["current_tenant"]= self.tenant.tenant_name
        context["is_private"] = sn.instance.is_private()
        context["cloud_assistant"] = sn.instance.cloud_assistant
        context = self.set_region_info(context)
        return context

    def set_region_info(self, context):
        arrival_regions = []
        for region in RegionInfo.region_list:
            if region['name'] == self.response_region:
                context['current_region'] = region
            else:
                if region['name'] == 'aws-bj-1':
                    if self.tenant.region != 'aws-bj-1':
                        continue
                if self.user.origion in ('ucloud',):
                    continue
                arrival_regions.append(region)
        # 判断租户是否在998活动中
        if self.tenant is not None:
            ta_num = TenantActivity.objects.filter(tenant_id=self.tenant.tenant_id).count()
            if ta_num > 0:
                arrival_regions = [RegionInfo.region_list[0]]
                context['current_region'] = RegionInfo.region_list[0]
                context['activity_id'] = 998

        context['arrival_regions'] = tuple(arrival_regions)
        return context

    def get_service_list(self):
        baseService = BaseTenantService()
        services = baseService.get_service_list(
            self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region)
        services = list(services)
        for s in services:
            if s.service_alias == self.serviceAlias:
                s.is_selected = True
                services.insert(0, s)
                services.remove(s)
                break
        return services
    
    def get_group_list(self):
        grouplist = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region)
        return grouplist

    def get_user_tenant(self,user_id):
        """根据用户的ID获取当前用户的所有租户信息"""
        prt_list = PermRelTenant.objects.filter(user_id=user_id)
        tenant_id_list = [x.tenant_id for x in prt_list]
        # 查询租户信息
        tenant_list = Tenants.objects.filter(pk__in=tenant_id_list)
        return tenant_list