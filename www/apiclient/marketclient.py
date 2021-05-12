# -*- coding: utf8 -*-
import json
import logging

from www.apiclient.baseclient import client_auth_service
from www.apiclient.baseclient import HttpClient

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
        url = url + "/openapi/console/v1/enter-market/apps/publish"
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
        return self._unpack(body)

    def get_service_group_list(self, enterprise_id, page, limit, app_group_name):
        url, id, token = client_auth_service.get_market_access_token_by_enterprise_id(enterprise_id)
        url = url + "/openapi/console/v1/enter-market/apps?page={0}&limit={1}".format(page, limit)
        if app_group_name:
            url += "&group_name={0}".format(app_group_name)
        res, body = self._get(url, self.__auth_header(id, token))
        return body

    def get_service_group_detail(self, tenant_id, group_key, group_version, template_version="v1"):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/console/v1/enter-market/apps/templates?\
            group_key={0}&group_version={1}&template_version={2}".format(group_key, group_version, template_version)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def get_remote_app_templates(self, enterprise_id, group_key, group_version, install=False):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_enterprise_id(enterprise_id)
        url = url + "/openapi/console/v1/enter-market/apps/{0}?group_version={1}&install={2}".format(
            group_key, group_version, install)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def batch_get_group_details(self, tenant_id, data):
        """批量下载多个应用信息"""
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/console/v1/enter-market/apps/batch-templates"
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
        return self._unpack(body)

    def confirm_access_token(self, domain, market_client_id, market_client_token):
        url = domain + "/openapi/v1/market/confirm"
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def get_enterprise_account_info(self, tenant_id, enterprise_id):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/console/v1/enterprises/" + enterprise_id
        # url = "http://5000.grcd3008.goodrain.ali-hz.goodrain.net:10080" + "/openapi/v1/enterprises/" + enterprise_id
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        data = self._unpack(body)
        return res, data

    def get_enterprise_team_fee(self, region, enterprise_id, team_id, date):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(team_id)
        url = url + "/openapi/console/v1/enterprises/{0}/bills?date={1}&tid={2}&region={3}\
            ".format(enterprise_id, date, team_id, region)
        # url = "http://5000.grcd3008.goodrain.ali-hz.goodrain.net:10080" + "/openapi/v1/enterprises/" + enterprise_id \
        #       + "/bills?date={0}&tid={1}&region={2}".format(date, team_id, region)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        # data = self._unpack(body)
        return res, body

    def get_enterprise_region_fee(self, region, enterprise_id, team_id, date):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(team_id)
        url = url + "/openapi/console/v1/enterprises/{0}/bills?date={1}&region={2}".format(enterprise_id, date, region)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return res, body

    def get_region_res_price(self, region_name, tenant_id, enterprise_id, memory, disk, rent_time):
        try:
            url, market_client_id, market_client_token = \
                client_auth_service.get_market_access_token_by_tenant(tenant_id)

            url = url + "/openapi/console/v1/enterprises/{0}/regions/{1}/fee".format(enterprise_id, region_name)
            data = {'memory': memory, 'disk': disk, 'rent_time': rent_time}
            res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
            return self._unpack(body), '', res.status
        except self.ApiSocketError as e:
            logger.exception(e)
            msg = e.body.get('msg_show') if e.body else e.message
            return None, msg, e.status

    def buy_region_res(self, region_name, tenant_id, enterprise_id, memory, disk, rent_time):
        try:
            url, market_client_id, market_client_token = \
                client_auth_service.get_market_access_token_by_tenant(tenant_id)

            url = url + "/openapi/console/v1/enterprises/{0}/regions/{1}/purchase".format(enterprise_id, region_name)
            data = {'memory': memory, 'disk': disk, 'rent_time': rent_time}
            res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
            return self._unpack(body), '', res.status
        except self.ApiSocketError as e:
            logger.exception(e)
            msg = e.body.get('msg_show') if e.body else e.message
            return None, msg, e.status
        except self.CallApiError as ex:
            logger.error("invoke market api error !")
            logger.exception(ex)
            if ex.status != 412:
                return None, "系统异常", ex.status
            else:
                return None, "企业余额不足", 10408

    def get_public_regions_list(self, tenant_id, enterprise_id):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        # url = url + "/openapi/v1/enterprises/" + enterprise_id + "/regions"
        url = url + "/openapi/console/v1/enterprises/" + enterprise_id + "/regions"
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        data = self._unpack(body)
        return res, data

    def get_enterprise_regions_resource(self, tenant_id, enterprise_id, region):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/console/v1/enterprises/" + enterprise_id + "/res-usage"

        if region:
            url = '{0}?region={1}'.format(url, region)

        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        data = self._unpack(body)
        return res, data

    def __auth_header(self, market_client_id, market_client_token):
        self.default_headers.update({"X_ENTERPRISE_ID": market_client_id, "X_ENTERPRISE_TOKEN": market_client_token})
        return self.default_headers

    def publish_v2_template_group_data(self, tenant_id, data):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enter-market/apps/templates"
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data), timeout=30)
        return self._unpack(body)

    def publish_v2_create_app(self, tenant_id, data):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enter-market/apps"
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data), timeout=30)
        return self._unpack(body)

    def publish_plugin_template_data(self, tenant_id, data):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enter-market/plugins/share"
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
        return self._unpack(body)

    def get_region_access_token(self, tenant_id, enterprise_id, region):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{0}/regions/{1}/token".format(enterprise_id, region)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        data = self._unpack(body)
        return res, data

    def get_enterprise_share_hub_info(self, eid, repo_type):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_enterprise_id(eid)
        url += "/openapi/console/v1/enter-market/config?repo_type={0}".format(repo_type)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def get_share_hub_info(self, tenant_id, repo_type):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enter-market/config?repo_type={0}".format(repo_type)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def get_enterprise_free_resource(self, tenant_id, enterprise_id, region, user_name):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{0}/resources/one-click".format(enterprise_id)
        data = {"region": region, "user_name": user_name}
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
        return self._unpack(body)

    def get_enterprise_recharge_records(self, tenant_id, enterprise_id, start_time, end_time, page, page_size):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{eid}/orders?type={type}&page={page}&limit={page_size}".format(
            eid=enterprise_id, type="recharge", page=page, page_size=page_size)
        if start_time and end_time:
            url += "&start={start_time}&end={end_time}".format(start_time=start_time, end_time=end_time)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return res, body

    def get_plugins(self, tenant_id, page, limit, plugin_name=''):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/console/v1/enter-market/plugins?page={0}&limit={1}&plugin_name={2}".format(
            page, limit, plugin_name)

        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body), body['data']['total']

    def get_plugin_templates(self, tenant_id, plugin_key, version):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)

        url = url + "/openapi/console/v1/enter-market/plugins/{0}?version={1}".format(plugin_key, version)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def get_enterprise_receipts(self, tenant_id, enterprise_id, receipt_status="Not", page=1, limit=10):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{0}/receipts?receipt_status={1}&page={2}&limit={3}".format(
            enterprise_id, receipt_status, page, limit)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return body

    def create_enterprise_receipts(self, tenant_id, enterprise_id, data):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{0}/receipts".format(enterprise_id)
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
        return self._unpack(body)

    def confirm_enterprise_receipts(self, tenant_id, enterprise_id, data):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{0}/receipts/confirm".format(enterprise_id)
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data))
        return self._unpack(body)

    def get_enterprise_receipt(self, tenant_id, enterprise_id, receipt_id):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{0}/receipts/{1}".format(enterprise_id, receipt_id)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return self._unpack(body)

    def get_enterprise_receipt_orders(self, tenant_id, enterprise_id, start, end):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{0}/receipt-orders?start={1}&end={2}".format(enterprise_id, start, end)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return body

    def get_enterprise_purchase_detail(self, tenant_id, enterprise_id, start, end, page, page_size):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/enterprises/{0}/purchase-detail?page={1}&page_size={2}start={3}&end={4}".format(
            enterprise_id, page, page_size, start, end)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return body

    def get_app_template(self, tenant_id, group_key, version):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/console/v1/enter-market/apps/{0}?group_version={1}".format(group_key, version)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        return body


