# -*- coding: utf8 -*-
"""
  Created on 2018/8/14.
"""
import json
import logging
import multiprocessing
import socket
import ssl
import certifi
import urllib3
from urllib import parse
import os
from django.conf import settings
from addict import Dict
from back_manager.decorator import method_perf_time
from urllib3.exceptions import MaxRetryError

logger = logging.getLogger('default')


class CallApiError(Exception):
    def __init__(self, apitype, url, method, res, body, describe=None):
        self.body = body
        self.message = {
            "apitype": apitype,
            "url": url,
            "method": method,
            "httpcode": res.status,
            "body": body,
        }
        self.api_message = "调用API失败"
        if body is not None and body.get("error", None) is not None:
            self.api_message = body.get("error")
        self.status = res.status

    def __str__(self):
        return json.dumps(self.message)

    def get_error(self):
        if self.body is None or not isinstance(self.body, dict) or self.body.get("error", None):
            return "调用API失败"
        self.body["error"]


class RegionApiBaseHttpClient(object):
    def __init__(self, region, timeout=5, *args, **kwargs):
        if not region:
            raise Exception("region can not be null")
        self.timeout = timeout
        self.apitype = 'Not specified'
        self.region = region
        verify_ssl = False
        # 判断是否为https请求
        region_api_host = parse.urlparse(self.region.url)
        if region_api_host.scheme == "https":
            verify_ssl = True
        self.host = region_api_host
        self.config = Configuration(
            verify_ssl=verify_ssl,
            ssl_ca_cert=self.region.ssl_ca_cert,
            cert_file=self.region.cert_file,
            key_file=self.region.key_file,
            region_name=self.region.region_name,
        )
        self.client = self.get_client(self.config)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json'}
        if self.region.token:
            self.default_headers.update({"Authorization": self.region.token})

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
        if 500 <= status <= 600:
            raise CallApiError(self.apitype, url, method, res, body)
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
    def _request(self, url, method, body=None, *args, **kwargs):
        url = "{0}://{1}{2}".format(self.host.scheme, self.host.netloc, url)
        retry_count = kwargs.get("retry_count", 2)
        timeout = kwargs.get("retry_count", self.timeout)
        while retry_count:
            try:
                if body is None:
                    response = self.client.request(url=url, method=method, headers=self.default_headers, timeout=timeout)
                else:
                    response = self.client.request(url=url,
                                                   method=method,
                                                   headers=self.default_headers,
                                                   body=json.dumps(body),
                                                   timeout=self.timeout)
                return response.status, response.data
            except socket.timeout as e:
                logger.error('client_error', "timeout: %s" % url)
                logger.exception('client_error', e)
                raise CallApiError(self.apitype, url, method, Dict({"status": 101}), {
                    "type": "request time out",
                    "error": str(e)
                })
            except socket.error as e:
                retry_count -= 1
                if retry_count:
                    logger.error("client_error", "retry request: %s" % url)
                else:
                    logger.exception('client_error', e)
                    raise CallApiError(self.apitype, url, method, Dict({"status": 101}), {
                        "type": "connect error",
                        "error": str(e)
                    })
            except MaxRetryError as e:
                # TODO: more friendly error handling
                logger.exception(e)
                raise CallApiError(self.apitype, url, method, Dict({"status": 101}), {"type": "connect error", "error": str(e)})

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
            self.pool_manager = urllib3.ProxyManager(num_pools=pools_size,
                                                     maxsize=maxsize,
                                                     cert_reqs=cert_reqs,
                                                     ca_certs=ca_certs,
                                                     cert_file=configuration.cert_file,
                                                     key_file=configuration.key_file,
                                                     proxy_url=configuration.proxy,
                                                     **addition_pool_args)
        else:
            self.pool_manager = urllib3.PoolManager(num_pools=pools_size,
                                                    maxsize=maxsize,
                                                    cert_reqs=cert_reqs,
                                                    ca_certs=ca_certs,
                                                    cert_file=configuration.cert_file,
                                                    key_file=configuration.key_file,
                                                    **addition_pool_args)
        return self.pool_manager

    def GET(self, url, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'GET', body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'GET', *args, **kwargs)
        res, body = self._check_status(url, 'GET', response, content)
        return res, body

    def POST(self, url, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'POST', body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'POST', *args, **kwargs)
        res, body = self._check_status(url, 'POST', response, content)
        return res, body

    def PUT(self, url, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'PUT', body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'PUT', *args, **kwargs)
        res, body = self._check_status(url, 'PUT', response, content)
        return res, body

    def DELETE(self, url, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'DELETE', body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'DELETE', *args, **kwargs)
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


def get_ssl_file_path(region_name):
    return settings.BASE_DIR + "/data/{0}/ssl".format(region_name)


def clear_ssl_file(region_name):
    file_path = get_ssl_file_path(region_name)
    for root, dirs, files in os.walk(file_path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.remove(os.path.join(root, name))


class Configuration():
    def __init__(self,
                 verify_ssl=True,
                 ssl_ca_cert=None,
                 cert_file=None,
                 key_file=None,
                 assert_hostname=None,
                 region_name=None):
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
        file_path = get_ssl_file_path(region_name)
        if not ssl_ca_cert or ssl_ca_cert.startswith('/'):
            self.ssl_ca_cert = ssl_ca_cert
        else:
            path = file_path + "/" + "ca.pem"
            # 判断证书路径是否存在
            if os.path.isfile(path):
                self.ssl_ca_cert = path
            else:
                # 校验证书文件是否写入成功
                self.ssl_ca_cert = check_file_path(file_path, "ca.pem", ssl_ca_cert)

        # client certificate file
        if not cert_file or cert_file.startswith('/'):
            self.cert_file = cert_file
        else:
            path = file_path + "/" + "client.pem"
            if os.path.isfile(path):
                self.cert_file = path
            else:
                self.cert_file = check_file_path(file_path, "client.pem", cert_file)

        # client key file
        if not key_file or key_file.startswith('/'):
            self.key_file = key_file
        else:
            path = file_path + "/" + "client.key.pem"
            if os.path.isfile(path):
                self.key_file = path
            else:
                self.key_file = check_file_path(file_path, "client.key.pem", key_file)
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
