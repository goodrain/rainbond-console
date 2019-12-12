# -*- coding: utf8 -*-

from console.utils.git_api.github_api import GithubApiV3
from console.utils.git_api.gitlab_api import GitLabApiV4
from console.utils.git_api.gitee_api import GiteeApiV5


class GitApi(object):
    def __init__(self, oauth_service, oauth_user):
        api = {
            "github": GithubApiV3(oauth_user.access_token),
            "gitlab": GitLabApiV4(oauth_service.home_url, oauth_user.access_token),
            "gitee": GiteeApiV5(oauth_service.home_url, oauth_user.access_token),
        }
        self.api = api.get(oauth_service.oauth_type)
