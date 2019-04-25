# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
from rest_framework.response import Response

from console.utils.response import MessageResponse
from www.utils.return_message import general_message


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


class AccountOverdueException(Exception):
    def __init__(self, message):
        super(AccountOverdueException, self).__init__(message)


class CallRegionAPIException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super(CallRegionAPIException, self).__init__(
            "Region api return code {0},error message {1}".format(
                code, message)
        )


class ServiceHandleException(Exception):
    def __init__(self, msg, msg_show=None, status_code=400, error_code=None):
        """
        :param msg: 错误信息(英文)
        :param msg_show: 错误信息(中文)
        :param status_code: http 状态码
        :param error_code: 错误码
        """
        super(Exception, self).__init__(status_code, error_code, msg, msg_show)
        self.msg = msg
        self.msg_show = msg_show or self.msg
        self.status_code = status_code
        self.error_code = error_code or status_code

    @property
    def response(self):
        return MessageResponse(
            self.msg,
            msg_show=self.msg_show,
            status_code=self.status_code,
            error_code=self.error_code
        )


class AbortRequest(ServiceHandleException):
    """终止请求"""
    pass


class RecordNotFound(Exception):
    """
    There is no corresponding record in the database
    """

    def __init__(self, msg):
        super(RecordNotFound, self).__init__(msg)


class RbdAppNotFound(Exception):
    def __init__(self, msg):
        super(RbdAppNotFound, self).__init__(msg)


class InvalidEnvName(Exception):
    def __init__(self, msg="invlaid env name"):
        super(InvalidEnvName, self).__init__(msg)


class EnvAlreadyExist(Exception):
    def __init__(self, env_name=None):
        msg = "env name: {}; already exist.".format(
            env_name) if env_name else "env already exist"
        super(EnvAlreadyExist, self).__init__(msg)
