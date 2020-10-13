# -*- coding: utf8 -*-
from console.exception.main import ServiceHandleException


class UserExistError(Exception):
    """
    用户已存在异常
    """

    def __init__(self, message):
        msg = "用户名已存在"
        super(UserExistError, self).__init__(msg)


class EmailExistError(Exception):
    """
    邮箱已存在异常
    """

    def __init__(self, message):
        msg = "邮箱已存在"
        super(EmailExistError, self).__init__(msg)


class PhoneExistError(Exception):
    """
    手机号已存在异常
    """

    def __init__(self, message):
        msg = "手机号已存在"
        super(PhoneExistError, self).__init__(msg)


class PasswordTooShortError(Exception):
    """
    密码过短
    """

    def __init__(self, message):
        super(PasswordTooShortError, self).__init__(message)


class ParamsError(Exception):
    """
    参数异常
    """

    def __init__(self, message):
        super(ParamsError, self).__init__(message)


class ConfigExistError(Exception):
    """
    配置已存在
    """

    def __init__(self, message):
        super(ConfigExistError, self).__init__(message)


class TenantOverFlowError(Exception):
    """
    租户超过最大配额
    """

    def __init__(self, message):
        super(TenantOverFlowError, self).__init__(message)


class BaseException(Exception):
    def __init__(self, message):
        super(BaseException, self).__init__(message)


class RegionNotExistError(BaseException):
    """
    数据中心不存在
    """
    pass


class RegionAccessError(BaseException):
    """
    数据中心查询出错
    """
    pass


class RegionExistError(BaseException):
    """
    数据中心已存在
    """
    pass


class ClusterExistError(BaseException):
    """
    集群已存在
    """
    pass


class ClusterNotExistError(BaseException):
    """
    集群不存在
    """
    pass


class AccountNotExistError(BaseException):
    """
    账户不存在
    """
    pass


class PasswordWrongError(BaseException):
    """
    密码不正确
    """
    pass


TenantNotExistError = ServiceHandleException(msg="the team is not found", msg_show="团队不存在", status_code=404, error_code=2002)


class TenantExistError(BaseException):
    """
    租户已存在
    """


class NoEnableRegionError(BaseException):
    """
    无已启用数据中心
    """


class UserNotExistError(BaseException):
    """
    用户不存在
    """


class PermTenantsExistError(BaseException):
    """
    用户已存在与租户下
    """


class RegionUnreachableError(BaseException):
    """
    数据中心不可达
    """


class LabelNotExistError(BaseException):
    """
    标签不存在
    """


class LabelExistError(BaseException):
    """
    标签已存在
    """


class ApiInvokeError(BaseException):
    """
    api调用异常
    """


class RegionAddError(BaseException):
    """
    数据中心添加异常
    """


class ExterpriseNotExistError(BaseException):
    """
    企业不存在
    """


class UserNotExistTenantError(BaseException):
    """
    该用户不存在该组
    """


class TenantIdentityNotExistError(BaseException):
    """
    没有这个权限
    """


class SameIdentityError(BaseException):
    """
    修改的权限与原权限相同
    """


class AuthorizationFailedError(BaseException):
    """
    授权失败
    """


class TeamServiceNotExistError(BaseException):
    """
    组件不存在
    """


class GroupNotExistError(BaseException):
    """
    应用不存在
    """


class AuthenticationInfoHasExpiredError(BaseException):
    """
    认证信息已过期
    """


class UserFavoriteNotExistError(BaseException):
    """
    用户收藏视图不存在
    """


# 20000 ~ 20099 => user
class ErrUserNotFound(ServiceHandleException):
    def __init__(self, message):
        msg = "user not found"
        super(ErrUserNotFound, self).__init__(msg)
        self.msg_show = u"用户不存在"
        self.status_code = 404
        self.error_code = 20000
