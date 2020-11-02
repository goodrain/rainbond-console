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
        super(CallRegionAPIException, self).__init__("Region api return code {0},error message {1}".format(code, message))


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
        return MessageResponse(self.msg, msg_show=self.msg_show, status_code=self.status_code, error_code=self.error_code)


class RegionNotFound(ServiceHandleException):
    """
    region not found exception
    """

    def __init__(self, msg):
        super(RegionNotFound, self).__init__("region not found")


class AbortRequest(ServiceHandleException):
    """终止请求"""
    pass


class RecordNotFound(Exception):
    """
    There is no corresponding record in the database
    """

    def __init__(self, msg):
        super(RecordNotFound, self).__init__(msg)


class RbdAppNotFound(ServiceHandleException):
    def __init__(self, msg):
        super(RbdAppNotFound, self).__init__(msg)


class InvalidEnvName(Exception):
    def __init__(self, msg="invlaid env name"):
        super(InvalidEnvName, self).__init__(msg)


class EnvAlreadyExist(Exception):
    def __init__(self, env_name=None):
        msg = "env name: {}; already exist.".format(env_name) if env_name else "env already exist"
        super(EnvAlreadyExist, self).__init__(msg)


class ServiceRelationAlreadyExist(Exception):
    def __init__(self):
        msg = "service relation already exist"
        super(ServiceRelationAlreadyExist, self).__init__(msg)


class InnerPortNotFound(Exception):
    def __init__(self):
        super(InnerPortNotFound, self).__init__("inner port not found")


class ErrInvalidVolume(Exception):
    def __init__(self, msg):
        super(ErrInvalidVolume, self).__init__(msg)


class ErrDepVolumeNotFound(Exception):
    def __init__(self, dep_service_id, dep_vol_name):
        msg = "dep service id: {}; volume name: {}; dep volume not found".format(dep_service_id, dep_vol_name)
        super(ErrDepVolumeNotFound, self).__init__(msg)


class ErrPluginAlreadyInstalled(Exception):
    def __init__(self, msg):
        super(ErrPluginAlreadyInstalled, self).__init__(msg)


class ErrDoNotSupportMultiDomain(Exception):
    def __init__(self, msg):
        super(ErrDoNotSupportMultiDomain, self).__init__(msg)


class MarketAppLost(ServiceHandleException):
    def __init__(self, msg):
        super(MarketAppLost, self).__init__(msg)


class CheckThirdpartEndpointFailed(ServiceHandleException):
    def __init__(self, msg="check endpoint failed", msg_show="校验实例地址失败"):
        super(CheckThirdpartEndpointFailed, self).__init__(msg=msg, msg_show=msg_show, status_code=500)


class ExportAppError(ServiceHandleException):
    def __init__(self, msg="export error", msg_show="导出失败", status_code=500):
        super(ExportAppError, self).__init__(msg, msg_show, status_code)


class NoPermissionsError(ServiceHandleException):
    def __init__(self, msg="no permissions ", msg_show="没有操作权限", status_code=403, error_code=10402):
        super(NoPermissionsError, self).__init__(msg, msg_show, status_code, error_code)


class StoreNoPermissionsError(ServiceHandleException):
    def __init__(self, bean=None):
        super(StoreNoPermissionsError, self).__init__(
            msg="no store permissions", msg_show="没有云应用商店操作权限,去认证", status_code=403, error_code=10407)
        self.bean = bean

    @property
    def response(self):
        return MessageResponse(
            self.msg, msg_show=self.msg_show, status_code=self.status_code, error_code=self.error_code, bean=self.bean)


class ErrVolumePath(ServiceHandleException):
    def __init__(self):
        super(ErrVolumePath, self).__init__(msg="path error", msg_show="请输入符合规范的路径（如：/tmp/volumes）", status_code=412)
