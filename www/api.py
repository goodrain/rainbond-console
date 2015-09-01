# -*- coding: utf8 -*-
import json
from django.conf import settings
from goodrain_web.base import BaseHttpClient


class RegionApi(BaseHttpClient):
    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Content-Type': 'application/json'}
        self.region_map = {}
        region_service_infos = settings.REGION_SERVICE_API
        for region_service_info in region_service_infos:
            self.region_map[region_service_info["region_name"]] = region_service_info["url"]

    def get_tenants(self, region):
        url = self.region_map[region] + '/v1/tenants'
        res, body = self._get(url, self.default_headers)
        return res, body

    def create_tenant(self, region, tenant_name, tenant_id):
        url = self.region_map[region] + '/v1/tenants'
        data = {"tenant_id": tenant_id, "tenant_name": tenant_name}
        res, body = self._post(url, self.default_headers, json.dumps(data))
        return res, body
