import json
from django.conf import settings

from goodrain_web.base import BaseHttpClient
from www.partners.ucloud.auth import verfy_ac

import logging
logger = logging.getLogger('default')


class UCloudApi(BaseHttpClient):

    def __init__(self, token, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/x-www-form-urlencoded'}
        self.default_params = {'AccessToken': token}

        api_info = settings.UCLOUD_APP
        for k, v in api_info.items():
            setattr(self, k, v)

    def parse_url(self, params):
        params.update(self.default_params)
        path, sig = verfy_ac(self.secret_key, params)
        path = self.api_url + '/?' + path + '&Signature=' + sig
        return path

    def get_user_info(self):
        params = {"Action": "GetUserInfo"}
        url = self.parse_url(params)
        res, body = self._get(url, self.default_headers)
        return body
