# coding=utf-8
from github import Github
from gitlab import Gitlab

import requests
import urllib
import requests

class NoQuoteSession(requests.Session):
    def send(self, prep, **send_kwargs):
        table = {
            urllib.quote('{'): '{',
            urllib.quote('}'): '}',
            urllib.quote(':'): ':',
            urllib.quote(','): ',',
            urllib.quote('<'): '<',
            urllib.quote('>'): '>',
        }
        for old, new in table.items():
            prep.url = prep.url.replace(old, new)

        return super(NoQuoteSession, self).send(prep, **send_kwargs)

s = NoQuoteSession()

class Gitee(object):
    def __init__(self, url, oauth_token=None, api_version="5"):
        self._api_version = str(api_version)
        self._base_url = url
        self._url = "%s/api/v%s" % (url, api_version)
        self.oauth_token = 'bearer '+ oauth_token
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
                if not isinstance(data, (list,dict)):
                    data = None
            else:
                data = None
        except:
            data = None
        return data


    def _api_post(self, url_suffix, params=None, data=None):
        url = '/'.join([self._url, url_suffix])
        # return self.session.request(method='POST', url=url, headers=self.headers, data=data, params=params)
        try:
            rst = self.session.request(method='POST', url=url, headers=self.headers, data=data, params=params)
            if rst.status_code == 200:
                dat = rst.json()
                if data.get("error_description"):
                    dat = None
            else:
                dat = None
        except:
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


