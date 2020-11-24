# -*- coding: utf8 -*-
import logging

import requests

from console.utils.oauth.base.exception import (NoAccessKeyErr, NoOAuthServiceErr)
from console.utils.oauth.base.git_oauth import GitOAuth2Interface
from console.utils.oauth.base.oauth import OAuth2User
from console.utils.urlutil import set_get_url

logger = logging.getLogger("default")


class Gitee(object):
    def __init__(self, url, oauth_token=None, api_version="5"):
        self._api_version = str(api_version)
        self._base_url = url
        self._url = "%s/api/v%s" % (url, api_version)
        self.oauth_token = 'bearer ' + oauth_token
        self.session = requests.Session()
        self.headers = {
            "Accept": "application/json",
            "Authorization": self.oauth_token,
        }

    def _api_get(self, url_suffix, params=None, **kwargs):
        url = '/'.join([self._url, url_suffix])
        try:
            rst = self.session.request(method='GET', url=url, headers=self.headers, params=params)
            if rst.status_code == 200:
                data = rst.json()
                if not isinstance(data, (list, dict)):
                    data = None
                if kwargs.get("get_tatol", False):
                    return data, rst.headers.get('total_count', 0)
            else:
                logger.warning("get gitee api status is {0}".format(rst.status_code))
                data = None
        except Exception as e:
            logger.exception(e)
            data = None
        return data, 0

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
        url_suffix = 'user'
        return self._api_get(url_suffix)

    def get_repos(self, **kwargs):
        url_suffix = 'user/repos'
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 10)
        params = {
            "page": page,
            "per_page": per_page,
            "sort": "updated",
        }
        return self._api_get(url_suffix, params, get_tatol=True)

    def search_repos(self, full_name, **kwargs):
        url_suffix = 'user/repos'
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 10)
        params = {"page": page, "per_page": per_page, "sort": "pushed", "q": full_name.split("/")[-1]}
        return self._api_get(url_suffix, params, get_tatol=True)

    def get_repo(self, full_name):
        url_suffix = 'repos/{full_name}'.format(full_name=full_name)
        return self._api_get(url_suffix)

    def get_branches(self, full_name):
        url_suffix = 'repos/{full_name}/branches'.format(full_name=full_name)
        return self._api_get(url_suffix)

    def get_tags(self, full_name):
        url_suffix = 'repos/{full_name}/tags'.format(full_name=full_name)
        return self._api_get(url_suffix)

    def create_hook(self, host, endpoint, full_name):
        url_suffix = 'repos/{full_name}/hooks'.format(full_name=full_name)
        data = {"url": '{host}/{endpoint}'.format(host=host, endpoint=endpoint), "push_events": True}
        return self._api_post(url_suffix, data=data)


class GiteeApiV5MiXin(object):
    def set_api(self, host, access_token):
        self.api = Gitee(host, oauth_token=access_token)


