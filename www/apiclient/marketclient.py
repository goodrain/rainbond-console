# -*- coding: utf8 -*-

import json
import logging

from www.apiclient.baseclient import HttpClient, client_auth_service


logger = logging.getLogger('default')


class MarketOpenAPI(HttpClient):
    """
    云市OpenAPI接口
    """

    def __init__(self, *args, **kwargs):
        HttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json'}

    def publish_all_service_group_data(self, tenant_id, data):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/v1/market/apps/publish"
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
        return self._unpack(body)

    def get_service_group_list(self, tenant_id):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/v1/market/apps/publish"
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def get_service_group_detail(self, tenant_id, group_key, group_version):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/v1/market/apps/settings?group_key={0}&group_version={1}".format(group_key, group_version)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def confirm_access_token(self, domain, market_client_id, market_client_token):
        url = domain + "/openapi/v1/market/confirm"
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def __auth_header(self, market_client_id, market_client_token):
        self.default_headers.update({"X_ENTERPRISE_ID": market_client_id,
                                     "X_ENTERPRISE_TOKEN": market_client_token})
        return self.default_headers
