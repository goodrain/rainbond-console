# -*- coding: utf8 -*-
from www.service_http import RegionServiceApi

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
