# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
from www.utils.return_message import general_message
from rest_framework.response import Response


class BusinessException(Exception):
    def __init__(self, response, *args, **kwargs):
        self.response = response

    def get_response(self):
        if self.response:
            return self.response
        else:
            return Response(
                general_message(10401, "failed", "无数据返回"), status=500)


class ResourceNotEnoughException(Exception):
    def __init__(self, message):
        super(ResourceNotEnoughException, self).__init__(message)


class AccountOverdueException(Exception):
    def __init__(self, message):
        super(AccountOverdueException, self).__init__(message)


class CallRegionAPIException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super(CallRegionAPIException, self).__init__("Region api return code {0},error message {1}".format(code, message))


class ServiceHandleException(Exception):
    def __init__(self, code, message, b_code=None, message_show=None):
        self.code = code
        self.message = message
        if not b_code:
            self.b_code = code
        else:
            self.b_code = b_code
        if not message_show:
            self.message_show = message
        super(CallRegionAPIException, self).__init__(message)

    def get_response(self):
        return Response(
            general_message(self.b_code, self.message, self.message_show), status=self.code)
   