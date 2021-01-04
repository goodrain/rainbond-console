# -*- coding: utf8 -*-
import logging
from .region_client.regionapibaseclient import RegionApiBaseHttpClient
from .api.tenants import Tenant

logger = logging.getLogger('default')


class RegionAPIFace:
    def __init__(self, region):
        self.api = RegionApiBaseHttpClient(region)
        self.tenants = Tenant(self.api)


def GetRegionAPI(region):
    return RegionAPIFace(region=region)