class MarketOpenAPIV2(HttpClient):
    def __init__(self, *args, **kwargs):
        HttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json'}
        self.version = "v2"

    def __auth_header(self, market_client_id, market_client_token):
        self.default_headers.update({"X_ENTERPRISE_ID": market_client_id, "X_ENTERPRISE_TOKEN": market_client_token})
        return self.default_headers

    def get_app_versions(self, tenant_id, group_key):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/{1}/enter-market/apps/{0}/versions".format(group_key, self.version)
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        if res.get("status") == 200 and not body.get("error_code"):
            return body
        return None

    def get_apps_versions(self, tenant_id):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/v2/enter-market/apps"
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        if res.get("status") == 200 and isinstance(body, list):
            return body
        return None

    def get_apps_versions_by_eid(self, eid, market_id):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_enterprise_id(eid)
        url = url + "/openapi/v2/enter-market/apps"
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        if res.get("status") == 200 and isinstance(body, list):
            return body
        return None

    def get_markets(self, tenant_id):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url = url + "/openapi/v2/enter-markets"
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        if res.get("status") == 200 and not body.get("error_code"):
            return body
        return None

    def get_markets_by_eid(self, eid):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_enterprise_id(eid)
        url = url + "/openapi/v2/enter-markets"
        res, body = self._get(url, self.__auth_header(market_client_id, market_client_token))
        if res.get("status") == 200 and isinstance(body, list):
            return body
        return None

    def create_market_app(self, tenant_id, data):
        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/v2/enter-market/apps"
        res, body = self._post(url, self.__auth_header(market_client_id, market_client_token), json.dumps(data), timeout=30)
        return self._unpack(body)

    def create_market_app_by_enterprise_id(self, enterprise_id, data):
        url, id, token = client_auth_service.get_market_access_token_by_enterprise_id(enterprise_id)
        url += "/openapi/v2/enter-market/apps"
        res, body = self._post(url, self.__auth_header(id, token), json.dumps(data), timeout=30)
        return self._unpack(body)
