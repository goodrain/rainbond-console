# -*- coding: utf8 -*-


class UserExistError(Exception):
    """
    用户已存在异常
    """

    def __init__(self, message):
        super(UserExistError, self).__init__(message)


class EmailExistError(Exception):
    """
    邮箱已存在异常
    """

    def __init__(self, message):
        super(EmailExistError, self).__init__(message)


class PhoneExistError(Exception):
    """
    邮箱已存在异常
    """

    def __init__(self, message):
        super(PhoneExistError, self).__init__(message)


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


class TenantNotExistError(BaseException):
    """
    租户不存在
    """


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
    应用不存在
    """


class GroupNotExistError(BaseException):
    """
    应用组不存在
    """


class AuthenticationInfoHasExpiredError(BaseException):
    """
    认证信息已过期
    """
