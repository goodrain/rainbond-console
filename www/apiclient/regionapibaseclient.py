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
from addict import Dict
from console.exception.main import ServiceHandleException, ErrClusterLackOfMemory, ErrTenantLackOfMemory
from console.repositories.region_repo import region_repo
from django.conf import settings
from django.http import HttpResponse, QueryDict
from urllib3.exceptions import MaxRetryError

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

    def __init__(self, *args, **kwargs):
        self.timeout = 5
        # cache client
        self.clients = {}
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
            if not body:
                raise ServiceHandleException(msg="request region api body is nil", msg_show="集群请求网络异常", status_code=status)
            if "code" in body:
                raise ServiceHandleException(msg=body.get("msg"), status_code=status, error_code=body.get("code"))
            if status == 409:
                raise self.CallApiFrequentError(self.apitype, url, method, res, body)
            if status == 401 and isinstance(body, dict) and body.get("bean", {}).get("code", -1) == 10400:
                logger.warning(body["bean"]["msg"])
                raise self.InvalidLicenseError()
            if status == 412:
                if body.get("msg") == "cluster_lack_of_memory":
                    raise ErrClusterLackOfMemory()
                if body.get("msg") == "tenant_lack_of_memory":
                    raise ErrTenantLackOfMemory()
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

    def get_default_timeout_conifg(self):
        try:
            connect = float(os.environ.get("REGION_CONNECTION_TIMEOUT", 5.0))
            red = float(os.environ.get("REGION_RED_TIMEOUT", 30.0))
        except Exception:
            connect, red = 5.0, 30.0
        return connect, red

    def _request(self, url, method, headers=None, body=None, *args, **kwargs):
        region_name = kwargs.get("region")
        retries = kwargs.get("retries", 2)
        d_connect, d_red = self.get_default_timeout_conifg()
        timeout = kwargs.get("timeout", d_red)
        preload_content = kwargs.get("preload_content")
        if kwargs.get("for_test"):
            region = region_name
            region_name = region.region_name
        else:
            region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ServiceHandleException("region {0} not found".format(region_name), error_code=10412)
        client = self.get_client(region_config=region)
        if not client:
            raise ServiceHandleException(
                msg="create region api client failure", msg_show="创建集群通信客户端错误，请检查集群配置", error_code=10411)
        try:
            if preload_content is False:
                response = client.request(
                    url=url,
                    method=method,
                    headers=headers,
                    preload_content=preload_content,
                    timeout=None,  # None will set an infinite timeout.
                )
                return response, None
            if body is None:
                response = client.request(
                    url=url,
                    method=method,
                    headers=headers,
                    timeout=urllib3.Timeout(connect=d_connect, read=timeout),
                    retries=retries)
            else:
                response = client.request(
                    url=url,
                    method=method,
                    headers=headers,
                    body=body,
                    timeout=urllib3.Timeout(connect=d_connect, read=timeout),
                    retries=retries)
            return response.status, response.data
        except urllib3.exceptions.SSLError:
            self.destroy_client(region_config=region)
            raise ServiceHandleException(error_code=10411, msg="SSLError", msg_show="访问数据中心异常，请稍后重试")
        except socket.timeout as e:
            raise self.CallApiError(self.apitype, url, method, Dict({"status": 101}), {
                "type": "request time out",
                "error": str(e),
                "error_code": 10411,
            })
        except MaxRetryError as e:
            logger.debug("error url {}".format(url))
            logger.exception(e)
            raise ServiceHandleException(error_code=10411, msg="MaxRetryError", msg_show="访问数据中心异常，请稍后重试")
        except Exception as e:
            logger.debug("error url {}".format(url))
            logger.exception(e)
            raise ServiceHandleException(error_code=10411, msg="Exception", msg_show="访问数据中心异常，请稍后重试")

    def destroy_client(self, region_config):
        key = hash(region_config.url + region_config.ssl_ca_cert + region_config.cert_file + region_config.key_file)
        self.clients[key] = None

    def get_client(self, region_config):
        # get client from cache
        key = hash(region_config.url + region_config.ssl_ca_cert + region_config.cert_file + region_config.key_file)
        client = self.clients.get(key, None)
        if client:
            return client
        config = Configuration(region_config)
        pools_size = int(os.environ.get("CLIENT_POOL_SIZE", 20))
        client = self.create_client(config, pools_size)
        self.clients[key] = client
        return client

    def create_client(self, configuration, pools_size=4, maxsize=None, *args, **kwargs):

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
                timeout=5,
                **addition_pool_args)
        else:
            self.pool_manager = urllib3.PoolManager(
                num_pools=pools_size,
                maxsize=maxsize,
                cert_reqs=cert_reqs,
                ca_certs=ca_certs,
                cert_file=configuration.cert_file,
                key_file=configuration.key_file,
                timeout=5,
                **addition_pool_args)
        return self.pool_manager

    def _get(self, url, headers, body=None, *args, **kwargs):
        if body is not None:
            response, content = self._request(url, 'GET', headers=headers, body=body, *args, **kwargs)
        else:
            response, content = self._request(url, 'GET', headers=headers, *args, **kwargs)
        preload_content = kwargs.get("preload_content")
        if preload_content is False:
            return response, None
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

    def proxy(self, request, url, region_name, requests_args=None):
        """
        Forward as close to an exact copy of the request as possible along to the
        given url.  Respond with as close to an exact copy of the resulting
        response as possible.
        If there are any additional arguments you wish to send to requests, put
        them in the requests_args dictionary.
        """
        requests_args = (requests_args or {}).copy()
        headers = self.get_headers(request.META)

        if 'headers' not in requests_args:
            requests_args['headers'] = {}
        if 'body' not in requests_args:
            requests_args['body'] = request.body
        if 'fields' not in requests_args:
            requests_args['fields'] = QueryDict('', mutable=True)

        # Overwrite any headers and params from the incoming request with explicitly
        # specified values for the requests library.
        headers.update(requests_args['headers'])

        # If there's a content-length header from Django, it's probably in all-caps
        # and requests might not notice it, so just remove it.
        for key in list(headers.keys()):
            if key.lower() == 'content-length':
                del headers[key]

        requests_args['headers'] = headers

        region = region_repo.get_region_by_region_name(region_name)
        if not region:
            raise ServiceHandleException("region {0} not found".format(region_name), error_code=10412)
        client = self.get_client(region_config=region)
        response = client.request(method=request.method, timeout=20, url="{}{}".format(region.url, url), **requests_args)

        proxy_response = HttpResponse(response.data, status=response.status)

        excluded_headers = set([
            # Hop-by-hop headers
            # ------------------
            # Certain response headers should NOT be just tunneled through.  These
            # are they.  For more info, see:
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec13.html#sec13.5.1
            'connection',
            'keep-alive',
            'proxy-authenticate',
            'proxy-authorization',
            'te',
            'trailers',
            'transfer-encoding',
            'upgrade',

            # Although content-encoding is not listed among the hop-by-hop headers,
            # it can cause trouble as well.  Just let the server set the value as
            # it should be.
            'content-encoding',

            # Since the remote server may or may not have sent the content in the
            # same encoding as Django will, let Django worry about what the length
            # should be.
            'content-length',
        ])
        for key, value in list(response.headers.items()):
            if key.lower() in excluded_headers:
                continue
            elif key.lower() == 'location':
                # If the location is relative at all, we want it to be absolute to
                # the upstream server.
                proxy_response[key] = self.make_absolute_location(response.url, value)
            else:
                proxy_response[key] = value

        return proxy_response

    def get_headers(self, environ):
        """
        Retrieve the HTTP headers from a WSGI environment dictionary.  See
        https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpRequest.META
        """
        headers = {}
        for key, value in list(environ.items()):
            # Sometimes, things don't like when you send the requesting host through.
            if key.startswith('HTTP_') and key != 'HTTP_HOST':
                headers[key[5:].replace('_', '-')] = value
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                headers[key.replace('_', '-')] = value

        return headers

    def handle_error(self, body):
        region_bcode = json.loads(body)
        if "code" in region_bcode:
            raise ServiceHandleException(
                msg=region_bcode.get("msg"), status_code=region_bcode.get("status"), error_code=region_bcode.get("code"))
        logger.error("request api failure, response body is {}".format(body))
        raise ServiceHandleException(msg="request region api failure", status_code=500, error_code=10411)


