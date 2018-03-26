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
            return Response(general_message(10401, "failed", "无数据返回"), status=500)


class ResourceNotEnoughException(Exception):
    def __init__(self, message):
        super(ResourceNotEnoughException, self).__init__(message)
