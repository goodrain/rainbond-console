# -*- coding: utf8 -*-
import json
from django.conf import settings

import httplib2

import logging

from www.apiclient.baseclient import HttpClient
from www.utils.conf_tool import regionConfig

logger = logging.getLogger('default')


class RegionInvokeApi(HttpClient):
    def __init__(self, *args, **kwargs):
        HttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {
            'Connection': 'keep-alive',
            'Content-Type': 'application/json'
        }

    def _get_region_request_info(self, region):
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        return token, region_map[region]['url']

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

    def get_all_tenant_resources(self, region):
        """获取所有租户的资源使用情况"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/resources/tenants"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_tenant_resources(self, region, tenant_name):
        """获取指定租户的资源使用情况"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/resources"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def create_tenant(self, region, tenant_name, tenant_id):
        """创建租户"""
        region_map = self.get_region_map(region)
        data = {"tenant_id": tenant_id, "tenant_name": tenant_name}
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return body

    def create_service(self, region, tenant_name, body):
        """创建应用"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def get_service_info(self, region, tenant_name, service_alias):
        """获取应用信息"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def update_service(self, region, tenant_name, service_alias, body):
        """更新应用"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=body)
        return body

    def delete_service(self, region, tenant_name, service_alias):
        """删除应用"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def build_service(self, region, tenant_name, service_alias, body):
        """应用构建"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/build"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def code_check(self, region, tenant_name, body):
        """代码检测"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/code-check"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def add_service_dependency(self, region, tenant_name, service_alias, body):
        """增加服务依赖"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/dependency"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def delete_service_dependency(self, region, tenant_name, service_alias, body):
        """取消服务依赖"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/dependency"
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region, body=body)
        return body

    def add_service_env(self, region, tenant_name, service_alias, body):
        """添加环境变量"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/env"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def delete_service_env(self, region, tenant_name, service_alias, body):
        """删除环境变量"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/env"
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region, body=body)
        return body

    def horizontal_upgrade(self, region, tenant_name, service_alias, body):
        """服务水平伸缩"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/horizontal"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=body)
        return body

    def vertical_upgrade(self, region, tenant_name, service_alias, body):
        """服务垂直伸缩"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/vertical"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=body)
        return body

    def change_memory(self, region, tenant_name, service_alias, body):
        """根据应用语言设置内存"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/language"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def addServiceNodeLabel(self, region, tenant_name, service_alias, body):
        """添加应用对应的节点标签"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/node-label"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def deleteServiceNodeLabel(self, region, tenant_name, service_alias, body):
        """删除应用对应的节点标签"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/node-label"
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, body, region=region)
        return body

    def add_service_state_label(self, region, tenant_name, service_alias, body):
        """添加应用有无状态标签"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/service-label"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def update_service_state_label(self, region, tenant_name, service_alias, body):
        """修改应用有无状态标签"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/service-label"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def get_service_pods(self, region, tenant_name, service_alias, body):
        """获取应用pod信息"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/pods"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, body, region=region)
        return body

    def add_service_port(self, region, tenant_name, service_alias, body):
        """添加服务端口"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def update_service_port(self, region, tenant_name, service_alias, body):
        """添加服务端口"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def delete_service_port(self, region, tenant_name, service_alias, port):
        """删除服务端口"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports/" + str(port)
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def manage_inner_port(self, region, tenant_name, service_alias, port, body):
        """打开关闭对内端口"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports/" + str(port) + "/inner"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def manage_outer_port(self, region, tenant_name, service_alias, port, body):
        """打开关闭对外端口"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports/" + str(port) + "/outer"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return body

    def update_service_probe(self, region, tenant_name, service_alias, body):
        """更新应用探针信息"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/probe"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body, region=region)
        return res, body

    def add_service_probe(self, region, tenant_name, service_alias, body):
        """添加应用探针信息"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/probe"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return res, body

    def delete_service_probe(self, region, tenant_name, service_alias, body):
        """删除应用探针信息"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/probe"
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, body, region=region)
        return body

    def restart_service(self, region, tenant_name, service_alias, body):
        """重启应用"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/restart"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def rollback(self, region, tenant_name, service_alias, body):
        """应用版本回滚"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/rollback"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def start_service(self, region, tenant_name, service_alias, body):
        """启动应用"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/start"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def stop_service(self, region, tenant_name, service_alias, body):
        """关闭应用"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/stop"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def upgrade_service(self, region, tenant_name, service_alias, body):
        """升级应用"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/upgrade"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def check_service_status(self, region, tenant_name, service_alias):
        """获取单个应用状态"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/status"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_service_volumes(self, region, tenant_name, service_alias):
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers)
        return res, body

    def add_service_volumes(self, region, tenant_name, service_alias, body):
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes".format(tenant_name, service_alias)
        self._set_headers(token)
        return self._post(url, self.default_headers, body)

    def delete_service_volumes(self, region, tenant_name, service_alias, volume_name):
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes/{2}".format(tenant_name, service_alias, volume_name)
        self._set_headers(token)
        return self._delete(url, self.default_headers)

    def get_service_dep_volumes(self, region, tenant_name, service_alias):
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers)
        return res, body

    def add_service_dep_volumes(self, region, tenant_name, service_alias, body):
        """ Add dependent volumes """
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body)
        return res, body

    def delete_service_dep_volumes(self, region, tenant_name, service_alias, body):
        """ Delete dependent volume"""
        token, uri_prefix = self._get_region_request_info(region)
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(tenant_name, service_alias)
        self._set_headers(token)
        return self._delete(url, self.default_headers, body)

    def add_service_volume(self, region, tenant_name, service_alias, body):
        """添加应用持久化目录"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/volume"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return res, body

    def delete_service_volume(self, region, tenant_name, service_alias, body):
        """删除应用持久化目录"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/volume"
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, body, region=region)
        return res, body

    def add_service_volume_dependency(self, region, tenant_name, service_alias, body):
        """添加服务持久化挂载依赖"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/volume-dependency"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def delete_service_volume_dependency(self, region, tenant_name, service_alias, body):
        """删除服务持久化挂载依赖"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/volume-dependency"
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, body, region=region)
        return body

    def service_status(self, region, tenant_name, body):
        """获取多个应用的状态"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services_status"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def get_docker_log_instance(self, region, tenant_name, service_alias):
        """获取日志实体"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/log-instance"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_service_logs(self, region, tenant_name, service_alias, body):
        """获取应用日志"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/log"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return body

    def get_service_log_files(self, region, tenant_name, service_alias):
        """获取应用日志文件列表"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/log-file"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_event_log(self, region, tenant_name, service_alias, body):
        """获取事件日志"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/event-log"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return res, body

    def get_api_version(self, url, token, region):
        """获取api版本"""
        url += "/v2/show"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_opentsdb_data(self, region, body):
        """获取opentsdb数据"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/opentsdb/query"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        try:
            bean = body["bean"]
            body_list = bean["body"]
            if not isinstance(body_list, list):
                body_list = json.loads(body_list)
            dps = body_list[0]['dps']
            return dps
        except IndexError:
            logger.info('tsdb_query', "request: {0}".format(url))
            logger.info('tsdb_query', "response: {0} ====== {1}".format(
                res, body))
            return None

    def get_region_tenants_resources(self, region, body):
        """获取租户在数据中心下的资源使用情况"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region][
                  'url'] + "/v2/resources/tenants"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def share_clound_service(self, region, tenant_name, body):
        """分享应用到云市"""
        region_map = self.get_region_map(region)
        token = region_map[region]['token']
        url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/cloud-share"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=body)
        return res, body

    # old api
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
