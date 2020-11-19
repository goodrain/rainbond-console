# -*- coding: utf8 -*-
from console.exception.main import ServiceHandleException


# 20000 ~ 20099 => user
class ErrUserNotFound(ServiceHandleException):
    def __init__(self, message):
        msg = "user not found"
        super(ErrUserNotFound, self).__init__(msg)
        self.msg_show = u"用户不存在"
        self.status_code = 404
        self.error_code = 20000


# 20100 ~ 20199 => app config group
class ErrAppConfigGroupExists(ServiceHandleException):
    def __init__(self):
        msg = "app config group exists"
        super(ErrAppConfigGroupExists, self).__init__(msg)
        self.msg_show = u"应用配置组已存在"
        self.status_code = 409
        self.error_code = 20100


class ErrAppConfigGroupNotFound(ServiceHandleException):
    def __init__(self):
        msg = "app config group not found"
        super(ErrAppConfigGroupNotFound, self).__init__(msg)
        self.msg_show = u"应用配置组不存在"
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
            "oauth service exists", msg_show=u"OAuth 名称已存在", status_code=409, error_code=20100)


# 20400 ~ 20499 => service ports
class ErrK8sServiceNameExists(ServiceHandleException):
    def __init__(self):
        super(ErrK8sServiceNameExists, self).__init__("k8s service name already exists", u"内部域名已存在", 409, 20100)
