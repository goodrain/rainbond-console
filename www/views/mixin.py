# -*- coding: utf8 -*-
from django.http import Http404
from www.service_http import RegionServiceApi
from www.models import PermRelTenant, Tenants
from www.tenantservice.baseservice import BaseTenantService
from www.region import RegionInfo

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

    def redirect_view(self):
        tenants_has = PermRelTenant.objects.filter(user_id=self.user.pk)
        if tenants_has:
            tenant_pk = tenants_has[0].tenant_id
            tenant = Tenants.objects.get(pk=tenant_pk)
            tenant_name = tenant.tenant_name
            return self.redirect_to('/apps/{0}/'.format(tenant_name))
        else:
            logger.error('account.login_error', 'user {0} with id {1} has no tenants to redirect login'.format(
                self.user.nick_name, self.user.pk))
            return Http404


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

    def update_response(self, response):
        if self.response_region != self.cookie_region:
            response.set_cookie('region', self.response_region)
        return response

    def get_context(self):
        context = super(LeftSideBarMixin, self).get_context()
        context['tenantServiceList'] = self.get_service_list()
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

        context['arrival_regions'] = tuple(arrival_regions)
        return context

    def get_service_list(self):
        baseService = BaseTenantService()
        services = baseService.get_service_list(
            self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region)
        for s in services:
            if s.service_alias == self.serviceAlias:
                s.is_selected = True
                break

        return services
