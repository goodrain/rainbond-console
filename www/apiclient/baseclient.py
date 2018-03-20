# -*- coding: utf8 -*-
import datetime as dt
import json
import logging
import socket

import httplib2
from addict import Dict

from goodrain_web.decorator import method_perf_time
from www.models.main import TenantEnterpriseToken, TenantEnterprise, Tenants

logger = logging.getLogger('default')


class HttpClient(object):

    class CallApiError(Exception):

        def __init__(self, apitype, url, method, res, body, describe=None):
            self.message = {
                "apitype": apitype,
                "url": url,
                "method": method,
                "httpcode": res.status,
                "body": body,
            }
            self.status = res.status

        def __str__(self):
            return json.dumps(self.message)

    class ApiSocketError(CallApiError):
        pass

    def __init__(self, *args, **kwargs):
        self.timeout = 5
        self.apitype = 'Not specified'

    def _jsondecode(self, string):
        try:
            pybody = json.loads(string)
        except ValueError:
            if len(string) < 10000:
                pybody = {"raw": string}
            else:
                pybody = {"raw": "too long to record!"}
        return pybody

    def _check_status(self, url, method, response, content):
        res = Dict(response)
        res.status = int(res.status)
        body = self._jsondecode(content)
        if isinstance(body, dict):
            body = Dict(body)
        if 400 <= res.status <= 600:
            logger.debug(url)
            raise self.CallApiError(self.apitype, url, method, res, body)
        else:
            return res, body

    def _unpack(self, dict_body):
        if 'data' not in dict_body:
            return dict_body

        data_body = dict_body['data']
        if 'bean' in data_body and data_body['bean']:
            return data_body['bean']
        elif 'list' in data_body and data_body['list']:
            return data_body['list']
        else:
            return dict()

    @method_perf_time
    def _request(self, url, method, headers=None, body=None, client=None, *args, **kwargs):
        retry_count = 2
        if client is None:
            client = httplib2.Http(timeout=self.timeout)
        while retry_count:
            try:
                if body is None:
                    response, content = client.request(url, method, headers=headers)
                else:
                    response, content = client.request(url, method, headers=headers, body=body)

                if len(content) > 10000:
                    record_content = '%s  .....ignore.....' % content[:1000]
                else:
                    record_content = content

                # if body is not None and len(body) > 1000:
                #     record_body = '%s .....ignore.....' % body[:1000]
                # else:
                #     record_body = body

                return response, content
            except socket.timeout, e:
                logger.error('client_error', "timeout: %s" % url)
                logger.exception('client_error', e)
                raise self.CallApiError(self.apitype, url, method, Dict({"status": 101}), {"type": "request time out", "error": str(e)})
            except socket.error, e:
                retry_count -= 1
                if retry_count:
                    logger.error("client_error", "retry request: %s" % url)
                else:
                    logger.exception('client_error', e)
                    raise self.ApiSocketError(self.apitype, url, method, Dict({"status": 101}), {"type": "connect error", "error": str(e)})

    def _get(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'GET', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'GET', headers=headers, *args, **kwargs)
        res, body = self._check_status(url, 'GET', response, content)
        return res, body

    def _post(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'POST', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'POST', headers=headers, *args, **kwargs)
        res, body = self._check_status(url, 'POST', response, content)
        return res, body

    def _put(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'PUT', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'PUT', headers=headers, *args, **kwargs)
        res, body = self._check_status(url, 'PUT', response, content)
        return res, body

    def _delete(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'DELETE', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'DELETE', headers=headers, *args, **kwargs)
        res, body = self._check_status(url, 'DELETE', response, content)
        return res, body


cached_enter_token = dict()


