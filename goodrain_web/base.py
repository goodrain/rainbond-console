# -*- coding: utf8 -*-
import json
import httplib2

from addict import Dict

from goodrain_web.errors import CallApiError


class BaseHttpClient(object):
    def __init__(self, *args, **kwargs):
        self.http = httplib2.Http()
        self.apitype = 'Not specified'
        #self.report = Dict({"ok":True})

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
            raise CallApiError(self.apitype, url, method, res, body)
        else:
            return res, body

    def _get(self, url, headers):
        response, content = self.http.request(url, 'GET', headers=headers)
        res, body = self._check_status(url, 'GET', response, content)
        return res, body

    def _post(self, url, headers, body=False):
        if body:
            response, content = self.http.request(url, 'POST', headers=headers, body=body)
        else:
            response, content = self.http.request(url, 'POST', headers=headers)
        res, body = self._check_status(url, 'POST', response, content)
        return res, body

    def _put(self, url, headers, body=False):
        if body:
            response, content = self.http.request(url, 'PUT', headers=headers, body=body)
        else:
            response, content = self.http.request(url, 'PUT', headers=headers)
        res, body = self._check_status(url, 'PUT', response, content)
        return res, body

    def _delete(self, url, headers, body=False):
        if body:
            response, content = self.http.request(url, 'DELETE', headers=headers, body=body)
        else:
            response, content = self.http.request(url, 'DELETE', headers=headers)
        res, body = self._check_status(url, 'DELETE', response, content)
        return res, body
