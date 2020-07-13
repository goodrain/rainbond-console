# -*- coding: utf8 -*-
import logging

from gitlab import Gitlab

from console.utils.oauth.base.exception import (NoAccessKeyErr, NoOAuthServiceErr)
from console.utils.oauth.base.git_oauth import GitOAuth2Interface
from console.utils.oauth.base.oauth import OAuth2User
from console.utils.urlutil import set_get_url

logger = logging.getLogger("default")


class GitlabApiV4MiXin(object):
    def set_api(self, host, access_token):
        self.api = Gitlab(host, oauth_token=access_token)


class GitlabApiV4(GitlabApiV4MiXin, GitOAuth2Interface):
    def __init__(self):
        super(GitlabApiV4, self).set_session()
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
        return "/".join([home_url, "api/v4/user"])

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
                try:
                    self.set_api(self.oauth_service.home_url, self.oauth_user.access_token)
                    self.api.auth()
                    user = self.api.user
                    if user.name:
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

        params = {"refresh_token": self.refresh_token, "grant_type": "refresh_token", "scope": "api"}
        rst = self._session.request(method='POST', url=self.oauth_service.access_token_url, headers=headers, params=params)
        data = rst.json()
        if rst.status_code == 200:
            self.oauth_user.refresh_token = data.get("refresh_token")
            self.oauth_user.access_token = data.get("access_token")
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.set_api(self.oauth_service.home_url, self.oauth_user.access_token)
            self.oauth_user = self.oauth_user.save()

    def get_user_info(self, code=None):
        access_token, refresh_token = self._get_access_token(code=code)
        self.api.auth()
        user = self.api.user
        return OAuth2User(user.name, user.id, user.email), access_token, refresh_token

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
        if per_page is None:
            per_page = 10
        for repo in self.api.projects.list(page=page, per_page=per_page, order_by="updated_at"):
            if hasattr(repo, "default_branch"):
                default_branch = repo.default_branch
            else:
                default_branch = "master"
            repo_list.append({
                "project_id": repo.id,
                "project_full_name": repo.path_with_namespace,
                "project_name": repo.name,
                "project_description": repo.description,
                "project_url": repo.http_url_to_repo,
                "project_default_branch": default_branch,
                "project_ssl_url": repo.ssh_url_to_repo,
                "updated_at": repo.last_activity_at,
                "created_at": repo.created_at
            })
        total = len(repo_list)
        meta = self.api.projects.list(as_list=False)
        if meta and meta.total:
            total = meta.total
        return repo_list, total

    def search_repos(self, full_name, *args, **kwargs):
        access_token, _ = self._get_access_token()
        page = int(kwargs.get("page", 1))
        per_page = kwargs.get("per_page", 10)
        repo_list = []
        name = full_name.split("/")[-1]
        for repo in self.api.projects.list(search=name, page=page, per_page=per_page, order_by="updated_at"):
            repo_list.append({
                "project_id": repo.id,
                "project_full_name": repo.path_with_namespace,
                "project_name": repo.name,
                "project_description": repo.description,
                "project_url": repo.http_url_to_repo,
                "project_default_branch": repo.default_branch,
                "project_ssl_url": repo.ssh_url_to_repo,
                "updated_at": repo.last_activity_at,
                "created_at": repo.created_at
            })
        total = len(repo_list)
        meta = self.api.projects.list(search=name, as_list=False)
        if meta and meta.total:
            total = meta.total
        return repo_list, total

    def get_repo_detail(self, full_name, *args, **kwargs):
        access_token, _ = self._get_access_token()
        repo_list = []
        name = full_name.split("/")[-1]
        for repo in self.api.projects.list(search=name, page=1):
            if repo.path_with_namespace == full_name:
                repo_list.append({
                    "project_id": repo.id,
                    "project_full_name": repo.path_with_namespace,
                    "project_name": repo.name,
                    "project_description": repo.description,
                    "project_url": repo.http_url_to_repo,
                    "project_default_branch": repo.default_branch,
                    "project_ssl_url": repo.ssh_url_to_repo,
                    "updated_at": repo.last_activity_at,
                    "created_at": repo.created_at
                })
        return repo_list

    def get_branches(self, full_name):
        access_token, _ = self._get_access_token()
        search_item = full_name.split("/")
        name = search_item[-1]
        repos = self.api.projects.list(search=name)
        rst_list = []
        for repo in repos:
            if repo.path_with_namespace == full_name:
                for branch in repo.branches.list():
                    rst_list.append(branch.name)
        return rst_list

    def get_tags(self, full_name):
        access_token, _ = self._get_access_token()
        name = full_name.split("/")[-1]
        repos = self.api.projects.list(search=name)
        rst_list = []
        for repo in repos:
            if repo.path_with_namespace == full_name:
                for branch in repo.tags.list():
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
        name = full_name.split("/")[-1]
        repo = self.api.projects.list(search=name)[0]
        url = "{host}/{endpoint}".format(host=host, endpoint=endpoint)
        return repo.hooks.create({'url': url, 'push_events': 1})

    def get_clone_user_password(self):
        access_token, _ = self._get_access_token()
        return "oauth2", self.oauth_user.access_token

    def get_clone_url(self, url):
        name, password = self.get_clone_user_password()
        urls = url.split("//")
        return urls[0] + '//' + name + ':' + password + '@' + urls[-1]
