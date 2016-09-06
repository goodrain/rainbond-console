# -*- coding: utf8 -*-

from django.conf import settings
from crypt import AuthCode
import json


class SNUtil:
    def __init__(self):
        if hasattr(settings, 'CLOUD_ASSISTANT'):
            self.cloud_assistant = settings.CLOUD_ASSISTANT
            self.username = settings.CLOUD_ASSISTANT + "-admin"
        else:
            self.cloud_assistant = ""
            self.username = ""
        self.password = ''
        self.pricing = "community"
        self.client_id = ''
        self.client_secret = ''
        if hasattr(settings, 'SN'):
            self.sn = settings.SN
            self.str_key = "goodrain_private_cloud_assistant_sn"
            # community\enterprise\vip
            version = self.sn[-2:]
            if version == "01":
                key_str = self.sn[:-2]
                json_str = AuthCode.decode(key_str, self.str_key)
                json_dict = json.loads(json_str)
                self.cloud_assistant = json_dict.get("enterprise", self.cloud_assistant)
                self.username = json_dict.get("username", self.username)
                self.password = json_dict.get("password", "")
                self.pricing = json_dict.get("pricing", "community")
                self.client_id = json_dict.get("client_id", "")
                self.client_secret = json_dict.get("client_secret", "")

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
    def pricing(self):
        return self.pricing

    @property
    def client_id(self):
        return self.client_id

    @property
    def client_secret(self):
        return self.client_secret

    def is_private(self):
        return self.pricing == "community"

instance = SNUtil()

