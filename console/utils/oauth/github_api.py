# -*- coding: utf8 -*-

import logging

from github import Github
from urllib3.exceptions import MaxRetryError, ReadTimeoutError, SSLError

from console.exception.main import ServiceHandleException
from console.utils.oauth.base.exception import (NoAccessKeyErr, NoOAuthServiceErr)
from console.utils.oauth.base.git_oauth import GitOAuth2Interface
from console.utils.oauth.base.oauth import OAuth2User
from console.utils.urlutil import set_get_url

logger = logging.getLogger("default")


class GithubApiV3MiXin(object):
    def set_api(self, access_token):
        self.api = Github(access_token, per_page=10)


class GithubApiV3(GithubApiV3MiXin, GitOAuth2Interface):
    def __init__(self):
        super(GithubApiV3, self).set_session()
        self.events = ["push"]
        self.request_params = {
            "scope": "user repo admin:repo_hook",
        }

    def get_auth_url(self, home_url=None):
        return "https://github.com/login/oauth/authorize"

    def get_access_token_url(self, home_url=None):
        return "https://github.com/login/oauth/access_token"

    def get_user_url(self, home_url=None):
        return "https://api.github.com/user"

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
                self.set_api(self.access_token)
                self.update_access_token(self.access_token, self.refresh_token)
                return self.access_token, self.refresh_token
            else:
                raise NoAccessKeyErr("can not get access key")
        else:
            if self.oauth_user:
                try:
                    self.set_api(self.oauth_user.access_token)
                    user = self.api.get_user()
                    if user.login:
                        return self.oauth_user.access_token, self.oauth_user.refresh_token
                except Exception as e:
                    logger.debug(e)
                    if self.oauth_user.refresh_token:
                        try:
                            self.refresh_access_token()
                        except Exception:
                            self.oauth_user.delete()
                            raise NoAccessKeyErr("refresh key is expired, please reauthorize")
                    elif isinstance(e, (SSLError, MaxRetryError, ReadTimeoutError)):
                        raise ServiceHandleException(msg=e.message, msg_show=u"连接github不稳定, 请刷新后重试")
                    else:
                        self.oauth_user.delete()
                        raise NoAccessKeyErr("access key is expired, please reauthorize")
        raise NoAccessKeyErr("can not get access key")

    def refresh_access_token(self):
        pass

    def get_user_info(self, code=None):
        access_token, refresh_token = self._get_access_token(code=code)
        user = self.api.get_user()
        return OAuth2User(user.login, user.id, user.email), access_token, refresh_token

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
        if not page:
            page = 1
        repo_list = []
        meta = self.api.get_user().get_repos()
        total = meta.totalCount
        for repo in meta.get_page(page=int(page) - 1):
            repo_list.append({
                "project_id": repo.id,
                "project_full_name": repo.full_name,
                "project_name": repo.name,
                "project_description": repo.description,
                "project_url": repo.clone_url,
                "project_ssh_url": repo.ssh_url,
                "project_default_branch": repo.default_branch,
                "updated_at": repo.updated_at,
                "created_at": repo.created_at
            })
        return repo_list, total

    def search_repos(self, full_name, *args, **kwargs):
        access_token, _ = self._get_access_token()
        page = int(kwargs.get("page", 1))
        repo_list = []
        total = 0
        try:
            user = full_name.split('/')[0]
            query = full_name.split('/')[1]
            meta = self.api.search_repositories(query=query + " user:" + user + " fork:true")
            total = meta.totalCount
            for repo in meta.get_page(page=int(page) - 1):
                if repo:
                    rst = {
                        "project_id": repo.id,
                        "project_full_name": repo.full_name,
                        "project_name": repo.name,
                        "project_description": repo.description,
                        "project_url": repo.clone_url,
                        "project_ssh_url": repo.ssh_url,
                        "project_default_branch": repo.default_branch,
                        "updated_at": repo.updated_at,
                        "created_at": repo.created_at
                    }
                    repo_list.append(rst)
        except Exception:
            return repo_list, total

        return repo_list, total

    def get_repo_detail(self, full_name, *args, **kwargs):
        access_token, _ = self._get_access_token()
        repo_list = []
        for repo in [self.api.get_repo(full_name, kwargs)]:
            if repo is None:
                pass
            else:
                rst = {
                    "project_id": repo.id,
                    "project_full_name": repo.full_name,
                    "project_name": repo.name,
                    "project_description": repo.description,
                    "project_url": repo.clone_url,
                    "project_ssh_url": repo.ssh_url,
                    "project_default_branch": repo.default_branch,
                    "updated_at": repo.updated_at,
                    "created_at": repo.created_at
                }
                repo_list.append(rst)
            return repo_list

    def get_branches(self, full_name):
        access_token, _ = self._get_access_token()
        rst_list = []
        repo = self.api.get_repo(full_name)
        for branch in repo.get_branches():
            rst_list.append(branch.name)
        return rst_list

    def get_tags(self, full_name):
        access_token, _ = self._get_access_token()
        rst_list = []
        repo = self.api.get_repo(full_name)
        for branch in repo.get_tags():
            rst_list.append(branch.name)
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
        repo = self.api.get_repo(full_name)
        config = {"url": "{host}/{endpoint}".format(host=host, endpoint=endpoint), "content_type": "json"}
        return repo.create_hook("web", config, self.events, active=True)

    def get_clone_user_password(self):
        access_token, _ = self._get_access_token()
        return self.oauth_user.oauth_user_name, self.oauth_user.access_token

    def get_clone_url(self, url):
        name, password = self.get_clone_user_password()
        urls = url.split("//")
        return urls[0] + '//' + name + ':' + password + '@' + urls[-1]