def create_file(path, name, body):
    if not os.path.exists(path):
        os.makedirs(path)
    file_path = path + "/" + name
    with open(file_path, 'w') as f:
        f.writelines(body)
    f.close()
    read = ""
    with open(file_path, 'r') as f:
        read = f.read()
    f.close()
    if read != body:
        return None
    return file_path


def check_file_path(path, name, body):
    file_path = create_file(path, name, body)
    if not file_path:
        file_path = create_file(path, name, body)
    return file_path


class Configuration():
    def __init__(self, region_config, assert_hostname=None):
        """
        Constructor
        """
        # create new client
        verify_ssl = False
        # 判断是否为https请求
        wsurl_split_list = region_config.url.split(':')
        if wsurl_split_list[0] == "https":
            verify_ssl = True
        # Default Base url
        self.host = region_config.url

        # SSL/TLS verification
        # Set this to false to skip verifying SSL certificate when calling API from https server.
        self.verify_ssl = verify_ssl
        # Set this to customize the certificate file to verify the peer.
        # 兼容证书路径和内容
        file_path = settings.BASE_DIR + "/data/{0}-{1}/ssl".format(region_config.enterprise_id, region_config.region_name)
        ssl_ca_cert = region_config.ssl_ca_cert
        cert_file = region_config.cert_file
        key_file = region_config.key_file
        if not ssl_ca_cert or ssl_ca_cert.startswith('/'):
            self.ssl_ca_cert = ssl_ca_cert
        else:
            self.ssl_ca_cert = check_file_path(file_path, "ca.pem", ssl_ca_cert)

        # client certificate file
        if not cert_file or cert_file.startswith('/'):
            self.cert_file = cert_file
        else:
            self.cert_file = check_file_path(file_path, "client.pem", cert_file)

        # client key file
        if not key_file or key_file.startswith('/'):
            self.key_file = key_file
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
