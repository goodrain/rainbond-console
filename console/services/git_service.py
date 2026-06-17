# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""
import json
import logging
from typing import Any, List, Optional, Tuple

from console.constants import AppConstants
from console.repositories.team_repo import team_gitlab_repo
from django.conf import settings
from goodrain_web.custom_config import custom_config
from www.gitlab_http import GitlabApi
from www.models.main import Tenants
from www.tenantservice.baseservice import CodeRepositoriesService
from www.utils.giturlparse import parse as git_url_parse

codeRepositoriesService = CodeRepositoriesService()
logger = logging.getLogger("default")
gitClient = GitlabApi()


class GitCodeService(object):
    def get_gitlab_repo(self, tenant: Tenants) -> Tuple[int, str, List[dict]]:
        sql_repos = team_gitlab_repo.get_team_gitlab_by_team_id(tenant.tenant_id)
        arr: List[dict] = []
        if sql_repos:
            for sqlobj in sql_repos:
                d = {}
                d["code_repos"] = sqlobj.respo_url
                d["code_user"] = sqlobj.respo_url.split(":")[1].split("/")[0]  # type: ignore[union-attr]  # NOTE: respo_url typed Optional[str] by stubs but runtime always str here
                d["code_project_name"] = sqlobj.repo_name
                d["code_id"] = sqlobj.git_project_id  # type: ignore[assignment]  # NOTE: git_project_id is int but d is untyped dict; harmless
                d["code_version"] = sqlobj.code_version
                arr.append(d)
        return 200, "success", arr

    def __get_gitlab_branchs(self, project_id: int) -> List[str]:
        if project_id > 0:
            branchlist = codeRepositoriesService.getProjectBranches(project_id)
            branchs = [e['name'] for e in branchlist]
            return branchs
        else:
            return ["master"]

    def __get_github_branchs(self, user: Any, parsed_git_url: Any) -> List[str]:
        token = user.github_token
        owner = parsed_git_url.owner
        repo = parsed_git_url.repo
        branchs: List[str] = []
        try:
            repos = codeRepositoriesService.gitHub_ReposRefs(owner, repo, token)
            reposList = json.loads(repos)
            for reposJson in reposList:
                ref = reposJson["ref"]
                branchs.append(ref.split("/")[2])
        except Exception as e:
            logger.error('client_error', e)
        return branchs

    def get_service_code_branch(self, user: Any, service: Any) -> List[str]:
        if service.service_source == AppConstants.SOURCE_CODE:
            code_type = ""
            parsed_git_url = git_url_parse(service.git_url, False)
            if service.code_from.startswith("gitlab") and service.code_from != "gitlab_manual":
                code_type = "gitlab"
            code, msg, branchs = self.get_code_branch(
                user, code_type, service.git_url, service.git_project_id, current_branch=service.code_version)
            if code != 200:
                return []
            return branchs  # type: ignore[return-value]  # NOTE: branchs is Optional[List[str]] but success path guarantees List
        return []

    def get_code_branch(self,
                        user: Any,
                        code_type: str,
                        git_url: str,
                        git_project_id: Any,
                        current_branch: str = "master") -> Tuple[int, str, Optional[List[str]]]:
        parsed_git_url = git_url_parse(git_url)
        host = parsed_git_url.host
        if host:
            if code_type == "gitlab":
                git_project_id = int(git_project_id)
                if git_project_id is None:
                    return 400, "gitlab检测需提供检测的代码ID", None
                branches = self.__get_gitlab_branchs(git_project_id)
            else:
                branches = [current_branch]
        else:
            branches = []
        return 200, "success", branches

    def is_gitlab_project_exist(self, namespace: str, tenant: Tenants, project_name: str) -> bool:
        """判断项目是否存在"""
        http_code = gitClient.getPorjectByNamespaceAndPorjectName(namespace, tenant.tenant_name + "_" + project_name)
        http_code = int(http_code)
        if http_code == 200:
            return True
        else:
            repo_name = namespace + "/" + tenant.tenant_name + "_" + project_name
            tgi = team_gitlab_repo.get_team_repo_by_code_name(tenant.tenant_id, repo_name)
            if tgi:
                return True
        return False
