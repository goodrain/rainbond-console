# -*- coding: utf8 -*-
import json
import httplib2
import socket

from addict import Dict

import logging
logger = logging.getLogger('default')


class BaseHttpClient(object):

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
        self.http = httplib2.Http(timeout=20)
        self.apitype = 'Not specified'
        # self.report = Dict({"ok":True})

    def _jsondecode(self, string):
        try:
            pybody = json.loads(string)
        except ValueError:
            pybody = {"raw": string}

        return pybody

    def _check_status(self, url, method, response, content):
        res = Dict(response)
        res.status = int(res.status)
        logger.debug(content)
        body = self._jsondecode(content)
        logger.debug(body)
        if isinstance(body, dict):
            body = Dict(body)
        if 400 <= res.status <= 600:
            logger.debug(url)
            raise self.CallApiError(self.apitype, url, method, res, body)
        else:
            logger.debug(res)
            logger.debug(body)
            return res, body

    def _request(self, url, method, headers=None, body=None):
        retry_count = 2
        while retry_count:
            try:
                if body is None:
                    response, content = self.http.request(url, method, headers=headers)
                else:
                    response, content = self.http.request(url, method, headers=headers, body=body)

                if len(content) > 1000:
                    record_content = '%s  .....ignore.....' % content[:1000]
                else:
                    record_content = content

                if body is not None and len(body) > 1000:
                    record_body = '%s .....ignore.....' % body[:1000]
                else:
                    record_body = body

                logger.debug(
                    'request', '''{0} "{1}" body={2} response: {3} \nand content is {4}'''.format(method, url, record_body, response, record_content))
                return response, content
            except socket.timeout, e:
                logger.exception('client_error', e)
                raise self.CallApiError(self.apitype, url, method, Dict({"status": 101}), {"type": "request time out", "error": str(e)})
            except socket.error, e:
                retry_count -= 1
                if retry_count:
                    logger.error("client_error", "retry request: %s" % url)
                else:
                    logger.exception('client_error', e)
                    raise self.ApiSocketError(self.apitype, url, method, Dict({"status": 101}), {"type": "connect error", "error": str(e)})

    def _get(self, url, headers):
        response, content = self._request(url, 'GET', headers=headers)
        res, body = self._check_status(url, 'GET', response, content)
        return res, body

    def _post(self, url, headers, body=None):
        if body is not None:
            response, content = self._request(url, 'POST', headers=headers, body=body)
        else:
            response, content = self._request(url, 'POST', headers=headers)
        logger.debug(content)
        res, body = self._check_status(url, 'POST', response, content)
        logger.debug(res)
        logger.debug(body)
        return res, body

    def _put(self, url, headers, body=None):
        if body is not None:
            response, content = self._request(url, 'PUT', headers=headers, body=body)
        else:
            response, content = self._request(url, 'PUT', headers=headers)
        res, body = self._check_status(url, 'PUT', response, content)
        return res, body

    def _delete(self, url, headers, body=None):
        if body is not None:
            response, content = self._request(url, 'DELETE', headers=headers, body=body)
        else:
            response, content = self._request(url, 'DELETE', headers=headers)
        res, body = self._check_status(url, 'DELETE', response, content)
        return res, body
