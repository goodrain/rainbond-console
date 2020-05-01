# -*- coding: utf8 -*-
import requests

from console.utils.oauth.base.oauth import OAuth2Interface
from console.utils.oauth.base.oauth import OAuth2User
from console.utils.oauth.base.exception import NoAccessKeyErr, NoOAuthServiceErr
from console.utils.urlutil import set_get_url

import time
import hmac
import base64
import hashlib
import urllib


class Dingtalk(object):
    def __init__(self, url, oauth_token=None):
        self._base_url = url
        self._url = "%s" % (url)
        self.oauth_token = 'Bearer ' + oauth_token
        self.session = requests.Session()
        self.headers = {
            "Accept": "application/json",
            "Authorization": self.oauth_token,
        }

    def _api_get(self, url_suffix, params=None):
        url = '/'.join([self._url, url_suffix])
        try:
            rst = self.session.request(method='GET', url=url, headers=self.headers, params=params)
            print rst.json()
            if rst.status_code == 200:
                data = rst.json()
                if not isinstance(data, (list, dict)):
                    data = None
            else:
                data = None
        except Exception:
            data = None
        return data

    def _api_post(self, url_suffix, params=None, data=None):
        url = '/'.join([self._url, url_suffix])
        try:
            rst = self.session.request(method='POST', url=url, headers=self.headers, data=data, params=params)
            if rst.status_code == 200:
                dat = rst.json()
                if data.get("error_description"):
                    dat = None
            else:
                dat = None
        except Exception:
            dat = None
        return dat

    def get_user(self):
        url_suffix = 'userinfo'
        return self._api_get(url_suffix)


class DingtalkApiV1MiXin(object):
    def set_api(self, host, access_token):
        self.api = Dingtalk(host, oauth_token=access_token)


class DingtalkApiV1(DingtalkApiV1MiXin, OAuth2Interface):
    def __init__(self):
        super(DingtalkApiV1, self).set_session()
        self.request_params = {
            "response_type": "code",
        }

    def get_auth_url(self, home_url=""):
        return "https://oapi.dingtalk.com/connect/qrconnect"

    def get_access_token_url(self, home_url=None):
        return "https://oapi.dingtalk.com/sns/gettoken"

    def get_user_url(self, home_url=""):
        return "https://oapi.dingtalk.com/sns/getuserinfo_bycode"

    def _compute_signature(self, secret, canonicalString):
        message = canonicalString.encode(encoding="utf-8")
        sec = secret.encode(encoding="utf-8")
        return str(base64.b64encode(hmac.new(sec, message, digestmod=hashlib.sha256).digest()))

    def _get_user_info(self, code=None):
        '''
        private function, get access_token
        :return: access_token, refresh_token
        '''
        if not self.oauth_service:
            raise NoOAuthServiceErr("no found oauth service")
        if code:
            headers = {"Content-Type": "application/json"}
            timestamp = str(int(round(time.time()))) + '000'
            signature = self._compute_signature(self.oauth_service.client_secret, timestamp)
            query = {
                "timestamp": timestamp,
                "accessKey": self.oauth_service.client_id,
                "signature": signature,
            }
            query_str = urllib.urlencode(query)
            params = {
                "tmp_auth_code": code,
            }
            url = self.get_user_url(self.oauth_service.home_url) + "?" + query_str
            try:
                rst = self._session.request(method='POST', url=url, headers=headers, json=params)
            except Exception:
                raise NoAccessKeyErr("can not get access key")
            if rst.status_code == 200:
                data = rst.json()
                errcode = data["errcode"]
                errmsg = data["errmsg"]
                if errcode == 0:
                    return data["user_info"]
                else:
                    raise NoAccessKeyErr(errmsg)
            else:
                raise NoAccessKeyErr("can not get user info")
        else:
            raise NoAccessKeyErr("no code")

    def refresh_access_token(self):
        pass

    def get_user_info(self, code=None):
        raw_user_info = self._get_user_info(code=code)
        return OAuth2User(raw_user_info["nick"], raw_user_info["openid"], None), None, None

    def get_authorize_url(self):
        if self.oauth_service:
            params = {
                "appid": self.oauth_service.client_id,
                "scope": "snsapi_login",
                "redirect_uri": urllib.quote(self.oauth_service.redirect_uri + "?service_id=" + str(self.oauth_service.ID)),
            }
            params.update(self.request_params)
            return set_get_url(self.oauth_service.auth_url, params)
        else:
            raise NoOAuthServiceErr("no found oauth service")
