# -*- coding: utf8 -*-

import logging

from backends.baseclient import BaseHttpClient
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient

logger = logging.getLogger('default')


class HttpInvokeApi(RegionApiBaseHttpClient):
    def __init__(self, *args, **kwargs):
        RegionApiBaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            # 'Authorization': 'Token 5ca196801173be06c7e6ce41d5f7b3b8071e680a'
        }
        self.base_url = ""

    def update_client(self, region):
        self.default_headers.update({"Authorization": "{}".format(region.token)})
        self.base_url = region.url
        # self.base_url = "http://test.goodrain.com:6200"

    def get_region_nodes(self, body):
        url = self.base_url + "/v2/nodes"
        res, body = self._get(url, self.default_headers, body)
        return res, body

    def add_node(self, body):
        url = self.base_url + "/v2/nodes"
        res, body = self._post(url, self.default_headers, body)
        return res, body

    def get_node_brief_info(self, node_uuid, body):
        url = self.base_url + "/v2/nodes/" + node_uuid + "/basic"
        res, body = self._get(url, self.default_headers, body)
        return res, body

    def get_node_info(self, node_uuid, body):
        url = self.base_url + "/v2/nodes/" + node_uuid + "/details"
        res, body = self._get(url, self.default_headers, body)
        return res, body

    def update_node_info(self, node_uuid, body):
        url = self.base_url + "/v2/nodes/" + node_uuid
        res, body = self._put(url, self.default_headers, body)
        return res, body

    def delete_node(self, node_uuid, body):
        url = self.base_url + "/v2/nodes/" + node_uuid
        res, body = self._delete(url, self.default_headers, body)
        return res, body

    def online_node(self, node_uuid, body):
        url = self.base_url + "/v2/nodes/" + node_uuid
        res, body = self._put(url, self.default_headers, body)
        return res, body

    def offline_node(self, node_uuid, body):
        url = self.base_url + "/v2/nodes/" + node_uuid + "/down"
        res, body = self._post(url, self.default_headers, body)
        return res, body

    def schedulable_node(self, node_uuid, body):
        url = self.base_url + "/v2/nodes/" + node_uuid + "/reschedulable"
        res, body = self._put(url, self.default_headers, body)
        return res, body

    def unschedulable_node(self, node_uuid, body):
        url = self.base_url + "/v2/nodes/" + node_uuid + "/unschedulable"
        res, body = self._put(url, self.default_headers, body)
        return res, body

    def node_login_check(self, body):
        url = self.base_url + "/v2/nodes/login"
        res, body = self._put(url, self.default_headers, body)
        return res, body

    def node_init_status(self, node_ip, body):
        url = self.base_url + "/v2/nodes/" + node_ip + "/init/status"
        res, body = self._get(url, self.default_headers, body)
        return res, body

    def node_component_init(self, node_ip, body):
        url = self.base_url + "/v2/nodes/" + node_ip + "/init"
        res, body = self._put(url, self.default_headers, body, is_init=True)
        return res, body

    def node_component_status(self, node_ip, body):
        url = self.base_url + "/v2/nodes/" + node_ip + "/install/status"
        res, body = self._get(url, self.default_headers, body)
        return res, body

    def node_component_install(self, node_ip, body):
        url = self.base_url + "/v2/nodes/" + node_ip + "/install"
        res, body = self._put(url, self.default_headers, body)
        return res, body

    def update_node_labels(self, region, node_uuid, body):
        self.update_client(region)
        url = self.base_url + "/v2/nodes/" + node_uuid + "/labels"
        res, body = self._put(url, self.default_headers, region=region.region_name, body=body)
        return res, body

    def get_region_resources(self):
        url = self.base_url + "/v2/nodes/resources"
        res, body = self._get(url, self.default_headers)
        return res, body

    def get_region_resource(self, region):
        self.update_client(region)
        url = self.base_url + "/v2/nodes/fullres"
        res, body = self._get(url, self.default_headers, region=region.region_name)
        return res, body

    # 查看数据中心下团队的资源内存剩余
    def get_tenant_limit_memory(self, region, body):
        self.update_client(region)
        url = self.base_url + "/v2/resources/tenants"
        res, body = self._post(url, self.default_headers, body, region=region.region_name)
        return res, body

    # 查看团队在某数据中心的应用状态
    def get_tenant_service_status(self, region):
        self.update_client(region)
        url = self.base_url + "/v2/tenants/services_status"
        res, body = self._get(url, self.default_headers, region=region.region_name)
        return res, body
