# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""
from www.db import BaseConnection
from www.gitlab_http import GitlabApi
from www.tenantservice.baseservice import CodeRepositoriesService
import json
from www.utils.giturlparse import parse as git_url_parse
import logging
from console.repositories.team_repo import team_gitlab_repo
from goodrain_web.custom_config import custom_config
from django.conf import settings
from console.constants import AppConstants

codeRepositoriesService = CodeRepositoriesService()
logger = logging.getLogger("default")
gitClient = GitlabApi()


class GitCodeService(object):
    # def get_gitlab_repo(self, tenant):
    #     tenant_id = tenant.tenant_id
    #     dsn = BaseConnection()
    #     query_sql = '''
    #                     select distinct git_url, git_project_id from tenant_service s where s.tenant_id = "{tenant_id}" and code_from="gitlab_new" and git_project_id>0
    #                 '''.format(tenant_id=tenant_id)
    #     sqlobjList = dsn.query(query_sql)
    #     arr = []
    #     if sqlobjList is not None:
    #         for sqlobj in sqlobjList:
    #             d = {}
    #             d["code_repos"] = sqlobj.git_url
    #             d["code_user"] = sqlobj.git_url.split(":")[1].split("/")[0]
    #             d["code_project_name"] = sqlobj.git_url.split(":")[1].split("/")[1].split(".")[0]
    #             d["code_id"] = sqlobj.git_project_id
    #             arr.append(d)
    #     return 200, "success", arr

    def get_gitlab_repo(self, tenant):
        sql_repos = team_gitlab_repo.get_team_gitlab_by_team_id(tenant.tenant_id)
        arr = []
        if sql_repos:
            for sqlobj in sql_repos:
                d = {}
                d["code_repos"] = sqlobj.respo_url
                d["code_user"] = sqlobj.respo_url.split(":")[1].split("/")[0]
                d["code_project_name"] = sqlobj.repo_name
                d["code_id"] = sqlobj.git_project_id
                d["code_version"] = sqlobj.code_version
                arr.append(d)
        return 200, "success", arr

    def get_github_repo(self, user):
        token = user.github_token
        if not token:
            github_auth_url = codeRepositoriesService.gitHub_authorize_url(user)
            data = {"url": github_auth_url}
            return 403, "github未授权", data
        else:
            repos = codeRepositoriesService.getgGitHubAllRepos(token)
            reposList = json.loads(repos)
            if isinstance(reposList, dict):
                data = {}
                data["status"] = "unauthorized"
                data["url"] = codeRepositoriesService.gitHub_authorize_url(user)
                return 403, "github未授权", data
            else:
                arr = []
                for reposJson in reposList:
                    d = {}
                    clone_url = reposJson["clone_url"]
                    code_id = reposJson["id"]
                    d["code_id"] = code_id
                    d["code_repos"] = clone_url
                    d["code_user"] = clone_url.split("/")[3]
                    d["code_project_name"] = clone_url.split("/")[4].split(".")[0]
                    arr.append(d)
                return 200, "success", arr

    def __get_gitlab_branchs(self, project_id):
        if project_id > 0:
            branchlist = codeRepositoriesService.getProjectBranches(project_id)
            branchs = [e['name'] for e in branchlist]
            return branchs
        else:
            return ["master"]

    def __get_github_branchs(self, user, parsed_git_url):
        token = user.github_token
        owner = parsed_git_url.owner
        repo = parsed_git_url.repo
        branchs = []
        try:
            repos = codeRepositoriesService.gitHub_ReposRefs(owner, repo, token)
            reposList = json.loads(repos)
            for reposJson in reposList:
                ref = reposJson["ref"]
                branchs.append(ref.split("/")[2])
        except Exception, e:
            logger.error('client_error', e)
        return branchs

    def get_service_code_branch(self, user, service):
        if service.service_source == AppConstants.SOURCE_CODE:
            code_type = ""
            parsed_git_url = git_url_parse(service.git_url, False)
            if service.code_from.startswith("gitlab") and service.code_from != "gitlab_manual":
                code_type = "gitlab"
            else:
                if parsed_git_url.host:
                    if parsed_git_url.host.endswith('github.com'):
                        code_type = "github"
            code, msg, branchs = self.get_code_branch(user, code_type, service.git_url, service.git_project_id,
                                                      current_branch=service.code_version)
            if code != 200:
                return []
            return branchs
        return []

    def get_code_branch(self, user, code_type, git_url, git_project_id, current_branch="master"):
        parsed_git_url = git_url_parse(git_url)
        host = parsed_git_url.host
        if host:
            if code_type == "gitlab":
                git_project_id = int(git_project_id)
                if git_project_id is None:
                    return 400, "gitlab检测需提供检测的代码ID", None
                branches = self.__get_gitlab_branchs(git_project_id)
            elif code_type == "github":
                branches = self.__get_github_branchs(user, parsed_git_url)
            else:
                branches = [current_branch]
        else:
            branches = []
        return 200, "success", branches

    def github_callback(self, user, code):
        "github 回调，更新user token"
        result = codeRepositoriesService.get_gitHub_access_token(code)
        content = json.loads(result)
        token = content["access_token"]
        user.github_token = token
        user.save()

    def is_gitlab_project_exist(self, namespace, tenant, project_name):
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

    def create_gitlab_project(self, tenant, user, project_name):

        """gitlab创建项目"""
        project_id = 0
        rt_data = {}
        import re
        r = re.compile(u'^[a-zA-Z0-9_\\-]+$')
        if not r.match(project_name.decode("utf-8")):
            return 400, u"项目名称只支持英文下划线和中划线",None
        namespace = settings.GITLAB_ADMIN_NAME
        is_project_exist = self.is_gitlab_project_exist(namespace, tenant, project_name)
        if is_project_exist:
            return 409, "项目名{0}已存在".format(tenant.tenant_name + "_" + project_name), None
        if user.git_user_id == 0:
            return 400, "用户未在gitlab上创建账号", None
        if user.git_user_id > 0:
            code, msg, data = gitClient.create_gitlab_project(tenant.tenant_name + "_" + project_name)
            if code != 200:
                return code, msg, data
            project_id = data["project_id"]

            if project_id > 0:
                gitClient.addProjectMember(project_id, user.git_user_id, 'master')
                gitClient.addProjectMember(project_id, settings.GITLAB_ADMIN_ID, 'reporter')
                # service.git_project_id = project_id
                # service.git_url = "git@code.goodrain.com:app/" + tenant.tenant_name + "_" + project_name + ".git"
                team_gitlab_info = {
                    "team_id": tenant.tenant_id,
                    "repo_name": namespace + "/" + tenant.tenant_name + "_" + project_name,
                    "respo_url": data["ssh_url_to_repo"],
                    "git_project_id": project_id,
                    "code_version": "master"
                }
                team_gitlab_repo.create_team_gitlab_info(**team_gitlab_info)
                rt_data["ssh_repo_url"] = data["ssh_url_to_repo"]
                rt_data["http_repo_url"] = data["http_url_to_repo"]
                rt_data["project_id"] = data["project_id"]
            return 200, "success", rt_data
        return 500, "内部异常", None

    def create_git_lab_user(self, user, email, password):
        if custom_config.GITLAB_SERVICE_API:
            if user.git_user_id == 0:
                if user.phone:
                    git_name = user.phone
                else:
                    git_name = user.nick_name
                git_user_id = gitClient.createUser(email, password, git_name, git_name)
                if git_user_id == 0:
                    return 500, "创建git用户失败,请联系管理员", None
                else:
                    user.git_user_id = git_user_id
                    user.email = email
                    user.set_password(password)
                    user.save()
                    bean = {"email": email, "password": password, "git_name": git_name}
                    return 200, "创建git账户成功", bean
            else:
                return 409, "您已创建git账户", None

        else:
            return 400, "系统未配置gitlab，请配置后再操作", None
