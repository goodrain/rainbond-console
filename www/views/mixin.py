# -*- coding: utf8 -*-
from django.http import Http404
from www.service_http import RegionServiceApi
from www.models import PermRelTenant, Tenants

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
