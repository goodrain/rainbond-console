# -*- coding: utf8 -*-
import json
import logging
import os

import httplib2
from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig
from django import http
from django.conf import settings
from www.apiclient.baseclient import client_auth_service
from www.apiclient.exception import err_region_not_found
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient
from www.models.main import TenantRegionInfo, Tenants
from console.exception.bcode import ErrNamespaceExists

logger = logging.getLogger('default')


class RegionInvokeApi(RegionApiBaseHttpClient):
    def __init__(self, *args, **kwargs):
        RegionApiBaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json'}

    def make_proxy_http(self, region_service_info):
        proxy_info = region_service_info['proxy']
        if proxy_info['type'] == 'http':
            proxy_type = httplib2.socks.PROXY_TYPE_HTTP_NO_TUNNEL
        else:
            raise TypeError("unsupport type: %s" % proxy_info['type'])

        proxy = httplib2.ProxyInfo(proxy_type, proxy_info['host'], proxy_info['port'])
        client = httplib2.Http(proxy_info=proxy, timeout=25)
        return client

    def _set_headers(self, token):
        if settings.MODULES["RegionToken"]:
            if not token:
                if os.environ.get('REGION_TOKEN'):
                    self.default_headers.update({"Authorization": os.environ.get('REGION_TOKEN')})
                else:
                    self.default_headers.update({"Authorization": ""})
            else:
                self.default_headers.update({"Authorization": token})
        # logger.debug('Default headers: {0}'.format(self.default_headers))

    def __get_tenant_region_info(self, tenant_name, region):
        if type(tenant_name) == Tenants:
            tenant_name = tenant_name.tenant_name
        tenants = Tenants.objects.filter(tenant_name=tenant_name)
        if tenants:
            tenant = tenants[0]
            tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, region_name=region)
            if not tenant_regions:
                logger.error("tenant {0} is not init in region {1}".format(tenant_name, region))
                raise http.Http404
        else:
            logger.error("team {0} is not found!".format(tenant_name))
            raise http.Http404
        return tenant_regions[0]

    def get_tenant_resources(self, region, tenant_name, enterprise_id):
        """获取指定租户的资源使用情况"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/resources?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=10)
        return body

    def get_region_publickey(self, tenant_name, region, enterprise_id, tenant_id):
        url, token = self.__get_region_access_info(tenant_name, region)
        url += "/v2/builder/publickey/" + tenant_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def create_tenant(self, region, tenant_name, tenant_id, enterprise_id, namespace):
        """创建租户"""
        url, token = self.__get_region_access_info(tenant_name, region)
        cloud_enterprise_id = client_auth_service.get_region_access_enterprise_id_by_tenant(tenant_name, region)
        if cloud_enterprise_id:
            enterprise_id = cloud_enterprise_id
        data = {"tenant_id": tenant_id, "tenant_name": tenant_name, "eid": enterprise_id, "namespace": namespace}
        url += "/v2/tenants"

        self._set_headers(token)
        logger.debug("create tenant url :{0}".format(url))
        try:
            res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
            return res, body
        except RegionApiBaseHttpClient.CallApiError as e:
            if "namespace exists" in e.message['body'].get('msg', ""):
                raise ErrNamespaceExists
            return {'status': e.message['httpcode']}, e.message['body']

    def delete_tenant(self, region, tenant_name):
        """删除组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def create_service(self, region, tenant_name, body):
        """创建组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_service_info(self, region, tenant_name, service_alias):
        """获取组件信息"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def update_service(self, region, tenant_name, service_alias, body):
        """更新组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def delete_service(self, region, tenant_name, service_alias, enterprise_id, data=None):
        """删除组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "?enterprise_id=" + enterprise_id

        self._set_headers(token)
        if not data:
            data = {}
        res, body = self._delete(url, self.default_headers, region=region, body=json.dumps(data))
        return body

    def build_service(self, region, tenant_name, service_alias, body):
        """组件构建"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/build"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def code_check(self, region, tenant_name, body):
        """发送代码检测消息"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/code-check"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_service_language(self, region, service_id, tenant_name):
        """获取组件语言"""

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/builder/codecheck/service/{0}".format(service_id)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def add_service_dependency(self, region, tenant_name, service_alias, body):
        """增加组件依赖"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/dependency"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def add_service_dependencys(self, region, tenant_name, service_alias, body):
        """增加组件依赖"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/dependencys"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def delete_service_dependency(self, region, tenant_name, service_alias, body):
        """取消组件依赖"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/dependency"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def add_service_env(self, region, tenant_name, service_alias, body):
        """添加环境变量"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/env"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def delete_service_env(self, region, tenant_name, service_alias, body):
        """删除环境变量"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        # 更新tenant_id 为数据中心tenant_id
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/env"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def update_service_env(self, region, tenant_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/env"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    def horizontal_upgrade(self, region, tenant_name, service_alias, body):
        """组件水平伸缩"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/horizontal"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def vertical_upgrade(self, region, tenant_name, service_alias, body):
        """组件垂直伸缩"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/vertical"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def change_memory(self, region, tenant_name, service_alias, body):
        """根据组件语言设置内存"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/language"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_region_labels(self, region, tenant_name):
        """获取数据中心可用的标签"""

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/resources/labels"

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def addServiceNodeLabel(self, region, tenant_name, service_alias, body):
        """添加组件对应的节点标签"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/label"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def deleteServiceNodeLabel(self, region, tenant_name, service_alias, body):
        """删除组件对应的节点标签"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/label"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, json.dumps(body), region=region)
        return body

    def add_service_state_label(self, region, tenant_name, service_alias, body):
        """添加组件有无状态标签"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/label"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body, region=region)
        return body

    def update_service_state_label(self, region, tenant_name, service_alias, body):
        """修改组件有无状态标签"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/label"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def get_service_pods(self, region, tenant_name, service_alias, enterprise_id):
        """获取组件pod信息"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/pods?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, None, region=region, timeout=15)
        return body

    def get_dynamic_services_pods(self, region, tenant_name, services_ids):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/pods?service_ids={}".format(",".join(services_ids))
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=15)
        return body

    def pod_detail(self, region, tenant_name, service_alias, pod_name):
        """获取组件pod信息"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/pods/" + pod_name + "/detail"

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, None, region=region)
        return body

    def add_service_port(self, region, tenant_name, service_alias, body):
        """添加组件端口"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        port_list = body["port"]
        for port in port_list:
            port["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def update_service_port(self, region, tenant_name, service_alias, body):
        """更新组件端口"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        port_list = body["port"]
        for port in port_list:
            port["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        return body

    def delete_service_port(self, region, tenant_name, service_alias, port, enterprise_id, body={}):
        """删除组件端口"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports/" + str(
            port) + "?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, json.dumps(body), region=region)
        return body

    def manage_inner_port(self, region, tenant_name, service_alias, port, body):
        """打开关闭对内端口"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports/" + str(
            port) + "/inner"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        return body

    def manage_outer_port(self, region, tenant_name, service_alias, port, body):
        """打开关闭对外端口"""
        try:
            url, token = self.__get_region_access_info(tenant_name, region)
            tenant_region = self.__get_tenant_region_info(tenant_name, region)
            url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/ports/" + str(
                port) + "/outer"

            self._set_headers(token)
            res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
            return body
        except RegionApiBaseHttpClient.CallApiError as e:
            message = e.body.get("msg")
            if message and message.find("do not allow operate outer port for thirdpart domain endpoints") >= 0:
                raise ServiceHandleException(
                    status_code=400,
                    msg="do not allow operate outer port for thirdpart domain endpoints",
                    msg_show="该第三方组件具有域名类实例，暂不支持开放网关访问")
            else:
                raise e

    def update_service_probec(self, region, tenant_name, service_alias, body):
        """更新组件探针信息"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/probe"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def add_service_probe(self, region, tenant_name, service_alias, body):
        """添加组件探针信息"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/probe"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def delete_service_probe(self, region, tenant_name, service_alias, body):
        """删除组件探针信息"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/probe"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, json.dumps(body), region=region)
        return body

    def restart_service(self, region, tenant_name, service_alias, body):
        """重启组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/restart"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def rollback(self, region, tenant_name, service_alias, body):
        """组件版本回滚"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/rollback"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def start_service(self, region, tenant_name, service_alias, body):
        """启动组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/start"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def pause_service(self, region, tenant_name, service_alias, body):
        """挂起组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/pause"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def un_pause_service(self, region, tenant_name, service_alias, body):
        """恢复组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/un_pause"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def stop_service(self, region, tenant_name, service_alias, body):
        """关闭组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/stop"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def upgrade_service(self, region, tenant_name, service_alias, body):
        """升级组件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/upgrade"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def check_service_status(self, region, tenant_name, service_alias, enterprise_id):
        """获取单个组件状态"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/status?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_user_service_abnormal_status(self, region, enterprise_id):
        """获取用户所有组件异常状态"""
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/enterprise/" + enterprise_id + "/abnormal_status"
        res, body = self._get(url, self.default_headers, region=region, timeout=2)
        if res.get("status") == 200 and isinstance(body, dict):
            return body
        return None

    def get_volume_options(self, region, tenant_name):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/volume-options"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_chart_information(self, region, tenant_name, data):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/helm/get_chart_information"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def check_helm_app(self, region, tenant_name, data):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/helm/check_helm_app"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, body=json.dumps(data), timeout=20)
        return res, body

    def get_yaml_by_chart(self, region, tenant_name, data):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/helm/get_chart_yaml"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, body=json.dumps(data), timeout=20)
        return res, body

    def get_upload_chart_information(self, region, tenant_name, event_id):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/helm/get_upload_chart_information?event_id={}".format(event_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def check_upload_chart(self, region, tenant_name, data):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/helm/check_upload_chart"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def get_upload_chart_resource(self, region, tenant_name, data):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/helm/get_upload_chart_resource"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def import_upload_chart_resource(self, region, tenant_name, data):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/helm/import_upload_chart_resource"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def get_upload_chart_value(self, region, tenant_name, event_id):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        url = uri_prefix + "/v2/helm/get_upload_chart_value?event_id={}".format(event_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_service_volumes_status(self, region, tenant_name, service_alias):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes-status".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_service_volumes(self, region, tenant_name, service_alias, enterprise_id):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes?enterprise_id={2}".format(
            tenant_name, service_alias, enterprise_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def add_service_volumes(self, region, tenant_name, service_alias, body):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes".format(tenant_name, service_alias)
        self._set_headers(token)
        return self._post(url, self.default_headers, json.dumps(body), region=region)

    def delete_service_volumes(self, region, tenant_name, service_alias, volume_name, enterprise_id, body={}):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes/{2}?enterprise_id={3}".format(
            tenant_name, service_alias, volume_name, enterprise_id)
        self._set_headers(token)
        return self._delete(url, self.default_headers, json.dumps(body), region=region)

    def upgrade_service_volumes(self, region, tenant_name, service_alias, body):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/volumes".format(tenant_name, service_alias)
        self._set_headers(token)
        return self._put(url, self.default_headers, json.dumps(body), region=region)

    def get_service_dep_volumes(self, region, tenant_name, service_alias, enterprise_id):
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes?enterprise_id={2}".format(
            tenant_name, service_alias, enterprise_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def add_service_dep_volumes(self, region, tenant_name, service_alias, body):
        """ Add dependent volumes """
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def delete_service_dep_volumes(self, region, tenant_name, service_alias, body):
        """ Delete dependent volume"""
        uri_prefix, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        tenant_name = tenant_region.region_tenant_name
        url = uri_prefix + "/v2/tenants/{0}/services/{1}/depvolumes".format(tenant_name, service_alias)
        self._set_headers(token)
        return self._delete(url, self.default_headers, json.dumps(body), region=region)

    def add_service_volume(self, region, tenant_name, service_alias, body):
        """添加组件持久化目录"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/volume"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def delete_service_volume(self, region, tenant_name, service_alias, body):
        """删除组件持久化目录"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/volume"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def add_service_volume_dependency(self, region, tenant_name, service_alias, body):
        """添加组件持久化挂载依赖"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/volume-dependency"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def delete_service_volume_dependency(self, region, tenant_name, service_alias, body):
        """删除组件持久化挂载依赖"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/volume-dependency"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, json.dumps(body), region=region)
        return body

    def service_status(self, region, tenant_name, body):
        """获取多个组件的状态"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services_status"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body), timeout=20)
        return body

    def watch_operator_managed(self, region_name, tenant_name, region_app_id):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/apps/{}/watch_operator_managed".format(tenant_region.region_tenant_name, region_app_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return body

    def get_enterprise_running_services(self, enterprise_id, region, test=False):
        if test:
            self.get_enterprise_api_version_v2(enterprise_id, region=region)
        url, token = self.__get_region_access_info_by_enterprise_id(enterprise_id, region)
        url = url + "/v2/enterprise/" + enterprise_id + "/running-services"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=10)
        if res.get("status") == 200 and isinstance(body, dict):
            return body
        return None

    def get_docker_log_instance(self, region, tenant_name, service_alias, enterprise_id):
        """获取日志实体"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/log-instance?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_service_logs(self, region, tenant_name, service_alias, rows):
        """获取组件日志"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/{0}/services/{1}/logs?rows={2}".format(tenant_region.region_tenant_name, service_alias, rows)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_service_log_files(self, region, tenant_name, service_alias, enterprise_id):
        """获取组件日志文件列表"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/log-file?enterprise_id=" + enterprise_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_event_log(self, region, tenant_name, service_alias, body):
        """获取事件日志"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/event-log"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body), timeout=10)
        return res, body

    def get_target_events_list(self, region, tenant_name, target, target_id, page, page_size):
        """获取作用对象事件日志列表"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/events" + "?target={0}&target-id={1}&page={2}&size={3}".format(target, target_id, page, page_size)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=20)
        return res, body

    def get_myteams_events_list(self, region, enterprise_id, tenant, tenant_id_list, page, page_size):
        """获取所有团队日志列表"""
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/events/myteam" + "?tenant={0}&tenant_ids={1}&page={2}&size={3}".format(
            tenant, tenant_id_list, page, page_size)
        res, body = self._get(url, self.default_headers, region=region, timeout=3)
        return res, body

    def get_events_log(self, tenant_name, region, event_id):
        """获取作用对象事件日志内容"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/events/" + event_id + "/log"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_api_version(self, url, token, region):
        """获取api版本"""
        url += "/v2/show"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_api_version_v2(self, tenant_name, region_name):
        """获取api版本-v2"""
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url += "/v2/show"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return res, body

    def get_enterprise_api_version_v2(self, enterprise_id, region, **kwargs):
        """获取api版本-v2"""
        kwargs["retries"] = 1
        kwargs["timeout"] = 1
        url, token = self.__get_region_access_info_by_enterprise_id(enterprise_id, region)
        url += "/v2/show"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, **kwargs)
        return res, body

    def get_region_tenants_resources(self, region, data, enterprise_id=""):
        """获取租户在数据中心下的资源使用情况"""
        url, token = self.__get_region_access_info_by_enterprise_id(enterprise_id, region)
        url += "/v2/resources/tenants"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(data), region=region, timeout=15.0)
        return body

    def get_service_resources(self, tenant_name, region, data):
        """获取一批组件的资源使用情况"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url += "/v2/resources/services"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(data), region=region, timeout=10.0)
        return body

    # v3.5版本后弃用
    def share_clound_service(self, region, tenant_name, body):
        """分享应用到云市"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/cloud-share"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    # v3.5版本新加可用
    def share_service(self, region, tenant_name, service_alias, body):
        """分享应用"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = "{0}/v2/tenants/{1}/services/{2}/share".format(url, tenant_region.region_tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    def share_service_result(self, region, tenant_name, service_alias, region_share_id):
        """查询分享应用状态"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = "{0}/v2/tenants/{1}/services/{2}/share/{3}".format(url, tenant_region.region_tenant_name, service_alias,
                                                                 region_share_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def share_plugin(self, region_name, tenant_name, plugin_id, body):
        """分享插件"""
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = "{0}/v2/tenants/{1}/plugins/{2}/share".format(url, tenant_region.region_tenant_name, plugin_id)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region_name, body=json.dumps(body))
        return res, body

    def share_plugin_result(self, region_name, tenant_name, plugin_id, region_share_id):
        """查询分享插件状态"""
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = "{0}/v2/tenants/{1}/plugins/{2}/share/{3}".format(url, tenant_region.region_tenant_name, plugin_id,
                                                                region_share_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return res, body

    def bindDomain(self, region, tenant_name, service_alias, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/domains"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def unbindDomain(self, region, tenant_name, service_alias, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/domains/" + \
            body["domain"]
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, json.dumps(body), region=region)
        return body

    def list_gateway_http_route(self, region, tenant_name, namespace, region_app_id):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/batch-gateway-http-route?namespace={0}&app_id={1}".format(
            namespace, region_app_id)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_gateway_certificate(self, region, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/gateway-certificate"
        res, body = self._get(url, self.default_headers, json.dumps(body), region=region)
        return body

    def create_gateway_certificate(self, region, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/gateway-certificate"
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def update_gateway_certificate(self, region, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/gateway-certificate"
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        return body

    def delete_gateway_certificate(self, region, tenant_name, namespace, name):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/gateway-certificate?namespace={0}&name={1}".format(namespace, name)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def get_gateway_http_route(self, region, tenant_name, namespace, name):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/gateway-http-route?namespace={0}&name={1}".format(namespace, name)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def add_gateway_http_route(self, region, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/gateway-http-route"
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def update_gateway_http_route(self, region, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/gateway-http-route"
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        return body

    def delete_gateway_http_route(self, region, tenant_name, namespace, name, region_app_id):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/gateway-http-route?namespace={0}&name={1}&app_id={2}".format(
            namespace, name, region_app_id)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def bind_http_domain(self, region, tenant_name, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_name + "/http-rule"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def update_http_domain(self, region, tenant_name, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_name + "/http-rule"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        return body

    def delete_http_domain(self, region, tenant_name, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/http-rule"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, json.dumps(body), region=region)
        return body

    def bindTcpDomain(self, region, tenant_name, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_name + "/tcp-rule"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def updateTcpDomain(self, region, tenant_name, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_name + "/tcp-rule"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        return body

    def unbindTcpDomain(self, region, tenant_name, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_name + "/tcp-rule"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, json.dumps(body), region=region)
        return body

    def get_port(self, region, tenant_name, lock=False):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/gateway/ports?lock={}".format(lock)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_ips(self, region, tenant_name):
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/gateway/ips"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def pluginServiceRelation(self, region, tenant_name, service_alias, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin"

        self._set_headers(token)
        return self._post(url, self.default_headers, json.dumps(body), region=region)

    def delPluginServiceRelation(self, region, tenant_name, plugin_id, service_alias):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id

        self._set_headers(token)
        return self._delete(url, self.default_headers, None, region=region)

    def updatePluginServiceRelation(self, region, tenant_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin"

        self._set_headers(token)
        return self._put(url, self.default_headers, json.dumps(body), region=region)

    def postPluginAttr(self, region, tenant_name, service_alias, plugin_id, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin/" \
            + plugin_id + "/setenv"

        self._set_headers(token)
        return self._post(url, self.default_headers, json.dumps(body), region=region)

    def putPluginAttr(self, region, tenant_name, service_alias, plugin_id, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/plugin/" + plugin_id + "/upenv"

        self._set_headers(token)
        return self._put(url, self.default_headers, json.dumps(body), region=region)

    def create_plugin(self, region, tenant_name, body):
        """创建数据中心端插件"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/plugin"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return res, body

    def build_plugin(self, region, tenant_name, plugin_id, body):
        """创建数据中心端插件"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/{0}/plugin/{1}/build".format(tenant_region.region_tenant_name, plugin_id)

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def get_build_status(self, region, tenant_name, plugin_id, build_version):
        """获取插件构建状态"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/{0}/plugin/{1}/build-version/{2}".format(tenant_region.region_tenant_name, plugin_id,
                                                                          build_version)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_plugin_event_log(self, region, tenant_name, data):
        """获取插件日志信息"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/{0}/event-log".format(tenant_region.region_tenant_name)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(data), region=region)
        return body

    def delete_plugin_version(self, region, tenant_name, plugin_id, build_version):
        """删除插件某个版本信息"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/{0}/plugin/{1}/build-version/{2}".format(tenant_region.region_tenant_name, plugin_id,
                                                                          build_version)

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def get_query_data(self, region, tenant_name, params):
        """获取监控数据"""

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/api/v1/query" + params
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=10, retries=1)
        return res, body

    def get_query_service_access(self, region, tenant_name, params):
        """获取团队下组件访问量排序"""

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/api/v1/query" + params
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=10, retries=1)
        return res, body

    def get_query_domain_access(self, region, tenant_name, params):
        """获取团队下域名访问量排序"""

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/api/v1/query" + params
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=10, retries=1)
        return res, body

    def get_query_range_data(self, region, tenant_name, params):
        """获取监控范围数据"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/api/v1/query_range" + params
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=10, retries=1)
        return res, body

    def get_service_publish_status(self, region, tenant_name, service_key, app_version):

        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/builder/publish/service/{0}/version/{1}".format(service_key, app_version)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_tenant_events(self, region, tenant_name, event_ids):
        """获取多个事件的状态"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/event"

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, body=json.dumps({"event_ids": event_ids}), timeout=10)
        return body

    def get_events_by_event_ids(self, region_name, event_ids):
        """获取多个event的事件"""
        region_info = self.get_region_info(region_name)
        url = region_info.url + "/v2/event"
        self._set_headers(region_info.token)
        res, body = self._get(
            url, self.default_headers, region=region_name, body=json.dumps({"event_ids": event_ids}), timeout=10)
        return body

    def __get_region_access_info(self, tenant_name, region):
        """获取一个团队在指定数据中心的身份认证信息"""
        # 根据团队名获取其归属的企业在指定数据中心的访问信息
        token = None
        if tenant_name:
            if type(tenant_name) == Tenants:
                tenant_name = tenant_name.tenant_name
            url, token = client_auth_service.get_region_access_token_by_tenant(tenant_name, region)
        # 如果团队所在企业所属数据中心信息不存在则使用通用的配置(兼容未申请数据中心token的企业)
        # 管理后台数据需要及时生效，对于数据中心的信息查询使用直接查询原始数据库
        region_info = self.get_region_info(region_name=region)
        if region_info is None:
            raise err_region_not_found
        url = region_info.url
        if not token:
            token = region_info.token
        else:
            token = "Token {}".format(token)
        return url, token

    def __get_region_access_info_by_enterprise_id(self, enterprise_id, region):
        url, token = client_auth_service.get_region_access_token_by_enterprise_id(enterprise_id, region)
        # 管理后台数据需要及时生效，对于数据中心的信息查询使用直接查询原始数据库
        region_info = self.get_region_info(region_name=region)
        if not region_info:
            raise ServiceHandleException("region not found")
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
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_region_info(self, region_name):
        configs = RegionConfig.objects.filter(region_name=region_name)
        if configs:
            return configs[0]
        return None

    def get_enterprise_region_info(self, eid, region):
        configs = RegionConfig.objects.filter(enterprise_id=eid, region_name=region)
        if configs:
            return configs[0]
        else:
            configs = RegionConfig.objects.filter(enterprise_id=eid, region_id=region)
            if configs:
                return configs[0]
        return None

    def get_tenant_image_repositories(self, region, tenant_name, namespace):
        """组件源检测"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/image-repositories?namespace={}".format(namespace)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=20)
        return res, body

    def get_tenant_image_tags(self, region, tenant_name, repository):
        """组件源检测"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/image-tags?repository={}".format(repository)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, timeout=20)
        return res, body

    def service_source_check(self, region, tenant_name, body):
        """组件源检测"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/servicecheck"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    def get_service_check_info(self, region, tenant_name, uuid):
        """组件源检测信息获取"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/servicecheck/" + str(uuid)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def service_chargesverify(self, region, tenant_name, data):
        """组件扩大资源申请接口"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + \
            "/chargesverify?quantity={0}&reason={1}&eid={2}".format(data["quantity"], data["reason"], data["eid"])
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def update_plugin_info(self, region, tenant_name, plugin_id, data):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url += "/v2/tenants/{0}/plugin/{1}".format(tenant_region.region_tenant_name, plugin_id)
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, json.dumps(data), region=region)
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
        return self._post(url, self.default_headers, json.dumps(body), region=region)

    def uninstall_service_plugin(self, region, tenant_name, plugin_id, service_alias, body={}):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin/" + plugin_id
        self._set_headers(token)
        return self._delete(url, self.default_headers, json.dumps(body), region=region)

    def update_plugin_service_relation(self, region, tenant_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/plugin"

        self._set_headers(token)
        return self._put(url, self.default_headers, json.dumps(body), region=region)

    def update_service_plugin_config(self, region, tenant_name, service_alias, plugin_id, body):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)

        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/plugin/" + plugin_id + "/upenv"

        self._set_headers(token)
        return self._put(url, self.default_headers, json.dumps(body), region=region)

    def get_services_pods(self, region, tenant_name, service_id_list, enterprise_id):
        """获取多个组件的pod信息"""
        service_ids = ",".join(service_id_list)
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/pods?enterprise_id=" \
            + enterprise_id + "&service_ids=" + service_ids

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, None, region=region, timeout=10)
        return body

    def export_app(self, region, enterprise_id, data):
        """导出应用"""
        url, token = self.__get_region_access_info_by_enterprise_id(enterprise_id, region)
        url += "/v2/app/export"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data).encode('utf-8'))
        return res, body

    def get_app_export_status(self, region, enterprise_id, event_id):
        """查询应用导出状态"""
        url, token = self.__get_region_access_info_by_enterprise_id(enterprise_id, region)
        url = url + "/v2/app/export/" + event_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def import_app_2_enterprise(self, region, enterprise_id, data):
        """ import app to enterprise"""
        url, token = self.__get_region_access_info_by_enterprise_id(enterprise_id, region)
        url += "/v2/app/import"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def import_app(self, region, tenant_name, data):
        """导入应用"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url += "/v2/app/import"
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def get_app_import_status(self, region, tenant_name, event_id):
        """查询导入状态"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/import/" + event_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_enterprise_app_import_status(self, region, eid, event_id):
        url, token = self.__get_region_access_info_by_enterprise_id(eid, region)
        url = url + "/v2/app/import/" + event_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_enterprise_import_file_dir(self, region, eid, event_id):
        url, token = self.__get_region_access_info_by_enterprise_id(eid, region)
        url = url + "/v2/app/import/ids/" + event_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_import_file_dir(self, region, tenant_name, event_id):
        """查询导入目录"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/import/ids/" + event_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def delete_enterprise_import(self, region, eid, event_id):
        url, token = self.__get_region_access_info_by_enterprise_id(eid, region)
        url = url + "/v2/app/import/" + event_id
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return res, body

    def delete_import(self, region, tenant_name, event_id):
        """删除导入"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/import/" + event_id
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return res, body

    def create_import_file_dir(self, region, tenant_name, event_id):
        """创建导入目录"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/import/ids/" + event_id
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return res, body

    def delete_enterprise_import_file_dir(self, region, eid, event_id):
        url, token = self.__get_region_access_info_by_enterprise_id(eid, region)
        url = url + "/v2/app/import/ids/" + event_id
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return res, body

    def delete_import_file_dir(self, region, tenant_name, event_id):
        """删除导入目录"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/import/ids/" + event_id
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return res, body

    def create_upload_file_dir(self, region, tenant_name, event_id):
        """创建上传文件目录"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/upload/events/" + event_id
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region)
        return res, body

    def get_upload_file_dir(self, region, tenant_name, event_id):
        """查询上传文件目录"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/upload/events/" + event_id
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def update_upload_file_dir(self, region, tenant_name, event_id, component_id):
        """更新上传文件目录"""
        url, token = self.__get_region_access_info(tenant_name, region)
        url = url + "/v2/app/upload/events/" + event_id + "/component_id/" + component_id
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region)
        return res, body

    def backup_group_apps(self, region, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/groupapp/backups"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_backup_status_by_backup_id(self, region, tenant_name, backup_id):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/groupapp/backups/" + str(backup_id)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def delete_backup_by_backup_id(self, region, tenant_name, backup_id):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/groupapp/backups/" + str(backup_id)

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region)
        return body

    def get_backup_status_by_group_id(self, region, tenant_name, group_uuid):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/groupapp/backups?group_id=" + str(group_uuid)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def star_apps_migrate_task(self, region, tenant_name, backup_id, data):
        """发起迁移命令"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/groupapp/backups/" + backup_id + "/restore"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return body

    def get_apps_migrate_status(self, region, tenant_name, backup_id, restore_id):
        """获取迁移结果"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/groupapp/backups/" \
            + backup_id + "/restore/" + restore_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def copy_backup_data(self, region, tenant_name, data):
        """数据中心备份数据进行拷贝"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/groupapp/backupcopy"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return body

    def get_service_build_versions(self, region, tenant_name, service_alias):
        """获取组件的构建版本"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/build-list"

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def delete_service_build_version(self, region, tenant_name, service_alias, version_id, body):
        """删除组件的某次构建版本"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/build-version/" + version_id

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region, body=json.dumps(body))
        return body

    def get_service_build_version_by_id(self, region, tenant_name, service_alias, version_id):
        """查询组件的某次构建版本"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" \
            + service_alias + "/build-version/" + version_id

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_team_services_deploy_version(self, region, tenant_name, data):
        """查询指定组件的部署版本"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/deployversions"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def get_service_deploy_version(self, region, tenant_name, service_alias):
        """查询指定组件的部署版本"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/deployversions"

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    # 获取数据中心应用异常信息

    def get_app_abnormal(self, url, token, region, start_stamp, end_stamp):
        url += "/v2/notificationEvent?start={0}&end={1}".format(start_stamp, end_stamp)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    # 第三方注册api注册方式添加endpoints
    def put_third_party_service_endpoints(self, region, tenant_name, service_alias, data):
        """第三方组件endpoint操作"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/endpoints"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    # 第三方注册api注册方式添加endpoints
    def post_third_party_service_endpoints(self, region, tenant_name, service_alias, data):
        """第三方组件endpoint操作"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/endpoints"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    # 第三方注册api注册方式添加endpoints
    def delete_third_party_service_endpoints(self, region, tenant_name, service_alias, data):
        """第三方组件endpoint操作"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/endpoints"

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    # 第三方组件endpoint数据
    def get_third_party_service_pods(self, region, tenant_name, service_alias):
        """获取第三方组件endpoint数据"""
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/endpoints"

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    # 获取第三方组件健康检测信息
    def get_third_party_service_health(self, region, tenant_name, service_alias):

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/3rd-party/probe"

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    # 修改第三方组件健康检测信息
    def put_third_party_service_health(self, region, tenant_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/3rd-party/probe"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region, body=json.dumps(body))
        return res, body

    # 5.1版本组件批量操作
    def batch_operation_service(self, region, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/batchoperation"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(body), timeout=10)
        return res, body

    # 修改网关自定义配置项
    def upgrade_configuration(self, region, tenant_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        body["tenant_id"] = tenant_region.region_tenant_id
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/rule-config"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, json.dumps(body), region=region)
        logger.debug('-------1111--body----->{0}'.format(body))
        return res, body

    def restore_properties(self, region, tenant_name, service_alias, uri, body):
        """When the upgrade fails, restore the properties of the service"""

        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + uri

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, json.dumps(body), region=region)
        return body

    def list_scaling_records(self, region, tenant_name, service_alias, page=None, page_size=None):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/xparecords"

        if page is not None and page_size is not None:
            url = url + "?page={}&page_size={}".format(page, page_size)

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def create_xpa_rule(self, region, tenant_name, service_alias, data):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/xparules"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body=json.dumps(data), region=region)
        return body

    def update_xpa_rule(self, region, tenant_name, service_alias, data):
        url, token = self.__get_region_access_info(tenant_name, region)
        tenant_region = self.__get_tenant_region_info(tenant_name, region)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias + "/xparules"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body=json.dumps(data), region=region)
        return body

    def update_ingresses_by_certificate(self, region_name, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + region.region_tenant_name + "/gateway/certificate"
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body=json.dumps(body), region=region_name)
        return res, body

    def get_region_resources(self, enterprise_id, **kwargs):
        region_name = kwargs.get("region")
        if kwargs.get("test"):
            self.get_enterprise_api_version_v2(enterprise_id, region=region_name)
        url, token = self.__get_region_access_info_by_enterprise_id(enterprise_id, region_name)
        url = url + "/v2/cluster"
        self._set_headers(token)
        kwargs["retries"] = 1
        kwargs["timeout"] = 5
        res, body = self._get(url, self.default_headers, **kwargs)
        return res, body

    def test_region_api(self, region_data):
        region = RegionConfig(**region_data)
        url = region.url + "/v2/show"
        return self._get(url, self.default_headers, region=region, for_test=True, retries=1, timeout=1)

    def check_region_api(self, enterprise_id, region):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        try:
            url = region_info.url + "/v2/show"
            _, body = self._get(url, self.default_headers, region=region_info.region_name, retries=1, timeout=1)
            return body
        except Exception as e:
            logger.exception(e)
            return None

    def list_gateways(self, enterprise_id, region):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/batch-gateway?eid={0}".format(enterprise_id)
        res, body = self._get(url, self.default_headers, region=region_info.region_name)
        return res, body

    def list_namespaces(self, enterprise_id, region, content):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/namespace?eid={0}&content={1}".format(enterprise_id, content)
        res, body = self._get(url, self.default_headers, region=region_info.region_name)
        return res, body

    def list_namespace_resources(self, enterprise_id, region, content, namespace):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/resource?eid={0}&content={1}&namespace={2}".format(enterprise_id, content, namespace)
        res, body = self._get(url, self.default_headers, region=region_info.region_name)
        return res, body

    def list_convert_resource(self, enterprise_id, region, namespace, content):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/convert-resource?eid={0}&content={1}&namespace={2}".format(enterprise_id, content, namespace)
        res, body = self._get(url, self.default_headers, region=region_info.region_name, timeout=30)
        return res, body

    def resource_import(self, enterprise_id, region, namespace, content):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/convert-resource?eid={0}&content={1}&namespace={2}".format(enterprise_id, content, namespace)
        res, body = self._post(url, self.default_headers, body="", region=region_info.region_name, timeout=30)
        return res, body

    def yaml_resource_name(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/yaml_resource_name?eid={0}".format(enterprise_id)
        res, body = self._get(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=20)
        return res, body

    def yaml_resource_detailed(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/yaml_resource_detailed?eid={0}".format(enterprise_id)
        res, body = self._get(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=20)
        return res, body

    def yaml_resource_import(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/yaml_resource_import?eid={0}".format(enterprise_id)
        res, body = self._post(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=300)
        return res, body

    def add_resource(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/convert-resource?eid={0}".format(enterprise_id)
        res, body = self._post(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=30)
        return res, body

    def list_tenants(self, enterprise_id, region, page=1, page_size=10):
        """list tenants"""
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/tenants?page={0}&pageSize={1}&eid={2}".format(page, page_size, enterprise_id)
        try:
            res, body = self._get(url, self.default_headers, region=region_info.region_name)
            return res, body
        except RegionApiBaseHttpClient.CallApiError as e:
            return {'status': e.message['httpcode']}, e.message['body']

    def set_tenant_limit_memory(self, enterprise_id, tenant_name, region, body):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/tenants/{0}/limit_memory".format(tenant_name)
        res, body = self._post(url, self.default_headers, region=region_info.region_name, body=json.dumps(body))
        return res, body

    def create_service_monitor(self, enterprise_id, region, tenant_name, service_alias, body):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/tenants/{0}/services/{1}/service-monitors".format(tenant_name, service_alias)
        res, body = self._post(url, self.default_headers, region=region_info.region_name, body=json.dumps(body))
        return res, body

    def update_service_monitor(self, enterprise_id, region, tenant_name, service_alias, name, body):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/tenants/{0}/services/{1}/service-monitors/{2}".format(tenant_name, service_alias, name)
        res, body = self._put(url, self.default_headers, region=region_info.region_name, body=json.dumps(body))
        return res, body

    def delete_service_monitor(self, enterprise_id, region, tenant_name, service_alias, name, body):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/tenants/{0}/services/{1}/service-monitors/{2}".format(tenant_name, service_alias, name)
        res, body = self._delete(url, self.default_headers, region=region_info.region_name, body=json.dumps(body))

    def delete_maven_setting(self, enterprise_id, region, name):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/builder/mavensetting/{0}".format(name)
        res, body = self._delete(url, self.default_headers, region=region_info.region_name)
        return res, body

    def add_maven_setting(self, enterprise_id, region, body):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/builder/mavensetting"
        res, body = self._post(url, self.default_headers, region=region_info.region_name, body=json.dumps(body))
        return res, body

    def get_maven_setting(self, enterprise_id, region, name):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/builder/mavensetting/{0}".format(name)
        res, body = self._get(url, self.default_headers, region=region_info.region_name)
        return res, body

    def update_maven_setting(self, enterprise_id, region, name, body):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/builder/mavensetting/{0}".format(name)
        res, body = self._put(url, self.default_headers, region=region_info.region_name, body=json.dumps(body))
        return res, body

    def list_maven_settings(self, enterprise_id, region):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/builder/mavensetting"
        res, body = self._get(url, self.default_headers, region=region_info.region_name)
        return res, body

    def update_app_ports(self, region_name, tenant_name, app_id, data):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id + "/ports"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body=json.dumps(data), region=region_name)
        return body

    def get_app_status(self, region_name, tenant_name, region_app_id):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + region_app_id + "/status"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region_name)
        return body["bean"]

    def get_app_detect_process(self, region_name, tenant_name, region_app_id):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + region_app_id + "/detect-process"

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return body["list"]

    def get_pod(self, region_name, tenant_name, pod_name):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/pods/" + pod_name

        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return body["bean"]

    def install_app(self, region_name, tenant_name, region_app_id, data):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + region_app_id + "/install"

        self._set_headers(token)
        _, _ = self._post(url, self.default_headers, region=region_name, body=json.dumps(data))

    def list_app_services(self, region_name, tenant_name, region_app_id):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + region_app_id + "/services"

        self._set_headers(token)
        _, body = self._get(url, self.default_headers, region=region_name)
        return body["list"]

    def create_application(self, region_name, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("bean", None)

    def batch_create_application(self, region_name, tenant_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/batch_create_apps"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("list", None)

    def update_service_app_id(self, region_name, tenant_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/services/" + service_alias

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("bean", None)

    def batch_update_service_app_id(self, region_name, tenant_name, app_id, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id + "/services"

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("bean", None)

    def update_app(self, region_name, tenant_name, app_id, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("bean", None)

    def create_app_config_group(self, region_name, tenant_name, app_id, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id + "/configgroups"

        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("bean", None)

    def update_app_config_group(self, region_name, tenant_name, app_id, config_group_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id + "/configgroups/" + config_group_name

        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("bean", None)

    def delete_app(self, region_name, tenant_name, app_id, data={}):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id

        self._set_headers(token)
        _, _ = self._delete(url, self.default_headers, region=region_name, body=json.dumps(data))

    def delete_compose_app_by_k8s_app(self, region_name, tenant_name, k8s_app):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/k8s-app/" + k8s_app

        self._set_headers(token)
        _, _ = self._delete(url, self.default_headers, region=region_name)

    def delete_app_config_group(self, region_name, tenant_name, app_id, config_group_name):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id + "/configgroups/" + config_group_name

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region_name)
        return res, body

    def batch_delete_app_config_group(self, region_name, tenant_name, app_id, config_group_names):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/{0}/apps/{1}/configgroups/{2}/batch".format(tenant_region.region_tenant_name, app_id,
                                                                             config_group_names)

        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region_name)
        return res, body

    def check_app_governance_mode(self, region_name, tenant_name, region_app_id, query):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/apps/{}/governance/check?governance_mode={}".format(tenant_region.region_tenant_name,
                                                                                        region_app_id, query)

        self._set_headers(token)
        _, _ = self._get(url, self.default_headers, region=region_name)

    def list_governance_mode(self, region_name, tenant_name):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/cluster/governance-mode"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return body.get("list", None)

    def create_governance_mode_cr(self, region_name, tenant_name, app_id, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{tenant_name}/apps/{app_id}/governance-cr".format(tenant_name=tenant_name, app_id=app_id)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("bean", None)

    def update_governance_mode_cr(self, region_name, tenant_name, app_id, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{tenant_name}/apps/{app_id}/governance-cr".format(tenant_name=tenant_name, app_id=app_id)
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, region=region_name, body=json.dumps(body))
        return body.get("bean", None)

    def delete_governance_mode_cr(self, region_name, tenant_name, app_id):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{tenant_name}/apps/{app_id}/governance-cr".format(tenant_name=tenant_name, app_id=app_id)
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, region=region_name)
        return body.get("bean", None)

    def get_monitor_metrics(self, region_name, tenant, target, app_id, component_id):
        url, token = self.__get_region_access_info(tenant.tenant_name, region_name)
        url = url + "/v2/monitor/metrics?target={target}&tenant={tenant_id}&app={app_id}&component={component_id}".format(
            target=target, tenant_id=tenant.tenant_id, app_id=app_id, component_id=component_id)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return body

    def check_resource_name(self, tenant_name, region_name, rtype, name):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/checkResourceName"

        self._set_headers(token)
        _, body = self._post(
            url, self.default_headers, region=region_name, body=json.dumps({
                "type": rtype,
                "name": name,
            }))
        return body["bean"]

    def parse_app_services(self, region_name, tenant_name, app_id, values):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id + "/parse-services"

        self._set_headers(token)
        _, body = self._post(
            url, self.default_headers, region=region_name, body=json.dumps({
                "values": values,
            }))
        return body["list"]

    def list_app_releases(self, region_name, tenant_name, app_id):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        tenant_region = self.__get_tenant_region_info(tenant_name, region_name)
        url = url + "/v2/tenants/" + tenant_region.region_tenant_name + "/apps/" + app_id + "/releases"

        self._set_headers(token)
        _, body = self._get(url, self.default_headers, region=region_name)
        return body["list"]

    def sync_components(self, tenant_name, region_name, app_id, components):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{tenant_name}/apps/{app_id}/components".format(tenant_name=tenant_name, app_id=app_id)
        self._set_headers(token)
        self._post(url, self.default_headers, body=json.dumps(components), region=region_name)

    def sync_config_groups(self, tenant_name, region_name, app_id, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{tenant_name}/apps/{app_id}/app-config-groups".format(tenant_name=tenant_name, app_id=app_id)
        self._set_headers(token)
        self._post(url, self.default_headers, body=json.dumps(body), region=region_name)

    def sync_plugins(self, tenant_name, region_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{tenant_name}/plugins".format(tenant_name=tenant_name)
        self._set_headers(token)
        self._post(url, self.default_headers, body=json.dumps(body), region=region_name)

    def build_plugins(self, tenant_name, region_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{tenant_name}/batch-build-plugins".format(tenant_name=tenant_name)
        self._set_headers(token)
        self._post(url, self.default_headers, body=json.dumps(body), region=region_name)

    def get_region_license_feature(self, tenant: Tenants, region_name):
        url, token = self.__get_region_access_info(tenant.tenant_name, region_name)
        url = url + "/license/features"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return body

    def list_app_statuses_by_app_ids(self, tenant_name, region_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{tenant_name}/appstatuses".format(tenant_name=tenant_name)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, body=json.dumps(body), region=region_name)
        return body

    def get_component_log(self, tenant_name, region_name, service_alias, pod_name, container_name, follow=False):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        follow = "true" if follow else "false"
        url = url + "/v2/tenants/{}/services/{}/log?podName={}&containerName={}&follow={}".format(
            tenant_name, service_alias, pod_name, container_name, follow)
        self._set_headers(token)
        resp, _ = self._get(url, self._set_headers(token), region=region_name, preload_content=False)
        return resp

    def change_application_volumes(self, tenant_name, region_name, region_app_id):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/apps/{}/volumes".format(tenant_name, region_app_id)
        self._set_headers(token)
        resp, _ = self._put(url, self._set_headers(token), region=region_name)
        return resp

    def get_region_alerts(self, region_name, **kwargs):
        url, token = self.__get_region_access_info(None, region_name)
        url = url + "/api/v1/alerts"
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, region=region_name, timeout=10, retries=1)
        return res, body

    def create_registry_auth(self, tenant_name, region_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/registry/auth".format(tenant_name)
        self._set_headers(token)
        resp, _ = self._post(url, self._set_headers(token), region=region_name, body=json.dumps(body))
        return resp

    def update_registry_auth(self, tenant_name, region_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/registry/auth".format(tenant_name)
        self._set_headers(token)
        resp, _ = self._put(url, self._set_headers(token), region=region_name, body=json.dumps(body))
        return resp

    def delete_registry_auth(self, tenant_name, region_name, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/registry/auth".format(tenant_name)
        self._set_headers(token)
        resp, _ = self._delete(url, self._set_headers(token), region=region_name, body=json.dumps(body))
        return resp

    def get_app_resource(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/k8s-resource"
        res, body = self._get(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=10)
        return res, body

    def create_app_resource(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/k8s-resource?eid={0}".format(enterprise_id)
        res, body = self._post(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=10)
        return res, body

    def update_app_resource(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/k8s-resource"
        res, body = self._put(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=10)
        return res, body

    def delete_app_resource(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/k8s-resource"
        res, body = self._delete(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=10)
        return res, body

    def batch_delete_app_resources(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/batch-k8s-resource"
        res, body = self._delete(url, self.default_headers, body=json.dumps(data), region=region_info.region_name, timeout=20)
        return res, body

    def sync_k8s_resources(self, tenant_name, region_name, data):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/cluster/sync-k8s-resources"
        res, body = self._post(url, self.default_headers, body=json.dumps(data), region=region_name, timeout=100)
        return res, body

    def get_component_k8s_attribute(self, tenant_name, region_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/services/{}/k8s-attributes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._get(url, self.default_headers, body=json.dumps(body), region=region_name)
        return res, body

    def create_component_k8s_attribute(self, tenant_name, region_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/services/{}/k8s-attributes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._post(url, self.default_headers, body=json.dumps(body), region=region_name)
        return res, body

    def update_component_k8s_attribute(self, tenant_name, region_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/services/{}/k8s-attributes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._put(url, self.default_headers, body=json.dumps(body), region=region_name)
        return res, body

    def delete_component_k8s_attribute(self, tenant_name, region_name, service_alias, body):
        url, token = self.__get_region_access_info(tenant_name, region_name)
        url = url + "/v2/tenants/{}/services/{}/k8s-attributes".format(tenant_name, service_alias)
        self._set_headers(token)
        res, body = self._delete(url, self.default_headers, body=json.dumps(body), region=region_name)
        return res, body

    def get_rbd_pods(self, region):
        """获取rbd pod信息"""
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/rbd-resource/pods"
        res, body = self._get(url, self.default_headers, None, region=region, timeout=15)
        return body

    def get_rbd_pod_log(self, region, pod_name, follow=False):
        """获取rbd logs信息"""
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        follow = "true" if follow else "false"
        url = url + "/v2/cluster/rbd-resource/log?pod_name={}&follow={}".format(pod_name, follow)
        res, _ = self._get(url, self.default_headers, None, region=region, preload_content=False)
        return res

    def get_rbd_component_logs(self, region, rbd_name, rows):
        """获取rbd组件日志"""
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/rbd-name/{0}/logs?rows={1}".format(rbd_name, rows)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def get_rbd_log_files(self, region, rbb_name):
        """获取rbd日志文件列表"""
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/log-file?rbd_name={}".format(rbb_name)
        res, body = self._get(url, self.default_headers, region=region)
        return body

    def create_shell_pod(self, region):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/shell-pod"
        data = {"region_name": region}
        res, body = self._post(url, self.default_headers, region=region, body=json.dumps(data))
        return body

    def delete_shell_pod(self, region, pod_name):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/shell-pod"
        data = {"region_name": region, "pod_name": pod_name}
        res, body = self._delete(url, self.default_headers, region=region, body=json.dumps(data))
        return body

    def get_cluster_nodes(self, region):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/nodes"
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_cluster_nodes_arch(self, region):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/nodes/arch"
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_node_info(self, region, node_name):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/nodes/{0}/detail".format(node_name)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def operate_node_action(self, region, node_name, action):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/nodes/{0}/action/{1}".format(node_name, action)
        res, body = self._post(url, self.default_headers, region=region)
        return res, body

    def get_node_labels(self, region, node_name):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/nodes/{0}/labels".format(node_name)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def update_node_labels(self, region, node_name, data):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/nodes/{0}/labels".format(node_name)
        res, body = self._put(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def get_node_taints(self, region, node_name):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/nodes/{0}/taints".format(node_name)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def update_node_taints(self, region, node_name, data):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/nodes/{0}/taints".format(node_name)
        res, body = self._put(url, self.default_headers, region=region, body=json.dumps(data))
        return res, body

    def get_rainbond_components(self, region):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/cluster/rbd-components"
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def get_container_disk(self, region, container_type):
        region_info = self.get_region_info(region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url = url + "/v2/container_disk/{}".format(container_type)
        res, body = self._get(url, self.default_headers, region=region)
        return res, body

    def list_plugins(self, enterprise_id, region_name, official):
        region_info = self.get_enterprise_region_info(enterprise_id, region_name)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url + "/v2/cluster/plugins?official={0}".format(official)
        res, body = self._get(url, self.default_headers, region=region_name, timeout=10)
        return res, body

    def list_abilities(self, enterprise_id, region_name):
        region_info = self.get_enterprise_region_info(enterprise_id, region_name)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url + "/v2/cluster/abilities"
        res, body = self._get(url, self.default_headers, region=region_name, timeout=10)
        return res, body

    def update_ability(self, enterprise_id, region_name, ability_id, body):
        region_info = self.get_enterprise_region_info(enterprise_id, region_name)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url + "/v2/cluster/abilities/{ability_id}".format(ability_id=ability_id)
        res, body = self._put(url, self.default_headers, body=json.dumps(body), region=region_name, timeout=10)
        return res, body

    def get_ability(self, enterprise_id, region_name, ability_id):
        region_info = self.get_enterprise_region_info(enterprise_id, region_name)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url + "/v2/cluster/abilities/{ability_id}".format(ability_id=ability_id)
        res, body = self._get(url, self.default_headers, region=region_name, timeout=10)
        return res, body

    def get_lang_version(self, enterprise_id, region, lang):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/langVersion?language={0}".format(lang)
        res, body = self._get(url, self.default_headers, region=region_info.region_name)
        return body

    def create_lang_version(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/langVersion"
        res, body = self._post(url, self.default_headers, body=json.dumps(data), region=region_info.region_name)
        return body

    def update_lang_version(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/langVersion"
        res, body = self._put(url, self.default_headers, body=json.dumps(data), region=region_info.region_name)
        return body

    def delete_lang_version(self, enterprise_id, region, data):
        region_info = self.get_enterprise_region_info(enterprise_id, region)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url
        url += "/v2/cluster/langVersion"
        res, body = self._delete(url, self.default_headers, body=json.dumps(data), region=region_info.region_name)
        return body

    def post_proxy(self, region_name, path, data):
        region_info = self.get_region_info(region_name)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url + path
        self._set_headers(region_info.token)
        res, body = self._post(url, self.default_headers, region=region_name, body=json.dumps(data))
        return body

    def get_proxy(self, region_name, path):
        region_info = self.get_region_info(region_name)
        if not region_info:
            raise ServiceHandleException("region not found")
        url = region_info.url + path
        self._set_headers(region_info.token)
        res, body = self._get(url, self.default_headers, region=region_name)
        return body
