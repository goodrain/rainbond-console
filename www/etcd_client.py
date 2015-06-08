import urllib3
import json

import etcd
from www.etcd_result import EtcdResult

import logging
logger = logging.getLogger('default')

class EtcdClient(object):

    _MGET = 'GET'
    _MPUT = 'PUT'
    _MPOST = 'POST'
    _MDELETE = 'DELETE'
    _comparison_conditions = set(('prevValue', 'prevIndex', 'prevExist'))
    _read_options = set(('recursive', 'wait', 'waitIndex', 'sorted', 'consistent'))
    _del_conditions = set(('prevValue', 'prevIndex'))
    def __init__(
            self,
            host='127.0.0.1',
            port=4001,
            version_prefix='/v2',
            read_timeout=60,
            allow_redirect=True,
            protocol='http',
            cert=None,
            ca_cert=None,
            allow_reconnect=False,
    ):

        self._protocol = protocol

        def uri(protocol, host, port):
            return '%s://%s:%d' % (protocol, host, port)

        if not isinstance(host, tuple):
            self._host = host
            self._port = port
        else:
            self._host, self._port = host[0]

        self._base_uri = uri(self._protocol, self._host, self._port)
        self.version_prefix = version_prefix
        self._read_timeout = read_timeout
        self._allow_redirect = allow_redirect
        self._allow_reconnect = allow_reconnect

        kw = {}
        if self._read_timeout > 0:
            kw['timeout'] = self._read_timeout

        if protocol == 'https':
            kw['ssl_version'] = ssl.PROTOCOL_TLSv1
            if cert:
                if isinstance(cert, tuple):
                    # Key and cert are separate
                    kw['cert_file'] = cert[0]
                    kw['key_file'] = cert[1]
                else:
                    kw['cert_file'] = cert
            if ca_cert:
                kw['ca_certs'] = ca_cert
                kw['cert_reqs'] = ssl.CERT_REQUIRED

        self.http = urllib3.PoolManager(num_pools=10, **kw)

        if self._allow_reconnect:
            self._machines_cache = self.machines
            self._machines_cache.remove(self._base_uri)
        else:
            self._machines_cache = []

    @property
    def base_uri(self):
        return self._base_uri

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def protocol(self):
        return self._protocol

    @property
    def read_timeout(self):
        return self._read_timeout

    @property
    def allow_redirect(self):
        return self._allow_redirect

    @property
    def key_endpoint(self):
        return self.version_prefix + '/keys'

    def _sanitize_key(self, key):
        if not key.startswith('/'):
            key = "/{}".format(key)
        return key


    def write(self, key, value, ttl=None, dir=False, append=False, **kwdargs):        
        key = self._sanitize_key(key)
        params = {}
        if value is not None:
            params['value'] = value
        if ttl:
            params['ttl'] = ttl

        if dir:
            if value:
                raise etcd.EtcdException(
                    'Cannot create a directory with a value')
            params['dir'] = "true"

        for (k, v) in kwdargs.items():
            if k in self._comparison_conditions:
                if type(v) == bool:
                    params[k] = v and "true" or "false"
                else:
                    params[k] = v

        method = append and self._MPOST or self._MPUT
        if '_endpoint' in kwdargs:
            path = kwdargs['_endpoint'] + key
        else:
            path = self.key_endpoint + key
            
        response = self.api_execute(path, method, params=params)
        return self._result_from_response(response)


    def read(self, key, **kwdargs):       
        key = self._sanitize_key(key)
        params = {}
        for (k, v) in kwdargs.items():
            if k in self._read_options:
                if type(v) == bool:
                    params[k] = v and "true" or "false"
                else:
                    params[k] = v

        timeout = kwdargs.get('timeout', None)

        response = self.api_execute(
            self.key_endpoint + key, self._MGET, params=params, timeout=timeout)
        return self._result_from_response(response)

    def delete(self, key, recursive=None, dir=None, **kwdargs):        
        key = self._sanitize_key(key)
        kwds = {}
        if recursive is not None:
            kwds['recursive'] = recursive and "true" or "false"
        if dir is not None:
            kwds['dir'] = dir and "true" or "false"

        for k in self._del_conditions:
            if k in kwdargs:
                kwds[k] = kwdargs[k]

        response = self.api_execute(
            self.key_endpoint + key, self._MDELETE, params=kwds)
        return self._result_from_response(response)


    def set(self, key, value, ttl=None):
        
        return self.write(key, value, ttl=ttl)

    def get(self, key):
        
        return self.read(key)
    
    def _result_from_response(self, response):
        try:
            res = json.loads(response.data.decode('utf-8'))
            r = EtcdResult(**res)
            if response.status == 201:
                r.newKey = True
            r.parse_headers(response)
            return r
        except Exception as e:
            logger.exception(e)
    
    def api_execute(self, path, method, params=None, timeout=None):
        some_request_failed = False
        response = False

        if timeout is None:
            timeout = self.read_timeout

        if timeout == 0:
            timeout = None

        if not path.startswith('/'):
            raise ValueError('Path does not start with /')

        while not response:
            try:
                url = self._base_uri + path

                if (method == self._MGET) or (method == self._MDELETE):
                    response = self.http.request(
                        method,
                        url,
                        timeout=timeout,
                        fields=params,
                        redirect=self.allow_redirect)

                elif (method == self._MPUT) or (method == self._MPOST):
                    response = self.http.request_encode_body(
                        method,
                        url,
                        fields=params,
                        timeout=timeout,
                        encode_multipart=False,
                        redirect=self.allow_redirect)
                else:
                    raise etcd.EtcdException(
                        'HTTP method {} not supported'.format(method))

            except urllib3.exceptions.MaxRetryError:
                some_request_failed = True
        return self._handle_server_response(response)

    def _handle_server_response(self, response):
        
        if response.status in [200, 201]:
            return response
        else:
            resp = response.data.decode('utf-8')
            try:
                r = json.loads(resp)
            except ValueError:
                r = None
            return r
