import json
from django.conf import settings

from goodrain_web.base import BaseHttpClient

import logging

logger = logging.getLogger('default')


class RegionServiceApi(BaseHttpClient):

    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json',
                                "Authorization": "Token 5ca196801173be06c7e6ce41d5f7b3b8071e680a"}
        self.region_map = {}
        region_service_infos = settings.REGION_SERVICE_API
        for region_service_info in region_service_infos:
            self.region_map[region_service_info["region_name"]] = region_service_info["url"]

    def create_service(self, region, tenant, body):
        url = self.region_map[region] + "/v1/tenants/" + tenant + "/services"
        res, body = self._post(url, self.default_headers, body)
        return body

    def update_service(self, region, service_id, data):
        url = self.region_map[region] + "/v1/services/" + service_id
        res, body = self._put(url, self.default_headers, json.dumps(data))
        return res, body

    def build_service(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/build/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def check_service_status(self, region, service_id):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/status/"
        res, body = self._post(url, self.default_headers)
        return body

    def restart(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/restart/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def stop(self, region, service_id):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/stop/"
        res, body = self._post(url, self.default_headers)
        return body

    def delete(self, region, service_id):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/delete/"
        res, body = self._delete(url, self.default_headers)
        return body

    def check_status(self, region, body):
        url = self.region_map[region] + "/v1/services/lifecycle/status/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def get_log(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/log/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def get_userlog(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/userlog/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def verticalUpgrade(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/vertical/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def horizontalUpgrade(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/horizontal/"
        res, body = self._put(url, self.default_headers, body)
        return body

    def addUserDomain(self, region, body):
        url = self.region_map[region] + "/v1/lb/user-domains"
        res, body = self._post(url, self.default_headers, body)
        return body

    def changeMemory(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/" + service_id + "/language"
        res, body = self._post(url, self.default_headers, body)
        return body

    def pause(self, region, tenant_id):
        url = self.region_map[region] + "/v1/tenants/" + tenant_id + "/pause"
        res, body = self._post(url, self.default_headers)
        return body

    def unpause(self, region, tenant_id):
        url = self.region_map[region] + "/v1/tenants/" + tenant_id + "/unpause"
        res, body = self._post(url, self.default_headers)
        return body

    def writeToRegionBeanstalk(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/beanstalk/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def createServiceDependency(self, region, service_id, body):
        url = self.region_map[region] + "/v1/etcd/" + service_id + "/manage"
        res, body = self._post(url, self.default_headers, body)
        return body

    def cancelServiceDependency(self, region, service_id, body):
        url = self.region_map[region] + "/v1/etcd/" + service_id + "/manage"
        res, body = self._put(url, self.default_headers, body)
        return body

    def deleteEtcdService(self, region, service_id, body):
        url = self.region_map[region] + "/v1/etcd/" + service_id + "/manage"
        res, body = self._delete(url, self.default_headers, body)
        return body

    def getTenantRunningServiceId(self, region, tenant_id):
        url = self.region_map[region] + "/v1/tenants/" + tenant_id + "/running-service"
        res, body = self._post(url, self.default_headers)
        return body["data"]

    def updateTenantServiceStatus(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/status-update/"
        res, body = self._post(url, self.default_headers, body)
        return body["old_status"]
