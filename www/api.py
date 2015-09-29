# -*- coding: utf8 -*-
import json
from django.conf import settings
from goodrain_web.base import BaseHttpClient


class RegionApi(BaseHttpClient):

    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Content-Type': 'application/json', "Authorization": "Token 5ca196801173be06c7e6ce41d5f7b3b8071e680a"}
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


class OpentsdbApi(BaseHttpClient):

    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.region_map = settings.OPENTSDB_API

    def query(self, region, metric, start='15m-ago', aggregate='sum', **tags):
        base_url = self.region_map[region]
        url = '{0}?start={1}&m={2}:{3}'.format(base_url, start, aggregate, metric)
        if tags:
            tag = '{' + ','.join(map(lambda (x, y): '{0}={1}'.format(x, y), tags.items())) + '}'
            url += tag
        res, body = self._get(url)
        return body.dps
