# -*- coding: utf8 -*-
import json
from django.conf import settings
from goodrain_web.utils import BaseHttpClient


class RegionApi(BaseHttpClient):
    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Content-Type': 'application/json'}
        region_info = settings.REGION_SERVICE_API
        for k, v in region_info.items():
            setattr(self, k, v)

    def get_tenants(self):
        url = self.url + '/v1/tenants'
        res, body = self._get(url, self.default_headers)
        return res, body

    def create_tenant(self, tenant_name, tenant_id):
        url = self.url + '/v1/tenants'
        data = {"tenant_id": tenant_id, "tenant_name": tenant_name}
        res, body = self._post(url, self.default_headers, json.dumps(data))
        return res, body
