import json
from django.conf import settings

from goodrain_web.base import BaseHttpClient, httplib2

import logging

logger = logging.getLogger('default')


class AppServiceApi(BaseHttpClient):

    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json'}
        self.url = settings.APP_SERVICE_API["url"]

    def publishServiceData(self, body):
        url = self.url + "/api/v0/services/published"
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def addUserDomain(self, region, body):
        url = self.region_map[region]['url'] + "/v1/lb/user-domains"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def deleteUserDomain(self, region, body):
        url = self.region_map[region]['url'] + "/v1/lb/delete-domains-rule"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def changeMemory(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/" + service_id + "/language"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def pause(self, region, tenant_id):
        url = self.region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/pause"
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def unpause(self, region, tenant_id):
        url = self.region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/unpause"
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def writeToRegionBeanstalk(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/beanstalk/"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def createServiceDependency(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/dependency/"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def cancelServiceDependency(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/dependency/"
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def createServiceEnv(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/env-var/"
        logger.debug("api.region", "function: {0}, {1}".format('createServiceEnv', url))
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def getTenantRunningServiceId(self, region, tenant_id):
        url = self.region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/running-service"
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def systemPause(self, region, tenant_id):
        url = self.region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/system-pause"
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def systemUnpause(self, region, tenant_id):
        url = self.region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/system-unpause"
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def findMappingPort(self, region, service_id):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/port-mapping/"
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def bindingMappingPortIp(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/port-mapping/"
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def manageServicePort(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/ports"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def opentsdbQuery(self, region, start, queries):
        url = self.region_map[region]['url'] + "/v1/statistic/opentsdb/query"
        data = {"start": start, "queries": queries}
        res, body = self._post(url, self.default_headers, json.dumps(data), region=region)
        try:
            dps = body[0]['dps']
            return dps
        except IndexError:
            logger.info('tsdb_query', "request: {0}".format(url))
            logger.info('tsdb_query', "response: {0} ====== {1}".format(res, body))
            return None

    def get_tenants(self, region):
        url = self.region_map[region]['url'] + '/v1/tenants'
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def create_tenant(self, region, tenant_name, tenant_id):
        url = self.region_map[region]['url'] + '/v1/tenants'
        data = {"tenant_id": tenant_id, "tenant_name": tenant_name}
        res, body = self._post(url, self.default_headers, json.dumps(data), region=region)
        return res, body

    def getLatestServiceEvent(self, region, service_id):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/latest-event/"
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def rollback(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/roll-back/"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def send_task(self, region, topic, body):
        url = self.region_map[region]['url'] + "/v1/queue?topic=" + topic
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def create_event(self, region, body):
        url = self.region_map[region]['url'] + "/v1/events"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def history_log(self, region, service_id):
        url = self.region_map[region]['url'] + "/v1/statistic/log/" + service_id + "/list"
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def latest_log(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/statistic/log/" + service_id + "/last"
        res, body = self._get(url, self.default_headers, body, region=region)
        return body
    
    def createServiceMnt(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/mnt/"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def cancelServiceMnt(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/mnt/"
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def createServicePort(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/port-var/"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body
    
    def extendMethodUpgrade(self, region, service_id, body):
        url = self.region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/extend-method/"
        res, body = self._post(url, self.default_headers, body, region=region)
        return body
    