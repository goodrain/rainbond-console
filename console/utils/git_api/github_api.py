# -*- coding: utf8 -*-

from github import Github


class GithubApiV3(object):
    def __init__(self, access_token):
        self.access_token = access_token
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
        except Exception:
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
        for repo in [self.api.get_repo(full_name_or_id, **kwargs)]:
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

    def get_git_clone_path(self, oauth_user, git_url):
        urls = git_url.split("//")
        return urls[0] + '//' + oauth_user + ':' + self.access_token + '@' + urls[-1]
