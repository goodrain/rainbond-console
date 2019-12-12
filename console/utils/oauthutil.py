# -*- coding: utf8 -*-

import requests
from console.utils.git_api.git_api import GitApi


OAUTH_SERVICES = {
    "github": {
        "id": "id",
        "name": "login",
        "email": "email",
    },
    "gitee": {
        "id": "id",
        "name": "login",
        "email": "email",
    },
}


class OAuthType(object):
    """
    填写当前支持的OAuth类型
    不是git仓库的类型，统一归为other
    """
    OAuthType = ("github", "gitlab", "gitee")


class BaseOAuth2(object):
    def __init__(self, oauth_service, oauth_user, code):
        self._session = requests.Session()
        self.oauth_service = oauth_service
        self.oauth_user = oauth_user
        self.code = code
        if self.oauth_user is None:
            self.access_token = None
            self.refresh_token = None
            self.user = None
        else:
            self.access_token = self.oauth_user.access_token
            self.refresh_token = self.oauth_user.refresh_token
            self.user = self.oauth_user.oauth_user_name
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def get_access_token(self):
        pass

    def refresh_access_token(self):
        pass

    def get_user(self):
        pass

    def check_and_refresh_access_token(self):
        pass


class OAuth2(BaseOAuth2):
    def __init__(self, oauth_service, oauth_user=None, code=None):
        super(OAuth2, self).__init__(oauth_service, oauth_user, code)
        self.is_git = self.oauth_service.is_git

    def get_access_token(self):
        if self.oauth_user is None:
            params = {
                "client_id": self.oauth_service.client_id,
                "client_secret": self.oauth_service.client_secret,
                "code": self.code,
                "redirect_uri": self.oauth_service.redirect_uri + '?service_id=' + str(self.oauth_service.ID),
                "grant_type": "authorization_code"
            }
            try:
                rst = self._session.request(method='POST', url=self.oauth_service.access_token_url,
                                            headers=self.headers, params=params)
                if rst.status_code == 200:
                    data = rst.json()
                    self.access_token = data["access_token"]
                    if data.get("error_description"):
                        data = None
                else:
                    data = None
            except Exception:
                data = None
            return data
        else:
            self.check_and_refresh_access_token()

    def refresh_access_token(self):
        if self.oauth_user.refresh_token is None:
            return
        params = {
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        if self.oauth_service.oauth_type == "gitlab":
            params["scope"] = 'api'
        rst = self._session.request(method='POST', url=self.oauth_service.access_token_url,
                                    headers=self.headers, params=params)
        data = rst.json()
        if rst.status_code == 200:
            self.oauth_user.refresh_token = data.get("refresh_token")
            self.oauth_user.access_token = data.get("access_token")
            self.oauth_user = self.oauth_user.save()

    def get_user(self):
        self.headers["Authorization"] = "bearer " + self.access_token
        data = self._session.request(method='GET', url=self.oauth_service.api_url, headers=self.headers).json()
        if self.oauth_service.oauth_type in OAUTH_SERVICES.keys():
            user_name = data[OAUTH_SERVICES[self.oauth_service.oauth_type]["name"]]
            user_id = str(data[OAUTH_SERVICES[self.oauth_service.oauth_type]["id"]])
            user_email = data[OAUTH_SERVICES[self.oauth_service.oauth_type]["email"]]
        else:
            user_name = data.get("name")
            user_id = data.get("id")
            user_email = data.get("email")

        rst = {
            "name": user_name,
            "id": user_id,
            "email": user_email
        }
        return rst

    def check_access_token(self):
        self.headers["Authorization"] = "bearer " + self.access_token
        data = self._session.request(method='GET', url=self.oauth_service.api_url, headers=self.headers)
        return data.status_code

    def check_and_refresh_access_token(self):
        code = self.check_access_token()
        if code == 401:
            self.refresh_access_token()

    @property
    def api(self):
        if self.is_git:
            return GitApi(self.oauth_service, self.oauth_user).api
        else:
            return None
