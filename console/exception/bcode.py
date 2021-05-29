# -*- coding: utf8 -*-
from console.exception.main import ServiceHandleException


# 20000 ~ 20099 => user
class ErrUserNotFound(ServiceHandleException):
    def __init__(self, message=""):
        msg = "user not found"
        super(ErrUserNotFound, self).__init__(msg)
        self.msg_show = "用户不存在"
        self.status_code = 404
        self.error_code = 20000


# 20100 ~ 20199 => app config group
class ErrAppConfigGroupExists(ServiceHandleException):
    def __init__(self):
        msg = "app config group exists"
        super(ErrAppConfigGroupExists, self).__init__(msg)
        self.msg_show = "应用配置组已存在"
        self.status_code = 409
        self.error_code = 20100


class ErrAppConfigGroupNotFound(ServiceHandleException):
    def __init__(self):
        msg = "app config group not found"
        super(ErrAppConfigGroupNotFound, self).__init__(msg)
        self.msg_show = "应用配置组不存在"
        self.status_code = 404
        self.error_code = 20101


# 20200 ~ 20299 => component monitor
class ErrComponentGraphNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrComponentGraphNotFound, self).__init__("component graph not found", "组件监控图表不存在", 404, 20200)


class ErrComponentGraphExists(ServiceHandleException):
    def __init__(self):
        super(ErrComponentGraphExists, self).__init__("component graph already exists", "组件监控图表已存在", 409, 20201)


class ErrInternalGraphsNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrInternalGraphsNotFound, self).__init__("internal graphs not found", "内置监控图表不存在", 404, 20202)


class ErrServiceMonitorExists(ServiceHandleException):
    def __init__(self):
        super(ErrServiceMonitorExists, self).__init__("service monitor already exists", "配置名称已存在", 409, 20203)


class ErrRepeatMonitoringTarget(ServiceHandleException):
    def __init__(self):
        super(ErrRepeatMonitoringTarget, self).__init__("repeat monitoring target", "配置名称已存在", 409, 20204)


# 20300 ~ 20399 => oauth
class ErrOauthServiceExists(ServiceHandleException):
    def __init__(self):
        super(ErrOauthServiceExists, self).__init__(
            "oauth service exists", msg_show="OAuth 名称已存在", status_code=409, error_code=20300)


class ErrUnSupportEnterpriseOauth(ServiceHandleException):
    def __init__(self):
        super(ErrUnSupportEnterpriseOauth, self).__init__(
            "Unsupported enterprise Oauth service", msg_show="不支持的企业Oauth服务", status_code=400, error_code=20301)


class ErrUnAuthnOauthService(ServiceHandleException):
    def __init__(self):
        super(ErrUnAuthnOauthService, self).__init__(
            "Unauthenticated oauth service", msg_show="该Oauth服务未认证，请认证后重试", status_code=400, error_code=20302)


class ErrExpiredAuthnOauthService(ServiceHandleException):
    def __init__(self):
        super(ErrExpiredAuthnOauthService, self).__init__(
            "oauth authentication information has expired", msg_show="该Oauth服务认证信息已过期，请重新认证", status_code=400, error_code=20303)


# 20400 ~ 20499 => enterprise
class ErrEnterpriseNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrEnterpriseNotFound, self).__init__("enterprise not found", msg_show="企业不存在", status_code=404, error_code=20400)


# 20500 ~ 20599 => service ports
class ErrK8sServiceNameExists(ServiceHandleException):
    def __init__(self):
        super(ErrK8sServiceNameExists, self).__init__("k8s service name already exists", "内部域名已存在", 409, 20500)


class ErrComponentPortExists(ServiceHandleException):
    def __init__(self):
        super(ErrComponentPortExists, self).__init__("component port already exists", "端口已存在", 409, 20501)


# 20600 ~ 20699 => service plugin
class ErrPluginIsUsed(ServiceHandleException):
    def __init__(self):
        super(ErrPluginIsUsed, self).__init__(
            msg="plugin is used by the service", msg_show="该插件被组件使用，无法删除", status_code=409, error_code=20600)


# 20700 ~ 20799 => tenant not found
class ErrTenantNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrTenantNotFound, self).__init__(msg="tenant not found", msg_show="团队不存在", status_code=404, error_code=20700)


# 20800 ~ 20899 => component
class ErrComponentBuildFailed(ServiceHandleException):
    def __init__(self):
        super(ErrComponentBuildFailed, self).__init__(
            msg="failed to build component", msg_show="组件构建失败", status_code=400, error_code=20800)
