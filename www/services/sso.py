# -*- coding: utf8 -*-
import logging

import os

from goodrain_web.base import BaseHttpClient

logger = logging.getLogger('default')

SSO_BASE_URL = os.getenv('SSO_BASE_URL', 'https://sso.goodrain.com')


class GoodRainSSOApi(BaseHttpClient):
    def __init__(self, sso_user_id, sso_user_token, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer {0}'.format(sso_user_token)
        }
        self.base_url = SSO_BASE_URL
        self.sso_user_id = sso_user_id
        self.sso_user_token = sso_user_token

    def _encode_params(self, kw):
        args = []
        for k, v in kw.items():
            try:
                qv = v.encode('utf-8') if isinstance(v, unicode) else str(v)
            except:
                qv = v
            args.append('%s=%s' % (k, qv))
        return '&'.join(args)

    def _unpack(self, dict_body):
        data_body = dict_body['data']
        if 'bean' in data_body and data_body['bean']:
            return data_body['bean']
        elif 'list' in data_body and data_body['list']:
            return data_body['list']
        else:
            return dict()

    def get_sso_user_info(self):
        url = '{0}/api/accounts/{1}'.format(self.base_url, self.sso_user_id)
        res, dict_body = self._get(url=url, headers=self.default_headers)
        return self._unpack(dict_body)

    def auth_sso_user_token(self):
        url = '{0}/api/validate_token?token={1}'.format(self.base_url, self.sso_user_token)
        try:
            res, dict_body = self._get(url=url, headers=self.default_headers)
            return True
        except Exception as e:
            logger.exception(e)
            return False
