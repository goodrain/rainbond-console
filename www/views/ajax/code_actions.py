# -*- coding: utf8 -*-
import datetime
import json

from django.views.decorators.cache import never_cache
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from www.views import AuthedView
from www.models import Users
from www.decorator import perm_required
from www.db import BaseConnection
from www.tenantservice.baseservice import CodeRepositoriesService

import logging
from django.template.defaultfilters import length
logger = logging.getLogger('default')

codeRepositoriesService = CodeRepositoriesService()

class CodeAction(AuthedView):    
    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.GET.get("action", "")
            if action == "gitlab":
                tenant_id = self.tenant.tenant_id
                dsn = BaseConnection()
                query_sql = '''
                    select distinct git_url, git_project_id from tenant_service s where s.tenant_id = "{tenant_id}" and code_from="gitlab_new" and git_project_id>0 
                '''.format(tenant_id=tenant_id)
                sqlobjList = dsn.query(query_sql)            
                if sqlobjList is not None:
                    arr = []
                    for sqlobj in sqlobjList:
                        d = {}
                        d["code_repos"] = sqlobj.git_url
                        d["code_user"] = sqlobj.git_url.split(":")[1].split("/")[0]
                        d["code_project_name"] = sqlobj.git_url.split(":")[1].split("/")[1].split(".")[0]
                        d["code_id"] = sqlobj.git_project_id
                        arr.append(d)
                    data["data"] = arr
                    data["status"] = "success"
            elif action == "github":
                token = self.user.github_token
                if token is not None:
                    repos = codeRepositoriesService.getgGitHubAllRepos(token)
                    reposList = json.loads(repos)
                    if isinstance(reposList, dict):
                        data["status"] = "unauthorized"
                        data["url"] = codeRepositoriesService.gitHub_authorize_url(self.user)
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
                        data["data"] = arr
                        data["status"] = "success"
                else:
                    data["status"] = "unauthorized"
                    data["url"] = codeRepositoriesService.gitHub_authorize_url(self.user)
        except Exception as e:
            logger.exception(e)
        return JsonResponse(data, status=200)
    
    @perm_required('tenant_account')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST["action"]
            if action == "gitlab":
                code_id = request.POST["code_id"]
                if code_id != "undefined":
                    branchList = codeRepositoriesService.getProjectBranches(code_id)
                    arr = []
                    if type(branchList) is str:
                        branchList = json.loads(branchList)
                    for branch in branchList:
                        d = {}
                        d["ref"] = branch["name"]
                        d["version"] = branch["name"]
                        arr.append(d)
                    data["data"] = arr
                    data["status"] = "success"
                    data["code_id"] = code_id
            elif action == "github":
                user = request.POST["user"]
                repos = request.POST["repos"]
                code_id = request.POST["code_id"]
                token = self.user.github_token
                data["code_id"] = code_id
                if token is not None:
                    repos = codeRepositoriesService.gitHub_ReposRefs(user, repos, token)
                    reposList = json.loads(repos)
                    if isinstance(reposList, dict):
                        data["status"] = "unauthorized"
                        data["url"] = codeRepositoriesService.gitHub_authorize_url(self.user)
                    else:
                        branches={}
                        for reposJson in reposList:
                            ref = reposJson["ref"]
                            branches[ref.split("/")[2]]=ref
                        keys = branches.keys()
                        keys.sort(reverse=True)
                        arr = []
                        for version in keys:
                            d = {}
                            d["version"] = version
                            d["ref"] = branches[version]
                            arr.append(d)
                        data["data"] = arr
                        data["status"] = "success"
                else:
                    data["status"] = "unauthorized"
                    data["url"] = codeRepositoriesService.gitHub_authorize_url(self.user)
        except Exception as e:
            logger.exception(e)
        return JsonResponse(data, status=200)
    

class UserGoodrainGitLabRegisterView(AuthedView):
    def post(self, request, *args, **kwargs):
        # 获取用户信息
        email = request.POST.get("email")
        password = request.POST.get("password")

        # 校验邮箱
        if not email:
            return JsonResponse(data={'ok': False, 'msg': '邮件地址不能为空'})

        count = Users.objects.filter(email=email).count()
        if count > 0:
            return JsonResponse(data={'ok': False, 'msg': '邮件地址已经存在'})

        # 检查用户密码合法
        if len(password) < 8:
            return JsonResponse(data={'ok': False, 'msg': '密码长度不合法'})

        if not self.user.check_password(password):
            return JsonResponse(data={'ok': False, 'msg': '密码错误'})

        # 创建git用户
        code_repo_svc = CodeRepositoriesService()
        if self.user.phone:
            git_name = self.user.phone
        else:
            git_name = self.user.nick_name
        code_repo_svc.createUser(self.user, email, password, git_name, git_name)

        # 将git账号记录入email字段
        self.user.email = email
        self.user.save()

        return JsonResponse(data={'ok': True})
