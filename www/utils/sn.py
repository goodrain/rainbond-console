# -*- coding: utf8 -*-

from django.conf import settings
from crypt import AuthCode


class SNUtil:
    def __init__(self):
        if hasattr(settings, 'SN'):
            self.sn = settings.SN
            self.str_key = "goodrain_private_cloud_assistant_sn"
            # community\enterprise\vip
            version = self.sn[-2:]
            if version == "01":
                key_str = self.sn[:-2]
                cloud_assistant, username, password, web_type = AuthCode.decode(key_str, self.str_key).split(',')
            self.cloud_assistant = cloud_assistant
            self.username = username
            self.password = password
            self.web_type = web_type
        else:
            # 这里兼容之前的老版本
            self.cloud_assistant = settings.CLOUD_ASSISTANT
            self.username = settings.CLOUD_ASSISTANT + "-admin"
            self.password = ''
            self.web_type = "community"

    @property
    def cloud_assistant(self):
        return self.cloud_assistant

    @property
    def username(self):
        return self.username

    @property
    def password(self):
        return self.password

    @property
    def web_type(self):
        return self.web_type

    def is_private(self):
        return self.web_type == "community"

instance = SNUtil()

