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
        body = self._jsondecode(content)
        if isinstance(body, dict):
            body = Dict(body)
        if 400 <= res.status <= 600:
            logger.debug(url)
            raise self.CallApiError(self.apitype, url, method, res, body)
        else:
            return res, body

    def _request(self, url, method, headers=None, body=None):
        retry_count = 1
        while retry_count:
            try:
                if body is None:
                    response, content = self.http.request(url, method, headers=headers)
                else:
                    response, content = self.http.request(url, method, headers=headers, body=body)
                logger.debug('''{0} "{1}" body={2} response: {3} ------- and content is {4}'''.format(method, url, body, response, content))
                return response, content
            except (socket.error, socket.timeout), e:
                retry_count -= 1
                logger.debug("retry request: %s" % url)
                if retry_count == 0:
                    raise self.ApiSocketError(self.apitype, url, method, Dict({"status": 101}), {"type": "connect error", "error": str(e)})
            except Exception, e:
                logger.error("request fail, url: {0}, method: {1}, headers: {2}, body: {3}".format(url, method, headers, body))
                logger.exception(e)
                raise e

    def _get(self, url, headers):
        response, content = self._request(url, 'GET', headers=headers)
        res, body = self._check_status(url, 'GET', response, content)
        return res, body

    def _post(self, url, headers, body=None):
        if body is not None:
            response, content = self._request(url, 'POST', headers=headers, body=body)
        else:
            response, content = self._request(url, 'POST', headers=headers)
        res, body = self._check_status(url, 'POST', response, content)
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
