# -*- coding: utf8 -*-
from console.exception.main import ServiceHandleException


# 20100 ~ 20199 => oauth
class ErrOauthServiceExists(ServiceHandleException):
    def __init__(self):
        super(ErrOauthServiceExists, self).__init__(
            "oauth service exists", msg_show=u"OAuth 名称已存在", status_code=409, error_code=20100)
