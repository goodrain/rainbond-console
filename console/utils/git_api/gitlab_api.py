# -*- coding: utf8 -*-
from gitlab import Gitlab


class GitLabApiV4(object):
    def __init__(self, host, access_token):
        self.access_token = access_token
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

    def get_git_clone_path(self, oauth_user, git_url):
        urls = git_url.split("//")
        return urls[0] + '//' + "oauth2" + ':' + self.access_token + '@' + urls[-1]
