# -*- coding: utf8 -*-
from console.exception.main import ServiceHandleException


# 20100 ~ 20199 => oauth
class ErrOauthServiceExists(ServiceHandleException):
    def __init__(self):
        super(ErrOauthServiceExists, self).__init__(
            "oauth service exists", msg_show=u"OAuth 名称已存在", status_code=409, error_code=20100)


# 20600 ~ 20699 => service plugin
class ErrPluginIsUsed(ServiceHandleException):
    def __init__(self):
        super(ErrPluginIsUsed, self).__init__(
            msg="plugin is used by the service", msg_show=u"该插件被组件使用，无法删除", status_code=409, error_code=20600)
