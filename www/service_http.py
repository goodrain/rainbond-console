# -*- coding: utf8 -*-
import json
from django.conf import settings

from goodrain_web.base import BaseHttpClient, httplib2

import logging
from www.utils.conf_tool import regionConfig

logger = logging.getLogger('default')


class RegionServiceApi(BaseHttpClient):
    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {
            'Connection': 'keep-alive',
            'Content-Type': 'application/json'
        }
        # if settings.MODULES["RegionToken"]:
        #     self.default_headers.update({
        #         "Authorization": settings.REGION_TOKEN
        #     })
        # self.region_map = {}
        # region_service_infos = regionConfig.region_service_api()
        # # region_service_infos = settings.REGION_SERVICE_API
        # for region_service_info in region_service_infos:
        #     client_info = {"url": region_service_info["url"]}
        #     token = region_service_info.get("token", None)
        #     client_info['token'] = token
        #
        #     if 'proxy' in region_service_info and region_service_info.get(
        #             'proxy_priority', False) is True:
        #         client_info['client'] = self.make_proxy_http(
        #             region_service_info)
        #     else:
        #         client_info['client'] = httplib2.Http(timeout=5)
        #     self.region_map[region_service_info["region_name"]] = client_info

    def make_proxy_http(self, region_service_info):
        proxy_info = region_service_info['proxy']
        if proxy_info['type'] == 'http':
            proxy_type = httplib2.socks.PROXY_TYPE_HTTP_NO_TUNNEL
        else:
            raise TypeError("unsupport type: %s" % proxy_info['type'])

        proxy = httplib2.ProxyInfo(proxy_type, proxy_info['host'],
                                   proxy_info['port'])
        client = httplib2.Http(proxy_info=proxy, timeout=25)
        return client

    def get_region_map(self, region):
        region_service_infos = regionConfig.region_service_api()
        region_map = {}
        for region_service_info in region_service_infos:
            client_info = {"url": region_service_info["url"]}
            token = region_service_info.get("token", None)
            client_info['token'] = token
            if 'proxy' in region_service_info and region_service_info.get(
                    'proxy_priority', False) is True:
                client_info['client'] = self.make_proxy_http(
                    region_service_info)
            else:
                client_info['client'] = httplib2.Http(timeout=5)

            region_map[region_service_info["region_name"]] = client_info
        return region_map

    def _set_headers(self, token):
        if settings.MODULES["RegionToken"]:
            if not token:
                self.default_headers.update({
                    "Authorization": settings.REGION_TOKEN
                })
            else:
                self.default_headers.update({
                    "Authorization": token
                })

    def check_region_status(self, region, region_url, token):
        url = region_url + "/v1/check_region"
        self._set_headers(token)
        try:
            res, body = self._get(url, self.default_headers, region=region)
        except Exception as e:
            logger.error("cannot get status")
            body = {"ok": False}
        return body

    def create_service(self, region, tenant, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/tenants/" + tenant + "/services"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def update_service(self, region, service_id, data):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/" + service_id
        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, json.dumps(data), region=region)
        return res, body

    def build_service(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/build/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def check_service_status(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/status/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def get_service_status(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/status/"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def deploy(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/deploy/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def restart(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/restart/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def start(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/start/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return res, body

    def stop(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/stop/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def delete(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/delete/"
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def check_status(self, region, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/status/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def get_log(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/log/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def get_userlog(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/userlog/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def get_compile_log(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/compile-log/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def verticalUpgrade(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/vertical/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def horizontalUpgrade(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/horizontal/"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def addUserDomain(self, region, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/lb/user-domains"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def deleteUserDomain(self, region, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/lb/delete-domains-rule"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def changeMemory(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/" + service_id + "/language"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def pause(self, region, tenant_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/pause"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def unpause(self, region, tenant_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/unpause"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def writeToRegionBeanstalk(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/beanstalk/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def createServiceDependency(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/dependency/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def cancelServiceDependency(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/dependency/"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def createL7Conf(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/l7_conf/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def createServiceEnv(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/env-var/"
        logger.debug("api.region", "function: {0}, {1}".format(
            'createServiceEnv', url))
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def getTenantRunningServiceId(self, region, tenant_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/running-service"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def systemPause(self, region, tenant_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/system-pause"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def systemUnpause(self, region, tenant_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/tenants/" + tenant_id + "/system-unpause"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def findMappingPort(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/port-mapping/"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def bindingMappingPortIp(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/port-mapping/"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def manageServicePort(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/ports"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def opentsdbQuery(self, region, start, queries):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/statistic/opentsdb/query"
        data = {"start": start, "queries": queries}
        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(data), region=region)
        try:
            dps = body[0]['dps']
            return dps
        except IndexError:
            logger.info('tsdb_query', "request: {0}".format(url))
            logger.info('tsdb_query', "response: {0} ====== {1}".format(
                res, body))
            return None

    def create_tenant(self, region, tenant_name, tenant_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + '/v1/tenants'
        data = {"tenant_id": tenant_id, "tenant_name": tenant_name}
        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(data), region=region)
        return res, body

    def send_service_exec(self, region, tenant_id, service_id, run_exec, method):
        url = self.region_map[region]['url'] + '/v1/execrun'
        data = {"tenant_id": tenant_id, "service_id": service_id, "run_exec": run_exec, "method": method}
        res, body = self._post(url, self.default_headers, json.dumps(data), region=region)
        return res, body

    def getLatestServiceEvent(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/latest-event/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return body

    def rollback(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/roll-back/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def send_task(self, region, topic, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/queue?topic=" + topic
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def create_event(self, region, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/events"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def history_log(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/statistic/log/" + service_id + "/list"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def latest_log(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/statistic/log/" + service_id + "/last"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, body, region=region)
        return body

    def createServiceMnt(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/mnt/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def cancelServiceMnt(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/mnt/"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def createServicePort(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/port-var/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def extendMethodUpgrade(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/extend-method/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def serviceContainerIds(self, region, service_id, body=None):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/containerIds/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def createServiceVolume(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/volume/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return res, body

    def cancelServiceVolume(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/volume/"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return res, body

    def _get_region_request_info(self, region):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        return token, region_map[region]['url']

    def add_volume_v2(self, region, tenant_name, service_alias, body):
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes".format(tenant_name, service_alias)
        self._set_headers(token)
        return self._post(url, self.default_headers, body)

    def delete_volume_v2(self, region, tenant_name, service_alias, volume_name):
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes/{2}".format(tenant_name, service_alias, volume_name)
        self._set_headers(token)
        return self._delete(url, self.default_headers)

    def add_dep_volume_v2(self, region, tenant_name, service_alias, body):
        """ Add dependent volumes """
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body)
        return res, body

    def delete_dep_volume_v2(self, region, tenant_name, service_alias, body):
        """ Delete dependent volume"""
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(tenant_name, service_alias)
        self._set_headers(token)
        return self._delete(url, self.default_headers, body)

    # 服务对外端口开启类型
    def mutiPortSupport(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/multi-outer-port/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return res, body

    # 服务挂载卷类型
    def mntShareSupport(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/mnt-share-type/"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return res, body

    def tenantServiceStats(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/container-stats/"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def monitoryQueryMem(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/monitor/container/query/mem/" + service_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def monitoryQueryCPU(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/monitor/container/query/cpu/" + service_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def monitoryQueryFS(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/monitor/container/query/fs/" + service_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def monitoryQueryIO(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/monitor/container/query/io/" + service_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def getEventLog(self, region, event_id, level):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/event/" + event_id + "/log?level=" + level
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def deleteEventLog(self, region, event_ids):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/events/log"
        self._set_headers(token)
        res, body = self._delete(
            url, self.default_headers, body=event_ids, region=region)
        return body

    def getDockerLogInstance(self, region, service_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/log/" + service_id + "/instance"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def updateServiceProbe(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/probe"
        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, region=region, body=body)
        return body

    def addServiceProbe(self, region, service_id, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/probe"
        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=body)
        return body

    def daleteServiceProbe(self, region, service_id, probe_id):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/services/lifecycle/" + service_id + "/probe"
        self._set_headers(token)
        res, body = self._delete(
            url,
            self.default_headers,
            region=region,
            body={"probe_id": probe_id})
        return body

    def getRegionResource(self, region, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/statistic/region-memory"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, body=body)
        return body

    def getTenantsResource(self, region, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v1/statistic/tenants-memory"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def bindDomain(self, region, tenant_name, service_alias, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/domains"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def unbindDomain(self, region, tenant_name, service_alias, body):
        data = json.loads(body)
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/domains/" + data[
                  "domain"]
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, body, region=region)
        return body

    def addServiceNodeLabel(self, region, tenant_name, service_alias, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/node-label"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def deleteServiceNodeLabel(self, region, tenant_name, service_alias, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/node-label"
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, body, region=region)
        return body

    def add_service_state_label(self, region, tenant_name, service_alias, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/service-label"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def update_service_state_label(self, region, tenant_name, service_alias, body):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/service-label"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body
