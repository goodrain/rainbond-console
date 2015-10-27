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

    def deploy(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/deploy/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def restart(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/restart/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def stop(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/stop/"
        res, body = self._post(url, self.default_headers, body)
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

    def get_userlog(self, region, service_id):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/userlog/"
        res, body = self._post(url, self.default_headers)
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

    def deleteUserDomain(self, region, body):
        url = self.region_map[region] + "/v1/lb/delete-domains-rule"
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
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/dependency/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def cancelServiceDependency(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/dependency/"
        res, body = self._put(url, self.default_headers, body)
        return body

    def createServiceEnv(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/env-var/"
        logger.debug("api.region", "function: {0}, {1}".format('createServiceEnv', url))
        res, body = self._post(url, self.default_headers, body)
        return body

    def getTenantRunningServiceId(self, region, tenant_id):
        url = self.region_map[region] + "/v1/tenants/" + tenant_id + "/running-service"
        res, body = self._post(url, self.default_headers)
        return body

    def updateTenantServiceStatus(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/status-update/"
        res, body = self._post(url, self.default_headers, body)
        return body["old_status"]

    def systemPause(self, region, tenant_id):
        url = self.region_map[region] + "/v1/tenants/" + tenant_id + "/system-pause"
        res, body = self._post(url, self.default_headers)
        return body

    def systemUnpause(self, region, tenant_id):
        url = self.region_map[region] + "/v1/tenants/" + tenant_id + "/system-unpause"
        res, body = self._post(url, self.default_headers)
        return body

    def modifyServiceProtocol(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/port-mapping/"
        res, body = self._post(url, self.default_headers, body)
        return body

    def findMappingPort(self, region, service_id):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/port-mapping/"
        res, body = self._get(url, self.default_headers)
        return body

    def bindingMappingPortIp(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/port-mapping/"
        res, body = self._put(url, self.default_headers, body)
        return body

    def opentsdbQuery(self, region, start, queries):
        url = self.region_map[region] + "/v1/statistic/opentsdb/query"
        data = {"start": start, "queries": queries}
        res, body = self._post(url, self.default_headers, json.dumps(data))
        try:
            dps = body[0]['dps']
            return dps
        except IndexError:
            logger.info('tsdb_query', "request: {0}".format(url))
            logger.info('tsdb_query', "response: {0} ====== {1}".format(res, body))
            return None

    def get_tenants(self, region):
        url = self.region_map[region] + '/v1/tenants'
        res, body = self._get(url, self.default_headers)
        return res, body

    def create_tenant(self, region, tenant_name, tenant_id):
        url = self.region_map[region] + '/v1/tenants'
        data = {"tenant_id": tenant_id, "tenant_name": tenant_name}
        res, body = self._post(url, self.default_headers, json.dumps(data))
        return res, body
    
    def getLatestServiceEvent(self, region, service_id):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/latest-event/"
        res, body = self._post(url, self.default_headers)
        return body
    
    def rollback(self, region, service_id, body):
        url = self.region_map[region] + "/v1/services/lifecycle/" + service_id + "/roll-back/"
        res, body = self._post(url, self.default_headers, body)
        return body
