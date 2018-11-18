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
from addict import Dict

from console.repositories.region_repo import region_repo
from goodrain_web.decorator import method_perf_time

logger = logging.getLogger('default')


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

    def _check_status(self, url, method, status, content):
        body = None
        if content:
            body = self._jsondecode(content)
        res = Dict({"status": status})
        if isinstance(body, dict):
            body = Dict(body)
        if 400 <= status <= 600:
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
        region_name = kwargs["region"]
        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise Exception("region {0} not found".format(region_name))
        verify_ssl = False
        # 判断是否为https请求
        wsurl_split_list = region.wsurl.split(':')
        if wsurl_split_list[0] == "wss":
            verify_ssl = True

        config = Configuration(verify_ssl, region.ssl_ca_cert, region.cert_file, region.key_file, region_name=region_name)

        client = self.get_client(config)
        retry_count = 2
        while retry_count:
            try:
                if body is None:
                    response = client.request(
                        url=url, method=method, headers=headers)
                else:
                    response = client.request(
                        url=url, method=method, headers=headers, body=body)

                # if len(content) > 10000:
                #     record_content = '%s  .....ignore.....' % content[:1000]
                # else:
                #     record_content = content
                # if body is not None and len(body) > 1000:
                #     record_body = '%s .....ignore.....' % body[:1000]
                # else:
                #     record_body = body
                return response.status, response.data
            except socket.timeout, e:
                logger.error('client_error', "timeout: %s" % url)
                logger.exception('client_error', e)
                raise self.CallApiError(
                    self.apitype, url, method,
                    Dict({
                        "status": 101
                    }), {"type": "request time out",
                         "error": str(e)})
            except socket.error, e:
                retry_count -= 1
                if retry_count:
                    logger.error("client_error", "retry request: %s" % url)
                else:
                    logger.exception('client_error', e)
                    raise self.ApiSocketError(
                        self.apitype, url, method,
                        Dict({
                            "status": 101
                        }), {"type": "connect error",
                             "error": str(e)})

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
            addition_pool_args[
                'assert_hostname'] = configuration.assert_hostname

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
                **addition_pool_args)
        else:
            self.pool_manager = urllib3.PoolManager(
                num_pools=pools_size,
                maxsize=maxsize,
                cert_reqs=cert_reqs,
                ca_certs=ca_certs,
                cert_file=configuration.cert_file,
                key_file=configuration.key_file,
                **addition_pool_args)
        return self.pool_manager

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
        if ssl_ca_cert.startswith('/'):
            self.ssl_ca_cert = ssl_ca_cert
        else:
            ssl_ca_cert_url = 'etc/data/{0}/ssl/ca.pem'.format(region_name)
            with open(ssl_ca_cert_url, 'w') as f:
                f.writelines(ssl_ca_cert)
                f.close()
            self.ssl_ca_cert = ssl_ca_cert_url
        # client certificate file
        if cert_file.startswith('/'):
            self.cert_file = cert_file
        else:
            cert_file_url = 'etc/data/{0}/ssl/client.pem'.format(region_name)
            with open(cert_file_url, 'w') as f:
                f.writelines(cert_file)
                f.close()
            self.ssl_ca_cert = cert_file_url
        # client key file
        if key_file.startswith('/'):
            self.key_file = key_file
        else:
            key_file_url = 'etc/data/{0}/ssl/client.key.pem'.format(region_name)
            with open(key_file_url, 'w') as f:
                f.writelines(key_file)
                f.close()
            self.ssl_ca_cert = key_file_url
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
