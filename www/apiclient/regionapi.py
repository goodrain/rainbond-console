# -*- coding: utf8 -*-
import json
import logging

import httplib2
from django import http
from django.conf import settings

from backends.models import RegionConfig
from www.apiclient.baseclient import HttpClient, client_auth_service
from www.models.main import TenantRegionInfo, Tenants
import os

logger = logging.getLogger('default')


class RegionInvokeApi(HttpClient):
    def __init__(self, *args, **kwargs):
        HttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {
            'Connection': 'keep-alive',
            'Content-Type': 'application/json'
        }


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


    def _set_headers(self, token):
        if settings.MODULES["RegionToken"]:
            if not token:
                if os.environ.get('REGION_TOKEN'):
                    self.default_headers.update({
                        "Authorization":
                        os.environ.get('REGION_TOKEN')
                    })
                else:
                    self.default_headers.update({
                        "Authorization": ""
                    })
            else:
                self.default_headers.update({"Authorization": token})
        # logger.debug('Default headers: {0}'.format(self.default_headers))

    def __get_tenant_region_info(self, tenant_name, region):

        tenants = Tenants.objects.filter(tenant_name=tenant_name)
        if tenants:
            tenant = tenants[0]
            tenant_regions = TenantRegionInfo.objects.filter(
                tenant_id=tenant.tenant_id, region_name=region)
            if not tenant_regions:
                logger.error("tenant {0} is not init in region {1}".format(
                    tenant_name, region))
                raise http.Http404
        else:
            logger.error("tenant {0} is not found!".format(tenant_name))
            raise http.Http404
        return tenant_regions[0]


    def get_tenant_resources(self, region, tenant_name, enterprise_id):
        """获取指定租户的资源使用情况"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name,region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/resources?enterprise_id="+enterprise_id

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/resources?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_region_publickey(self, tenant_name, region, enterprise_id):
        url, token = self.__get_region_access_info(tenant_name, region)
        url += "/v2/builder/publickey"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def create_tenant(self, region, tenant_name, tenant_id, enterprise_id):
        """创建租户"""
        # region_map = self.get_region_map(region)
        # # TODO add enterprise id
        # data = {"tenant_id": tenant_id, "tenant_name": tenant_name}
        # token = region_map[region]['token']
        # url = region_map[region]['url'] + "/v2/tenants"

        url, token = self.__get_region_access_info(tenant_name, region)
        # # TODO add enterprise id
        cloud_enterprise_id = client_auth_service.get_region_access_enterprise_id_by_tenant(
            tenant_name, region)
        if cloud_enterprise_id:
            enterprise_id = cloud_enterprise_id
        data = {"tenant_id": tenant_id, "tenant_name": tenant_name, "eid": enterprise_id}
        url += "/v2/tenants"

        self._set_headers(token)
        logger.debug("create tenant url :{0}".format(url))
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def create_service(self, region, tenant_name, body):
        """创建应用"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # # 更新tenant_id 为数据中心tenant_id
        # body["tenant_id"] = tenant_region.region_tenant_id
        #
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services"

        self._set_headers(token)
        logger.debug(
            'Create service headers :{0}'.format(self.default_headers))
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_service_info(self, region, tenant_name, service_alias):
        """获取应用信息"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def update_service(self, region, tenant_name, service_alias, body):
        """更新应用"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def delete_service(self, region, tenant_name, service_alias,
                       enterprise_id):
        """删除应用"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias+"?enterprise_id="+enterprise_id

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def build_service(self, region, tenant_name, service_alias, body):
        """应用构建"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/build"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/build"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def code_check(self, region, tenant_name, body):
        """发送代码检测消息"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # # 更新tenant_id 为数据中心tenant_id
        # body["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/code-check"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/code-check"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_service_language(self, region, service_id, tenant_name):
        """获取服务语言"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # url = region_map[region]['url'] + "/v2/builder/codecheck/service/{0}".format(service_id)

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/builder/codecheck/service/{0}".format(service_id)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def add_service_dependency(self, region, tenant_name, service_alias, body):
        """增加服务依赖"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # # 更新tenant_id 为数据中心tenant_id
        # body["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/dependency"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/dependency"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def delete_service_dependency(self, region, tenant_name, service_alias,
                                  body):
        """取消服务依赖"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # # 更新tenant_id 为数据中心tenant_id
        # body["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/dependency"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/dependency"

        self._set_headers(token)
        res, body = self._delete(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def add_service_env(self, region, tenant_name, service_alias, body):
        """添加环境变量"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # # 更新tenant_id 为数据中心tenant_id
        # body["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/env"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/env"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def delete_service_env(self, region, tenant_name, service_alias, body):
        """删除环境变量"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/env"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/env"

        self._set_headers(token)
        res, body = self._delete(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def update_service_env(self, region, tenant_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/env"

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    def horizontal_upgrade(self, region, tenant_name, service_alias, body):
        """服务水平伸缩"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/horizontal"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/horizontal"

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def vertical_upgrade(self, region, tenant_name, service_alias, body):
        """服务垂直伸缩"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/vertical"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/vertical"

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def change_memory(self, region, tenant_name, service_alias, body):
        """根据应用语言设置内存"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/language"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/language"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def addServiceNodeLabel(self, region, tenant_name, service_alias, body):
        """添加应用对应的节点标签"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/node-label"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/node-label"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def deleteServiceNodeLabel(self, region, tenant_name, service_alias, body):
        """删除应用对应的节点标签"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/node-label"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/node-label"

        self._set_headers(token)
        res, body = self._delete(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def add_service_state_label(self, region, tenant_name, service_alias,
                                body):
        """添加应用有无状态标签"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/service-label"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/service-label"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def update_service_state_label(self, region, tenant_name, service_alias,
                                   body):
        """修改应用有无状态标签"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/service-label"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/service-label"

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def get_service_pods(self, region, tenant_name, service_alias,
                         enterprise_id):
        """获取应用pod信息"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/pods?enterprise_id="+enterprise_id

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/pods?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, None, region=region)
        return body

    def add_service_port(self, region, tenant_name, service_alias, body):
        """添加服务端口"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # port_list = body["port"]
        # for port in port_list:
        #     port["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        port_list = body["port"]
        for port in port_list:
            port["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def update_service_port(self, region, tenant_name, service_alias, body):
        """更新服务端口"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # port_list = body["port"]
        # for port in port_list:
        #     port["tenant_id"] = tenant_region.region_tenant_id
        #
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        port_list = body["port"]
        for port in port_list:
            port["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports"

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def delete_service_port(self, region, tenant_name, service_alias, port,
                            enterprise_id):
        """删除服务端口"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports/" + str(port) +"?enterprise_id="+enterprise_id

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports/" + str(
            port) + "?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def manage_inner_port(self, region, tenant_name, service_alias, port,
                          body):
        """打开关闭对内端口"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports/" + str(port) + "/inner"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports/" + str(
            port) + "/inner"

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def manage_outer_port(self, region, tenant_name, service_alias, port,
                          body):
        """打开关闭对外端口"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/ports/" + str(port) + "/outer"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports/" + str(
            port) + "/outer"

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def update_service_probe(self, region, tenant_name, service_alias, body):
        """更新应用探针信息"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # body["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/probe"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/probe"

        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def add_service_probe(self, region, tenant_name, service_alias, body):
        """添加应用探针信息"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # body["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/probe"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/probe"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def delete_service_probe(self, region, tenant_name, service_alias, body):
        """删除应用探针信息"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/probe"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/probe"

        self._set_headers(token)
        res, body = self._delete(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def restart_service(self, region, tenant_name, service_alias, body):
        """重启应用"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/restart"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/restart"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def rollback(self, region, tenant_name, service_alias, body):
        """应用版本回滚"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/rollback"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/rollback"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def start_service(self, region, tenant_name, service_alias, body):
        """启动应用"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/start"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/start"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def stop_service(self, region, tenant_name, service_alias, body):
        """关闭应用"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/stop"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/stop"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def upgrade_service(self, region, tenant_name, service_alias, body):
        """升级应用"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/upgrade"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/upgrade"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def check_service_status(self, region, tenant_name, service_alias,
                             enterprise_id):
        """获取单个应用状态"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/status?enterprise_id="+ enterprise_id

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/status?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_service_volumes(self, region, tenant_name, service_alias,
                            enterprise_id):
        # token, uri_prefix = self._get_region_request_info(region)
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes?enterprise_id={2}".format(
            tenant_name, service_alias, enterprise_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers)
        return res, body

    def add_service_volumes(self, region, tenant_name, service_alias, body):
        # token, uri_prefix = self._get_region_request_info(region)
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes".format(
            tenant_name, service_alias)
        self._set_headers(token)
        return self._post(url, self.default_headers, json.dumps(body))

    def delete_service_volumes(self, region, tenant_name, service_alias,
                               volume_name, enterprise_id):
        # token, uri_prefix = self._get_region_request_info(region)
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes/{2}?enterprise_id={3}".format(
            tenant_name, service_alias, volume_name, enterprise_id)
        self._set_headers(token)
        return self._delete(url, self.default_headers)

    def get_service_dep_volumes(self, region, tenant_name, service_alias,
                                enterprise_id):
        # token, uri_prefix = self._get_region_request_info(region)
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes?enterprise_id={2}".format(
            tenant_name, service_alias, enterprise_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers)
        return res, body

    def add_service_dep_volumes(self, region, tenant_name, service_alias,
                                body):
        """ Add dependent volumes """
        # token, uri_prefix = self._get_region_request_info(region)
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(
            tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body))
        return res, body

    def delete_service_dep_volumes(self, region, tenant_name, service_alias,
                                   body):
        """ Delete dependent volume"""
        # token, uri_prefix = self._get_region_request_info(region)
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(
            tenant_name, service_alias)
        self._set_headers(token)
        return self._delete(url, self.default_headers, json.dumps(body))

    def add_service_volume(self, region, tenant_name, service_alias, body):
        """添加应用持久化目录"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/volume"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/volume"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def delete_service_volume(self, region, tenant_name, service_alias, body):
        """删除应用持久化目录"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/volume"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/volume"

        self._set_headers(token)
        res, body = self._delete(
            url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def add_service_volume_dependency(self, region, tenant_name, service_alias,
                                      body):
        """添加服务持久化挂载依赖"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # body["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/volume-dependency"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/volume-dependency"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def delete_service_volume_dependency(self, region, tenant_name,
                                         service_alias, body):
        """删除服务持久化挂载依赖"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # body["tenant_id"] = tenant_region.tenant_id
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/volume-dependency"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/volume-dependency"

        self._set_headers(token)
        res, body = self._delete(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def service_status(self, region, tenant_name, body):
        """获取多个应用的状态"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services_status"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services_status"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_docker_log_instance(self, region, tenant_name, service_alias,
                                enterprise_id):
        """获取日志实体"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/log-instance?enterprise_id="+enterprise_id

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/log-instance?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_service_logs(self, region, tenant_name, service_alias, body):
        """获取应用日志"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/log"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/log"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_service_log_files(self, region, tenant_name, service_alias,
                              enterprise_id):
        """获取应用日志文件列表"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/log-file?enterprise_id="+enterprise_id

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/log-file?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_event_log(self, region, tenant_name, service_alias, body):
        """获取事件日志"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/event-log"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/event-log"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    def get_api_version(self, url, token, region):
        """获取api版本"""
        url += "/v2/show"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_opentsdb_data(self, region, tenant_name, body):
        """获取opentsdb数据"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # url = region_map[region][
        #           'url'] + "/v2/opentsdb/query"

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/opentsdb/query"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
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

    def get_region_tenants_resources(self, region, data, enterprise_id=""):
        """获取租户在数据中心下的资源使用情况"""
        url, token = self.__get_region_access_info_by_enterprise_id(enterprise_id, region)
        # url, token = self.__get_region_access_info(tenant_name, region)
        url += "/v2/resources/tenants"
        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(data), region=region)
        return body

    def get_service_resources(self, tenant_name, region, data):
        """获取一批应用的资源使用情况"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url += "/v2/resources/services"
        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(data), region=region)
        return body

    # v3.5版本后弃用
    def share_clound_service(self, region, tenant_name, body):
        """分享应用到云市"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/cloud-share"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/cloud-share"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    # v3.5版本新加可用
    def share_service(self, region, tenant_name, service_alias, body):
        """分享应用"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = "{0}/v2/tenants/{1}/services/{2}/share".format(
            url, tenant_region.region_tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    def share_service_result(self, region, tenant_name, service_alias,
                             region_share_id):
        """查询分享应用状态"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = "{0}/v2/tenants/{1}/services/{2}/share/{3}".format(
            url, tenant_region.region_tenant_name, service_alias,
            region_share_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def bindDomain(self, region, tenant_name, service_alias, body):
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # body["tenant_id"] = tenant_region.region_tenant_id
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/domains"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/domains"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def unbindDomain(self, region, tenant_name, service_alias, body):
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region][
        #           'url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/domains/" + body[
        #           "domain"]

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/domains/" + \
              body["domain"]

        self._set_headers(token)
        res, body = self._delete(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def pluginServiceRelation(self, region, tenant_name, service_alias, body):
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/plugin"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin"

        self._set_headers(token)
        return self._post(
            url, self.default_headers, json.dumps(body), region=region)

    def delPluginServiceRelation(self, region, tenant_name, plugin_id,
                                 service_alias):
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id

        self._set_headers(token)
        return self._delete(url, self.default_headers, None, region=region)

    def updatePluginServiceRelation(self, region, tenant_name, service_alias,
                                    body):
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/plugin"
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin"

        self._set_headers(token)
        return self._put(
            url, self.default_headers, json.dumps(body), region=region)

    def postPluginAttr(self, region, tenant_name, service_alias, plugin_id,
                       body):
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id + "/setenv"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id + "/setenv"

        self._set_headers(token)
        return self._post(
            url, self.default_headers, json.dumps(body), region=region)

    def putPluginAttr(self, region, tenant_name, service_alias, plugin_id,
                      body):
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id + "/upenv"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id + "/upenv"

        self._set_headers(token)
        return self._put(
            url, self.default_headers, json.dumps(body), region=region)

    def create_plugin(self, region, tenant_name, body):
        """创建数据中心端插件"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/plugin"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/plugin"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def build_plugin(self, region, tenant_name, plugin_id, body):
        """创建数据中心端插件"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/{0}/plugin/{1}/build".format(tenant_name, plugin_id)
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/{0}/plugin/{1}/build".format(
            tenant_region.region_tenant_name, plugin_id)

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(body), region=region)
        return body

    def get_build_status(self, region, tenant_name, plugin_id, build_version):
        """获取插件构建状态"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/{0}/plugin/{1}/build-version/{2}".format(tenant_name, plugin_id,
        #                                                                                         build_version)
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/{0}/plugin/{1}/build-version/{2}".format(
            tenant_region.region_tenant_name, plugin_id, build_version)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_plugin_event_log(self, region, tenant_name, data):
        """获取插件日志信息"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/{0}/event-log".format(tenant_name)

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/{0}/event-log".format(
            tenant_region.region_tenant_name)
        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, json.dumps(data), region=region)
        return body

    def delete_plugin_version(self, region, tenant_name, plugin_id,
                              build_version):
        """删除插件某个版本信息"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/{0}/plugin/{1}/build-version/{2}".format(tenant_name, plugin_id,
        #                                                                                         build_version)
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/{0}/plugin/{1}/build-version/{2}".format(
            tenant_region.region_tenant_name, plugin_id, build_version)

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers)
        return body

    def get_query_data(self, region, tenant_name, params):
        """获取监控数据"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # url = region_map[region]['url'] + "/api/v1/query" + params

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/api/v1/query" + params
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_query_range_data(self, region, tenant_name, params):
        """获取监控范围数据"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # url = region_map[region]['url'] + "/api/v1/query_range" + params
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/api/v1/query_range" + params
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_service_publish_status(self, region, tenant_name, service_key,
                                   app_version):
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # url = region_map[region]['url'] + "/v2/builder/publish/service/{0}/version/{1}".format(service_key,app_version)

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/builder/publish/service/{0}/version/{1}".format(
            service_key, app_version)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_tenant_events(self, region, tenant_name, event_ids):
        """获取多个事件的状态"""
        # region_map = self.get_region_map(region)
        # token = region_map[region]['token']
        # tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # tenant_name = tenant_region.region_tenant_name
        # url = region_map[region]['url'] + "/v2/tenants/" + tenant_name + "/event"

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/event"

        self._set_headers(token)
        res, body = self._get(
            url,
            self.default_headers,
            region=region,
            body=json.dumps({
                "event_ids": event_ids
            }))
        return body

    def get_events_by_event_ids(self, region_name, event_ids):
        """获取多个event的事件"""
        region_info = self.get_region_info(region_name)
        url = region_info.url + "/v2/event"
        self._set_headers(region_info.token)
        res, body = self._get(url, self.default_headers, region=region_name, body=json.dumps({"event_ids": event_ids}))
        return body

    def __get_region_access_info(self, tenant_name, region):
        """获取一个团队在指定数据中心的身份认证信息"""
        # 根据团队名获取其归属的企业在指定数据中心的访问信息
        url, token = client_auth_service.get_region_access_token_by_tenant(
            tenant_name, region)
        # 如果团队所在企业所属数据中心信息不存在则使用通用的配置(兼容未申请数据中心token的企业)
        # 管理后台数据需要及时生效，对于数据中心的信息查询使用直接查询原始数据库
        region_info = self.get_region_info(region_name=region)
        url = region_info.url
        if not token:
            # region_map = self.get_region_map(region)
            token = region_info.token
        else:
            token = "Token {}".format(token)
        return url, token

    def __get_region_access_info_by_enterprise_id(self, enterprise_id, region):
        url, token = client_auth_service.get_region_access_token_by_enterprise_id(enterprise_id, region)
        # 管理后台数据需要及时生效，对于数据中心的信息查询使用直接查询原始数据库
        region_info = self.get_region_info(region_name=region)
        url = region_info.url
        if not token:
            token = region_info.token
        else:
            token = "Token {}".format(token)
        return url, token


    def get_protocols(self, region, tenant_name):
        """
        @ 获取当前数据中心支持的协议
        """
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/protocols"
        logger.debug("multi protocol url is {}".format(url))
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_region_info(self, region_name):
        configs = RegionConfig.objects.filter(region_name=region_name)
        if configs:
            return configs[0]
        return None

    def service_source_check(self, region, tenant_name, body):
        """应用源检测"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/servicecheck"

        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    def get_service_check_info(self, region, tenant_name, uuid):
        """应用源检测信息获取"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/servicecheck/" + str(
            uuid)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def service_chargesverify(self, region, tenant_name, data):
        """应用扩大资源申请接口"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/chargesverify?quantity={0}&reason={1}&eid={2}".format(
            data["quantity"], data["reason"], data["eid"])
        self._set_headers(token)
        res, body = self._get(
            url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def update_plugin_info(self, region, tenant_name, plugin_id, data):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url += "/v2/tenants/{0}/plugin/{1}".format(tenant_region.region_tenant_name, plugin_id)
        self._set_headers(token)
        res, body = self._put(
            url, self.default_headers, json.dumps(data), region=region)
        return body

    def delete_plugin(self, region, tenant_name, plugin_id):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url += "/v2/tenants/{0}/plugin/{1}".format(tenant_region.region_tenant_name, plugin_id)
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return res, body

    def install_service_plugin(self, region, tenant_name, service_alias, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin"

        self._set_headers(token)
        return self._post(
            url, self.default_headers, json.dumps(body), region=region)

    def uninstall_service_plugin(self, region, tenant_name, plugin_id,
                                 service_alias):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id
        self._set_headers(token)
        return self._delete(url, self.default_headers, None, region=region)

    def update_plugin_service_relation(self, region, tenant_name, service_alias,
                                       body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin"

        self._set_headers(token)
        return self._put(
            url, self.default_headers, json.dumps(body), region=region)

    def update_service_plugin_config(self, region, tenant_name, service_alias, plugin_id,
                                     body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id + "/upenv"

        self._set_headers(token)
        return self._put(
            url, self.default_headers, json.dumps(body), region=region)

    def get_services_pods(self, region, tenant_name, service_id_list,
                         enterprise_id):
        """获取多个应用的pod信息"""
        service_ids = ",".join(service_id_list)
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/pods?enterprise_id=" + enterprise_id + "&service_ids=" + service_ids

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, None, region=region)
        return body

    def export_app(self, region, tenant_name, data):
        """导出应用"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url += "/v2/app/export"
        self._set_headers(token)
        res, body = self._post(
            url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def get_app_export_status(self, region, tenant_name, event_id):
        """查询应用导出状态"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/export/" + event_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body
