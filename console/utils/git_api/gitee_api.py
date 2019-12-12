# -*- coding: utf8 -*-

import requests


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

    def _api_get(self, url_suffix, params=None):
        url = '/'.join([self._url, url_suffix])
        try:
            rst = self.session.request(method='GET', url=url, headers=self.headers, params=params)
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
        url_suffix = 'user'
        return self._api_get(url_suffix)

    def get_repos(self, **kwargs):
        url_suffix = 'user/repos'
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 10)
        if not page:
            page = 1
        params = {
            "page": page,
            "per_page": per_page,
        }
        return self._api_get(url_suffix, params)

    def search_repos(self, full_name, page=1):
        url_suffix = 'search/repositories?q={full_name}&page={page}&per_page=10'.format(full_name=full_name,
                                                                                        page=page)
        return self._api_get(url_suffix)

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
        data = {
            "url": 'http://{host}/{endpoint}'.format(host=host, endpoint=endpoint),
            "push_events": True
        }
        return self._api_post(url_suffix, data=data)


class GiteeApiV5(object):
    def __init__(self, host, access_token):
        self.access_token = access_token
        self.api = Gitee(host, oauth_token=access_token)

    def get_user(self):
        user = self.api.get_user()
        rst = {
            "name": user["name"],
            "email": user["email"],
            "id": user["id"],
        }
        return rst

    def get_repos(self, **kwargs):
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 10)
        repo_list = []
        repos = self.api.get_repos(page=page, per_page=per_page)
        if repos:
            for repo in repos:
                repo_list.append(
                    {
                        "project_id": repo["id"],
                        "project_full_name": repo["full_name"],
                        "project_name": repo["name"],
                        "project_description": repo["description"],
                        "project_url": repo["html_url"],
                        "project_default_branch": repo["default_branch"],
                        "project_ssl_url": repo["ssh_url"],
                        "updated_at": repo["updated_at"],
                        "created_at": repo["created_at"]
                    }
                )
        return repo_list

    def search_repo(self, full_name, **kwargs):
        page = int(kwargs.get("page", 1))
        repo_list = []
        repos = self.api.search_repos(full_name=full_name, page=page)
        for repo in repos:
            if repo is None:
                pass
            else:
                repo_list.append(
                    {
                        "project_id": repo["id"],
                        "project_full_name": repo["full_name"],
                        "project_name": repo["name"],
                        "project_description": repo["description"],
                        "project_url": repo["html_url"],
                        "project_default_branch": repo["default_branch"],
                        "project_ssl_url": repo["ssh_url"],
                        "updated_at": repo["updated_at"],
                        "created_at": repo["created_at"]
                    }
                )
        return repo_list

    def get_repo(self, full_name):
        repo_list = []
        repos = [self.api.get_repo(full_name)]
        for repo in repos:
            if repo is None:
                pass
            else:
                repo_list.append(
                    {
                        "project_id": repo["id"],
                        "project_full_name": repo["full_name"],
                        "project_name": repo["name"],
                        "project_description": repo["description"],
                        "project_url": repo["html_url"],
                        "project_default_branch": repo["default_branch"],
                        "project_ssl_url": repo["ssh_url"],
                        "updated_at": repo["updated_at"],
                        "created_at": repo["created_at"]
                    }
                )
        return repo_list

    def get_project_branches_or_tags(self, full_name, type):
        rst_list = []
        if type == "branches":
            if self.api.get_tags(full_name=full_name) is not None:
                for branch in self.api.get_branches(full_name=full_name):
                    rst_list.append(branch["name"])
        elif type == "tags":
            if self.api.get_tags(full_name=full_name) is not None:
                for tag in self.api.get_tags(full_name=full_name):
                    rst_list.append(tag["name"])
        else:
            pass
        return rst_list

    def creat_hooks(self, host, full_name, endpoint='console/webhooks'):
        return self.api.create_hook(host, endpoint, full_name)

    def get_git_clone_path(self, oauth_user, git_url):
        urls = git_url.split("//")
        return urls[0] + '//' + oauth_user + ':' + self.access_token + '@' + urls[-1]
