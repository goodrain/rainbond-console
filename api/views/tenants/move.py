# -*- coding: utf8 -*-
import datetime
import logging

from www.apiclient.regionapi import RegionInvokeApi
from www.tenantservice.baseservice import BaseTenantService

logger = logging.getLogger('default')

region_api = RegionInvokeApi()
baseService = BaseTenantService()


def make_deploy_version():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