class Oauth2(object):
    def __init__(self, oauth_service, oauth_user=None, code=None):
        self._session = requests.Session()

        self.client_id = oauth_service.client_id
        self.client_secret = oauth_service.client_secret
        self.redirect_uri = oauth_service.redirect_uri
        self.access_token_url = oauth_service.access_token_url
        self.code = code
        self.oauth_user = oauth_user
        self.oauth_type = oauth_service.oauth_type
        self.oauth_user_url = oauth_service.api_url
        self.service_id = oauth_service.ID
        if self.oauth_user is None:
            self.access_token = None
            self.refresh_token = None
            self.user = None
        else:
            self.access_token = oauth_user.access_token
            self.refresh_token = oauth_user.refresh_token
            self.user = oauth_user.oauth_user_name
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def get_access_token(self):
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": self.code,
            "redirect_uri": self.redirect_uri+'?service_id='+str(self.service_id),
            "grant_type": "authorization_code"
        }
        try:
            rst = self._session.request(method='POST', url=self.access_token_url,
                                        headers=self.headers, params=params)
            print(rst.url, rst.content)
            if rst.status_code == 200:
                data = rst.json()
                self.access_token = data["access_token"]
                if data.get("error_description"):
                    data = None
            else:
                data = None
        except:
            data = None
        return data

    def refresh_access_token(self):
        if self.oauth_type == "github":
            return
        params = {
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        if self.oauth_type == "gitlab":
            params["scope"] = 'api'
        rst = self._session.request(method='POST', url=self.access_token_url,
                                    headers=self.headers, params=params)
        data = rst.json()
        if rst.status_code == 200:
            self.refresh_token = data.get("refresh_token")
            self.access_token = data.get("access_token")
            self.oauth_user.refresh_token = self.refresh_token
            self.oauth_user.access_token = self.access_token
            self.oauth_user.save()

    def get_user(self):
        self.headers["Authorization"] = "bearer " + self.access_token
        return self._session.request(method='GET', url=self.oauth_user_url, headers=self.headers)

    def check_and_refresh_access_token(self):
        rst = self.get_user()
        if rst.status_code == 401:
            self.refresh_access_token()
        else:
            pass


class GithubApiV3(object):
    def __init__(self, access_token):
        self.api = Github(access_token, per_page=10)
        self.events = ["push"]

    def get_user(self):
        user = self.api.get_user()
        rst = {
            "name": user.login,
            "email": user.email,
            "id": user.id,
        }
        return rst

    def get_repos(self, **kwargs):
        page = kwargs.get("page", 1)
        if not page:
            page = 1
        # per_page = kwargs.get("per_page", 10)
        repo_list = []
        for repo in self.api.get_user().get_repos().get_page(page=int(page)-1):
            repo_list.append(
                {
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
            )
        return repo_list

    def search_repo(self, full_name_or_id, **kwargs):
        page = int(kwargs.get("page", 1))
        repo_list = []
        try:
            repos = self.api.search_repositories(query=full_name_or_id+' in:name')
        except Exception as e:
            return repo_list
        for repo in repos:
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

        return repo_list[10*page-10:10*page]

    def get_repo(self, full_name_or_id, **kwargs):
        repo_list = []
        for repo in  [self.api.get_repo(full_name_or_id, **kwargs)]:
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

    def get_project_branches_or_tags(self, full_name_or_id, type):
        rst_list = []
        repo = self.api.get_repo(full_name_or_id)
        if type == "branches":
            for branch in repo.get_branches():
                rst_list.append(branch.name)
        elif type == "tags":
            for tag in repo.get_tags():
                rst_list.append(tag.name)
        else:
            pass
        return rst_list

    def creat_hooks(self, host, full_name_or_id, endpoint='console/webhooks'):
        repo = self.api.get_repo(full_name_or_id)
        config = {
            "url": "http://{host}/{endpoint}".format(host=host, endpoint=endpoint),
            "content_type": "json"
        }
        return repo.create_hook("web", config, self.events, active=True)


class GitLabApiV4(object):
    def __init__(self, host, access_token):
        self.api = Gitlab(host, oauth_token=access_token)
        self.events = ["push", "pull_request"]

    def get_user(self):
        self.api.auth()
        user = self.api.user
        rst = {
            "name": user.name,
            "email": user.email,
            "id": user.id,
        }
        return rst

    def get_repos(self, **kwargs):
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 10)
        repo_list = []
        if per_page is None:
            per_page = 10
        for repo in self.api.projects.list(page=page, size=per_page):
            repo_list.append(
                {
                    "project_id": repo.id,
                    "project_full_name": repo.path_with_namespace,
                    "project_name": repo.name,
                    "project_description": repo.description,
                    "project_url": repo.http_url_to_repo,
                    "project_default_branch": repo.default_branch,
                    "project_ssl_url": repo.ssh_url_to_repo,
                    "updated_at": repo.last_activity_at,
                    "created_at": repo.created_at
                }
            )
        return repo_list

    def search_repo(self, full_name_or_id, **kwargs):
        page = int(kwargs.get("page", 1))
        repo_list = []
        name = full_name_or_id.split("/")[-1]
        for repo in self.api.projects.list(search=name, page=page):
            repo_list.append(
                {
                    "project_id": repo.id,
                    "project_full_name": repo.path_with_namespace,
                    "project_name": repo.name,
                    "project_description": repo.description,
                    "project_url": repo.http_url_to_repo,
                    "project_default_branch": repo.default_branch,
                    "project_ssl_url": repo.ssh_url_to_repo,
                    "updated_at": repo.last_activity_at,
                    "created_at": repo.created_at
                }
            )
        return repo_list

    def get_repo(self, full_name_or_id, **kwargs):
        return self.search_repo(full_name_or_id)

    def get_project_branches_or_tags(self, full_name_or_id, type):
        rst_list = []
        name = full_name_or_id.split("/")[-1]
        repo = self.api.projects.list(search=name)[0]
        if type == "branches":
            for branch in repo.protectedbranches.list():
                rst_list.append(branch.name)
        elif type == "tags":
            for tag in repo.protectedtags.list():
                rst_list.append(tag.name)
        else:
            pass
        return rst_list

    def creat_hooks(self, host, full_name_or_id, endpoint=''):
        name = full_name_or_id.split("/")[-1]
        repo = self.api.projects.list(search=name)[0]
        url = "http://{host}/{endpoint}".format(host=host, endpoint=endpoint)
        return repo.hooks.create({'url': url, 'push_events': 1})


class GiteeApiV5(object):
    def __init__(self, host, access_token):
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
        repos =  self.api.search_repos(full_name=full_name, page=page)
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
            for branch in self.api.get_branches(full_name=full_name):
                rst_list.append(branch["name"])
        elif type == "tags":
            for tag in self.api.get_tags(full_name=full_name):
                rst_list.append(tag["name"])
        else:
            pass
        return rst_list

    def creat_hooks(self, host, full_name, endpoint='console/webhooks'):
        return self.api.create_hook(host, endpoint, full_name)


class GitApi(object):
    def __init__(self, oauth_service, oauth_user):
        api = {
            "github": GithubApiV3(oauth_user.access_token),
            "gitlab": GitLabApiV4(oauth_service.home_url, oauth_user.access_token),
            "gitee": GiteeApiV5(oauth_service.home_url, oauth_user.access_token),
        }
        Oauth2(oauth_service=oauth_service, oauth_user=oauth_user).check_and_refresh_access_token()
        self.api = api[oauth_service.oauth_type]
