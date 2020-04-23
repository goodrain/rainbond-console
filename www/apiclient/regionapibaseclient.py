# -*- coding: utf8 -*-
"""
  Created on 2018/8/14.
"""
import json
import logging
import multiprocessing
import os
import socket
import ssl

import certifi
import urllib3
from urllib3.exceptions import MaxRetryError
from addict import Dict
from django.conf import settings

from console.exception.main import ServiceHandleException
from console.repositories.region_repo import region_repo
from goodrain_web.decorator import method_perf_time

logger = logging.getLogger('default')

resource_not_enough_message = {"cluster_lack_of_memory": "集群资源不足，请联系集群管理员", "tenant_lack_of_memory": "团队可用资源不足，请联系企业管理员"}


class RegionApiBaseHttpClient(object):
    class CallApiError(Exception):
        def __init__(self, apitype, url, method, res, body, describe=None):
            self.message = {
                "apitype": apitype,
                "url": url,
                "method": method,
                "httpcode": res.status,
                "body": body,
            }
            self.apitype = apitype
            self.url = url
            self.method = method
            self.body = body
            self.status = res.status

        def __str__(self):
            return json.dumps(self.message)

    class CallApiFrequentError(Exception):
        def __init__(self, apitype, url, method, res, body, describe=None):
            self.message = {
                "apitype": apitype,
                "url": url,
                "method": method,
                "httpcode": res.status,
                "body": body,
            }
            self.apitype = apitype
            self.url = url
            self.method = method
            self.body = body
            self.status = res.status

        def __str__(self):
            return json.dumps(self.message)

    class ApiSocketError(CallApiError):
        pass

    class InvalidLicenseError(Exception):
        pass

    class ResourceNotEnoughError(Exception):
        def __init__(self, status, body):
            self.body = body
            self.status = status
            if resource_not_enough_message[body.msg]:
                self.msg = resource_not_enough_message[body.msg]
            else:
                self.msg = "资源不足，请联系管理员"

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

    def _check_status(self, url, method, status, content):
        body = None
        if content:
            body = self._jsondecode(content)
        res = Dict({"status": status})
        if isinstance(body, dict):
            body = Dict(body)
        if 400 <= status <= 600:
            if status == 409:
                raise self.CallApiFrequentError(
                    self.apitype, url, method, res, body)
            if status == 401 and isinstance(body, dict) and body.get("bean", {}).get("code", -1) == 10400:
                logger.warning(body["bean"]["msg"])
                raise self.InvalidLicenseError()
            if status == 412:
                raise self.ResourceNotEnoughError(status, body)
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
    def _request(self, url, method, headers=None, body=None, *args, **kwargs):
        region_name = kwargs.get("region")
        retries = kwargs.get("retries", 3)
        timeout = kwargs.get("timeout", 5)
        if kwargs.get("for_test"):
            region = region_name
            region_name = region.region_name
        else:
            region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ServiceHandleException("region {0} not found".format(region_name))
        verify_ssl = False
        # 判断是否为https请求
        wsurl_split_list = region.url.split(':')
        if wsurl_split_list[0] == "https":
            verify_ssl = True

        config = Configuration(verify_ssl, region.ssl_ca_cert,
                               region.cert_file, region.key_file,
                               region_name=region_name, enterprise_id=region.enterprise_id)

        client = self.get_client(config)
        try:
            if body is None:
                response = client.request(
                    url=url, method=method, headers=headers, timeout=timeout, retries=retries)
            else:
                response = client.request(
                    url=url, method=method, headers=headers, body=body, timeout=timeout, retries=retries)
            return response.status, response.data
        except socket.timeout as e:
            logger.error('client_error', "timeout: %s" % url)
            logger.exception('client_error', e)
            raise self.CallApiError(self.apitype, url, method, Dict({"status": 101}), {
                "type": "request time out",
                "error": str(e)
            })
        except MaxRetryError as e:
            logger.error('client_error', e)
            raise ServiceHandleException(
                msg="region error: %s" % url, msg_show="超出访问数据中心最大重试次数，请检查网络和配置")
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException(
                msg="region error: %s" % url, msg_show="访问数据中心失败，请检查网络和配置")

    def get_client(self, configuration, pools_size=4, maxsize=None, *args, **kwargs):

        if configuration.verify_ssl:
            cert_reqs = ssl.CERT_REQUIRED
        else:
            cert_reqs = ssl.CERT_NONE

        # ca_certs
        if configuration.ssl_ca_cert:
            ca_certs = configuration.ssl_ca_cert
        else:
            # if not set certificate file, use Mozilla's root certificates.
            ca_certs = certifi.where()

        addition_pool_args = {}
        if configuration.assert_hostname is not None:
            addition_pool_args['assert_hostname'] = configuration.assert_hostname

        if maxsize is None:
            if configuration.connection_pool_maxsize is not None:
                maxsize = configuration.connection_pool_maxsize
            else:
                maxsize = 4

        # https pool manager
        if configuration.proxy:
            self.pool_manager = urllib3.ProxyManager(
                num_pools=pools_size,
                maxsize=maxsize,
                cert_reqs=cert_reqs,
                ca_certs=ca_certs,
                cert_file=configuration.cert_file,
                key_file=configuration.key_file,
                proxy_url=configuration.proxy,
                timeout=3,
                **addition_pool_args)
        else:
            self.pool_manager = urllib3.PoolManager(
                num_pools=pools_size,
                maxsize=maxsize,
                cert_reqs=cert_reqs,
                ca_certs=ca_certs,
                cert_file=configuration.cert_file,
                key_file=configuration.key_file,
                timeout=3,
                **addition_pool_args)
        return self.pool_manager

    def _get(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(
                url, 'GET', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(
                url, 'GET', headers=headers, *args, **kwargs)
        res, body = self._check_status(url, 'GET', response, content)
        return res, body

    def _post(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(
                url, 'POST', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(
                url, 'POST', headers=headers, *args, **kwargs)
        res, body = self._check_status(url, 'POST', response, content)
        return res, body

    def _put(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(
                url, 'PUT', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(
                url, 'PUT', headers=headers, *args, **kwargs)
        res, body = self._check_status(url, 'PUT', response, content)
        return res, body

    def _delete(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(
                url, 'DELETE', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(
                url, 'DELETE', headers=headers, *args, **kwargs)
        res, body = self._check_status(url, 'DELETE', response, content)
        return res, body


def createFile(path, name, body):

    if not os.path.exists(path):
        os.makedirs(path)
    file_path = path + "/" + name
    with open(file_path, 'w') as f:
        f.writelines(body)
        f.close()
    f = open(file_path, "r")
    content = f.read()
    if content == body:
        return file_path
    else:
        return None


def check_file_path(path, name, body):
    file_path = createFile(path, name, body)
    if not file_path:
        check_file_path(path, name, body)
    else:
        return file_path


class Configuration():
    def __init__(self, verify_ssl=True, ssl_ca_cert=None, cert_file=None, key_file=None, assert_hostname=None,
                 region_name=None, enterprise_id=""):
        """
        Constructor
        """
        # Default Base url
        self.host = "https://localhost:8888"

        # SSL/TLS verification
        # Set this to false to skip verifying SSL certificate when calling API from https server.
        self.verify_ssl = verify_ssl
        # Set this to customize the certificate file to verify the peer.
        # 兼容证书路径和内容
        file_path = settings.BASE_DIR + "/data/{0}-{1}/ssl".format(enterprise_id, region_name)
        if not ssl_ca_cert or ssl_ca_cert.startswith('/'):
            self.ssl_ca_cert = ssl_ca_cert
        else:
            path = file_path + "/" + "ca.pem"
            # 判断证书路径是否存在
            if os.path.isfile(path):
                self.ssl_ca_cert = path
            else:
                # 校验证书文件是否写入成功
                self.ssl_ca_cert = check_file_path(
                    file_path, "ca.pem", ssl_ca_cert)

        # client certificate file
        if not cert_file or cert_file.startswith('/'):
            self.cert_file = cert_file
        else:
            path = file_path + "/" + "client.pem"
            if os.path.isfile(path):
                self.cert_file = path
            else:
                self.cert_file = check_file_path(
                    file_path, "client.pem", cert_file)

        # client key file
        if not key_file or key_file.startswith('/'):
            self.key_file = key_file
        else:
            path = file_path + "/" + "client.key.pem"
            if os.path.isfile(path):
                self.key_file = path
            else:
                self.key_file = check_file_path(
                    file_path, "client.key.pem", key_file)

        # Set this to True/False to enable/disable SSL hostname verification.
        self.assert_hostname = assert_hostname

        # urllib3 connection pool's maximum number of connections saved
        # per pool. urllib3 uses 1 connection as default value, but this is
        # not the best value when you are making a lot of possibly parallel
        # requests to the same host, which is often the case here.
        # cpu_count * 5 is used as default value to increase performance.
        self.connection_pool_maxsize = multiprocessing.cpu_count() * 5

        # Proxy URL
        self.proxy = None
        # Safe chars for path_param
        self.safe_chars_for_path_param = ''
