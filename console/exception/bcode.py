# -*- coding: utf8 -*-
from console.exception.main import ServiceHandleException


# 20100 ~ 20199 => oauth
class ErrOauthServiceExists(ServiceHandleException):
    def __init__(self):
        super(ErrOauthServiceExists, self).__init__(
            "oauth service exists", msg_show=u"OAuth 名称已存在", status_code=409, error_code=20100)


# 20200 ~ 20299 => user
class ErrUserNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrUserNotFound, self).__init__("user not found", msg_show=u"用户不存在", status_code=404, error_code=20200)


# 20300 ~ 20399 => enterprise
class ErrEnterpriseNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrEnterpriseNotFound, self).__init__(
            "enterprise not found", msg_show=u"企业不存在", status_code=404, error_code=20300)
