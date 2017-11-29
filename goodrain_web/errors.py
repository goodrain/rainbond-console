# -*- coding: utf8 -*-
import json


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


class PermissionDenied(Exception):
    def __init__(self, error, redirect_url=None):
        self.error = error
        self.redirect_url = redirect_url

    def __str__(self):
        return self.error


class UrlParseError(Exception):
    def __init__(self, code, error):
        self.code = code
        self.error = error

    def __str__(self):
        return self.error