class ClientAuthService(object):
    def get_enterprise_by_id(self, enterprise_id):
        try:
            return TenantEnterprise.objects.get(enterprise_id=enterprise_id)
        except TenantEnterprise.DoesNotExist:
            return None

    def save_market_access_token(self, enterprise_id, url, market_client_id, market_client_token):
        """
        保存企业访问云市的api的token
        :param enterprise_id: 要绑定激活的云市企业ID
        :param url: 云市url
        :param market_client_id: 云市业ID
        :param market_client_token: 云市企业token
        :return: 
        """
        enterprise = self.get_enterprise_by_id(enterprise_id)
        if not enterprise:
            return False

        # enterprise的认证信息统一由TenantEnterpriseToken管理
        try:
            token = TenantEnterpriseToken.objects.get(enterprise_id=enterprise.pk, access_target='market')
            token.access_url = url
            token.access_id = market_client_id
            token.access_token = market_client_token
            token.update_time = dt.datetime.now()
            token.save()

            self.reflush_access_token(enterprise_id, 'market')
        except TenantEnterpriseToken.DoesNotExist:
            token = TenantEnterpriseToken()
            token.enterprise_id = enterprise.pk
            token.access_target = 'market'
            token.access_url = url
            token.access_id = market_client_id
            token.access_token = market_client_token
            token.save()

        enterprise.is_active = 1
        enterprise.save()

        return True

    def save_region_access_token(self, enterprise_id, region_name, access_url, access_token, key, crt):
        """
        保存企业访问数据中心api的token
        :param enterprise_id: 企业ID
        :param region_name: 数据中心名字
        :param access_url: 数据中心访问url
        :param access_token: 数据中心访问token
        :param key: 数据中心访问证书key
        :param crt: 数据中心访问证书crt
        :return: 
        """
        enterprise = self.get_enterprise_by_id(enterprise_id)
        if not enterprise:
            return False

        try:
            token = TenantEnterpriseToken.objects.get(enterprise_id=enterprise.pk, access_target=region_name)
            token.access_url = access_url
            token.access_token = access_token
            token.key = key
            token.crt = crt
            token.update_time = dt.datetime.now()
            token.save()

            self.reflush_access_token(enterprise_id, region_name)
        except TenantEnterpriseToken.DoesNotExist:
            token = TenantEnterpriseToken()
            token.enterprise_id = enterprise.pk
            token.access_target = region_name
            token.access_url = access_url
            token.access_token = access_token
            token.key = key
            token.crt = crt
            token.save()

        return True

    def __get_enterprise_access_token(self, enterprise_id, access_target):
        enter = TenantEnterprise.objects.get(enterprise_id=enterprise_id)
        try:
            return TenantEnterpriseToken.objects.get(enterprise_id=enter.pk, access_target=access_target)
        except TenantEnterpriseToken.DoesNotExist:
            return None

    def __get_cached_access_token(self, enterprise_id, access_target):
        key = '-'.join([enterprise_id, access_target])
        return cached_enter_token.get(key)

    def reflush_access_token(self, enterprise_id, access_target):
        enter_token = self.__get_enterprise_access_token(enterprise_id, access_target)

        key = '-'.join([enterprise_id, access_target])
        if not enter_token:
            cached_enter_token[key] = None
        else:
            cached_enter_token[key] = enter_token

        return cached_enter_token[key]

    def get_market_access_token_by_tenant(self, tenant_id):
        tenant = Tenants.objects.get(tenant_id=tenant_id)
        if not tenant:
            return None, None, None

        token = self.__get_cached_access_token(tenant.enterprise_id, 'market')
        if not token:
            token = self.reflush_access_token(tenant.enterprise_id, 'market')

        if not token:
            return None, None, None

        return token.access_url, token.access_id, token.access_token

    def get_region_access_token_by_tenant(self, tenant_name, region_name):
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        if not tenant:
            return None, None

        token = self.__get_cached_access_token(tenant.enterprise_id, region_name)
        if not token:
            token = self.reflush_access_token(tenant.enterprise_id, region_name)

        if not token:
            return None, None

        return token.access_url, token.access_token

    def get_region_access_token_by_enterprise_id(self, enterprise_id, region_name):
        token = self.__get_cached_access_token(enterprise_id, region_name)
        if not token:
            token = self.reflush_access_token(enterprise_id, region_name)

        if not token:
            return None, None

        return token.access_url, token.access_token

    def get_region_access_enterprise_id_by_tenant(self, tenant_name, region_name):
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        if not tenant:
            return None

        token = self.__get_cached_access_token(tenant.enterprise_id, region_name)
        if not token:
            token = self.reflush_access_token(tenant.enterprise_id, region_name)

        if not token:
            return None

        return token.access_id

    def get_market_access_token_by_access_token(self, access_id, access_token):
        try:
            return TenantEnterpriseToken.objects.get(access_target='market', access_id=access_id, access_token=access_token)
        except TenantEnterpriseToken.DoesNotExist:
            return None

client_auth_service = ClientAuthService()