class GiteeApiV5(GiteeApiV5MiXin, GitOAuth2Interface):
    def __init__(self):
        super(GiteeApiV5, self).set_session()
        self.events = ["push"]
        self.request_params = {
            "response_type": "code",
        }

    def get_auth_url(self, home_url=None):
        home_url.strip().strip("/")
        return "/".join([home_url, "oauth/authorize"])

    def get_access_token_url(self, home_url=None):
        home_url.strip().strip("/")
        return "/".join([home_url, "oauth/token"])

    def get_user_url(self, home_url=None):
        home_url.strip().strip("/")
        return "/".join([home_url, "api/v5/user"])

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
                self.set_api(self.oauth_service.home_url, self.access_token)
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
        headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}

        params = {
            "refresh_token": self.oauth_user.refresh_token,
            "grant_type": "refresh_token",
        }
        rst = self._session.request(method='POST', url=self.oauth_service.access_token_url, headers=headers, params=params)
        data = rst.json()
        if rst.status_code == 200:
            self.oauth_user.refresh_token = data.get("refresh_token")
            self.oauth_user.access_token = data.get("access_token")
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.set_api(self.oauth_service.home_url, self.oauth_user.access_token)
            self.oauth_user = self.oauth_user.save()
        return

    def get_user_info(self, code=None):
        access_token, refresh_token = self._get_access_token(code=code)
        user = self.api.get_user()
        return OAuth2User(user[0]["login"], user[0]["id"], user[0]["email"]), access_token, refresh_token

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

    def get_repos(self, *args, **kwargs):
        access_token, _ = self._get_access_token()
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 10)
        repo_list = []
        repos, total = self.api.get_repos(page=page, per_page=per_page)
        if repos:
            for repo in repos:
                repo_list.append({
                    "project_id": repo["id"],
                    "project_full_name": repo["full_name"],
                    "project_name": repo["name"],
                    "project_description": repo["description"],
                    "project_url": repo["html_url"],
                    "project_default_branch": repo["default_branch"],
                    "project_ssl_url": repo["ssh_url"],
                    "updated_at": repo["updated_at"],
                    "created_at": repo["created_at"]
                })
        return repo_list, total

    def search_repos(self, full_name, *args, **kwargs):
        access_token, _ = self._get_access_token()
        page = int(kwargs.get("page", 1))
        repo_list = []
        search_name = full_name.split("/")
        owner = search_name[0]
        query = "/".join(search_name[1:])
        repos, total = self.api.search_repos(full_name=full_name, page=page, owner=owner, query=query)
        if repos:
            for repo in repos:
                if repo:
                    repo_list.append({
                        "project_id": repo["id"],
                        "project_full_name": repo["full_name"],
                        "project_name": repo["name"],
                        "project_description": repo["description"],
                        "project_url": repo["html_url"],
                        "project_default_branch": repo["default_branch"],
                        "project_ssl_url": repo["ssh_url"],
                        "updated_at": repo["updated_at"],
                        "created_at": repo["created_at"]
                    })
        return repo_list, total

    def get_repo_detail(self, full_name, *args, **kwargs):
        access_token, _ = self._get_access_token()
        repo_list = []
        repos = [self.api.get_repo(full_name)]
        for repo in repos:
            if repo and full_name == repo["full_name"]:
                repo_list.append({
                    "project_id": repo["id"],
                    "project_full_name": repo["full_name"],
                    "project_name": repo["name"],
                    "project_description": repo["description"],
                    "project_url": repo["html_url"],
                    "project_default_branch": repo["default_branch"],
                    "project_ssl_url": repo["ssh_url"],
                    "updated_at": repo["updated_at"],
                    "created_at": repo["created_at"]
                })
        return repo_list

    def get_branches(self, full_name):
        access_token, _ = self._get_access_token()
        rst_list = []
        if self.api.get_tags(full_name=full_name) is not None:
            for branch in self.api.get_branches(full_name=full_name):
                rst_list.append(branch["name"])
        return rst_list

    def get_tags(self, full_name):
        access_token, _ = self._get_access_token()
        rst_list = []
        if self.api.get_tags(full_name=full_name) is not None:
            for branch in self.api.get_tags(full_name=full_name):
                rst_list.append(branch["name"])
        return rst_list

    def get_branches_or_tags(self, type, full_name):
        if type == "branches":
            return self.get_branches(full_name)
        elif type == "tags":
            return self.get_tags(full_name)
        else:
            return []

    def create_hook(self, host, full_name, endpoint='console/webhooks'):
        access_token, _ = self._get_access_token()
        return self.api.create_hook(host, endpoint, full_name)

    def get_clone_user_password(self):
        access_token, _ = self._get_access_token()
        return self.oauth_user.oauth_user_name, self.oauth_user.access_token

    def get_clone_url(self, url):
        name, password = self.get_clone_user_password()
        urls = url.split("//")
        return urls[0] + '//' + name + ':' + password + '@' + urls[-1]
