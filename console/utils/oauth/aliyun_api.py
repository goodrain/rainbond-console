# -*- coding: utf8 -*-
import requests

from console.utils.oauth.base.oauth import OAuth2Interface
from console.utils.oauth.base.oauth import OAuth2User
from console.utils.oauth.base.exception import NoAccessKeyErr, NoOAuthServiceErr
from console.utils.urlutil import set_get_url


class AliYun(object):
    def __init__(self, url, oauth_token=None, api_version="1"):
        self._api_version = str(api_version)
        self._base_url = url
        self._url = "%s/v%s" % (url, api_version)
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
            print((rst.json()))
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


class AliYunApiV1MiXin(object):
    def set_api(self, host, access_token):
        self.api = AliYun(host, oauth_token=access_token)


class AliYunApiV1(AliYunApiV1MiXin, OAuth2Interface):
    def __init__(self):
        super(AliYunApiV1, self).set_session()
        self.request_params = {
            "response_type": "code",
        }

    def get_auth_url(self, home_url=""):
        return "https://signin.aliyun.com/oauth2/v1/auth"

    def get_access_token_url(self, home_url=None):
        return "https://oauth.aliyun.com/v1/token"

    def get_user_url(self, home_url=""):
        return "https://oauth.aliyun.com/v1/userinfo"

    def _get_access_token(self, code=None):
        '''
        private function, get access_token
        :return: access_token, refresh_token
        '''
        if not self.oauth_service:
            raise NoOAuthServiceErr("no found oauth service")
        if code:
            headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded", "Connection": "close"}
            params = {
                "client_id": self.oauth_service.client_id,
                "client_secret": self.oauth_service.client_secret,
                "code": code,
                "redirect_uri": self.oauth_service.redirect_uri + '?service_id=' + str(self.oauth_service.ID),
                "grant_type": "authorization_code"
            }
            url = self.get_access_token_url(self.oauth_service.home_url)
            try:
                rst = self._session.request(method='POST', url=url, headers=headers, params=params)
            except Exception:
                raise NoAccessKeyErr("can not get access key")
            if rst.status_code == 200:
                data = rst.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                if self.access_token is None:
                    return None, None
                self.set_api("https://oauth.aliyun.com", self.access_token)
                self.update_access_token(self.access_token, self.refresh_token)
                return self.access_token, self.refresh_token
            else:
                raise NoAccessKeyErr("can not get access key")
        else:
            if self.oauth_user:
                self.set_api(self.oauth_service.home_url, self.oauth_user.access_token)
                try:
                    user = self.api.get_user()
                    if user["login"]:
                        return self.oauth_user.access_token, self.oauth_user.refresh_token
                except Exception:
                    if self.oauth_user.refresh_token:
                        try:
                            self.refresh_access_token()
                            return self.access_token, self.refresh_token
                        except Exception:
                            self.oauth_user.delete()
                            raise NoAccessKeyErr("access key is expired, please reauthorize")
                    else:
                        self.oauth_user.delete()
                        raise NoAccessKeyErr("access key is expired, please reauthorize")
            raise NoAccessKeyErr("can not get access key")

    def refresh_access_token(self):
        pass

    def get_user_info(self, code=None):
        access_token, refresh_token = self._get_access_token(code=code)
        user = self.api.get_user()
        return OAuth2User(user["login_name"], user["sub"], None), access_token, refresh_token

    def get_authorize_url(self):
        if self.oauth_service:
            params = {
                "client_id": self.oauth_service.client_id,
                "redirect_uri": self.oauth_service.redirect_uri + "?service_id=" + str(self.oauth_service.ID),
            }
            params.update(self.request_params)
            return set_get_url(self.oauth_service.auth_url, params)
        else:
            raise NoOAuthServiceErr("no found oauth service")
