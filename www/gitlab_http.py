# -*- coding: utf8 -*-
from django.conf import settings

from goodrain_web.base import BaseHttpClient
from goodrain_web.custom_config import custom_config

import json
import logging
import httplib2
from urllib import urlencode

logger = logging.getLogger('default')

PREFIX = "api/v3"


class GitlabApi(BaseHttpClient):
    ACCESS_LEVEL = {
        "GUEST": 10,
        "REPORTER": 20,
        "DEVELOPER": 30,
        "MASTER": 40,
        "OWNER": 50,
    }

    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive'}
        gitlab_service_info = custom_config.GITLAB_SERVICE_API
        if gitlab_service_info is not None:
            for k, v in gitlab_service_info.items():
                setattr(self, k, v)

    def _reload(self):
        gitlab_service_info = custom_config.GITLAB_SERVICE_API
        if gitlab_service_info is not None:
            for k, v in gitlab_service_info.items():
                setattr(self, k, v)

    def get_private_token(self):
        self._reload()
        private_token = ""
        body = {}
        body["login"] = self.admin_user
        body["email"] = self.admin_email
        body["password"] = self.admin_password
        url = self.url + PREFIX + "/session"
        headers = {'Content-Type': 'application/json'}
        num = 0
        while num < 2 and private_token == "":
            try:
                num = num + 1
                res, body = self._post(url, headers, json.dumps(body))
                private_token = body["private_token"]
            except Exception as e:
                logger.exception(e)
        return private_token

    def getUser(self, user_id):
        self._reload()
        git_user_id = 0
        try:
            userId = str(user_id)
            private_token = self.get_private_token()
            url = self.url + PREFIX + "/users/" + userId
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
            res, body = self._get(url, headers)
            git_user_id = body["id"]
            logger.debug(git_user_id)
        except Exception as e:
            logger.exception(e)
        return git_user_id

    def modifyUser(self, user_id, **kwargs):
        self._reload()
        try:
            private_token = self.get_private_token()
            url = self.url + PREFIX + "/users/" + str(user_id)
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
            data = kwargs
            res, body = self._put(url, headers, json.dumps(data))
            return body
        except Exception, e:
            raise e

    def createUser(self, email, password, username, name):
        self._reload()
        git_user_id = 0
        user = {}
        user["email"] = email
        user["password"] = password
        user["username"] = username
        user["name"] = name
        user["projects_limit"] = 1
        user["admin"] = False
        user["can_create_group"] = False
        user["confirm "] = False
        url = self.url + PREFIX + "/users"
        private_token = self.get_private_token()
        logger.debug(private_token)
        headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
        num = 0
        while num < 2 and git_user_id == 0:
            try:
                num = num + 1
                res, body = self._post(url, headers, json.dumps(user))
                logger.debug(body)
                git_user_id = body["id"]
                logger.debug(git_user_id)
            except Exception as e:
                logger.exception(e)
                logger.info("account.gituser",
                            "create gitlab user for {0} failed, reason: got uid 0".format(e))
        return git_user_id

    def deleteUser(self,git_user_id):
        self._reload()
        try:
            private_token = self.get_private_token()
            url = self.url + PREFIX + "/users/" + str(git_user_id)
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
            res, body = self._delete(url, headers)
            logger.debug(git_user_id)
            return body
        except Exception, e:
            logger.exception(e)

    def createProject(self, appname):
        self._reload()
        project_id = 0
        project = {}
        project["name"] = appname
        project["issues_enabled"] = True
        project["merge_requests_enabled"] = True
        project["wiki_enabled"] = True
        project["snippets_enabled"] = True
        project["public"] = False
        project["visibility_level"] = 0
        private_token = self.get_private_token()
        url = self.url + PREFIX + "/projects"
        headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
        num = 0
        while num < 2 and project_id == 0:
            try:
                num = num + 1
                res, body = self._post(url, headers, json.dumps(project))
                logger.debug(body)
                project_id = body["id"]
                logger.debug(project_id)
            except Exception as e:
                logger.exception(e)
        return project_id

    def create_gitlab_project(self, appname):
        self._reload()
        project_id = 0
        project = {}
        project["name"] = appname
        project["issues_enabled"] = True
        project["merge_requests_enabled"] = True
        project["wiki_enabled"] = True
        project["snippets_enabled"] = True
        project["public"] = False
        project["visibility_level"] = 0
        private_token = self.get_private_token()
        url = self.url + PREFIX + "/projects"
        headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
        data = {}
        try:
            res, body = self._post(url, headers, json.dumps(project))
            logger.debug("create gitlab project {0},{1}".format(res, body))
            data["project_id"] = body["id"]

            separator = "://"
            ssh_repo_url = body["ssh_url_to_repo"]
            if separator in body["ssh_url_to_repo"]:
                ssh_repo_url = body["ssh_url_to_repo"].split(separator)[1]
            data["ssh_url_to_repo"] = ssh_repo_url
            data["http_url_to_repo"] = body["http_url_to_repo"]
            return 200, "success", data
        except Exception as e:
            logger.exception(e)
            return 500, "创建失败," ,None

    def createProjectForUser(self, appname, user_id):
        self._reload()
        project_id = 0
        try:
            userId = str(user_id)
            project = {}
            project["user_id"] = userId
            project["name"] = appname
            project["issues_enabled"] = True
            project["merge_requests_enabled"] = True
            project["wiki_enabled"] = True
            project["snippets_enabled"] = True
            project["public"] = False
            project["visibility_level"] = 0
            private_token = self.get_private_token()

            url = self.url + PREFIX + "/projects/user/" + userId
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
            res, body = self._post(url, headers, json.dumps(project))
            logger.debug(body)
            project_id = body["id"]
            logger.debug(project_id)
        except Exception as e:
            logger.exception(e)
        return project_id

    def deleteProject(self, project_id):
        self._reload()
        try:
            private_token = self.get_private_token()
            logger.debug(private_token)
            projectId = str(project_id)
            url = self.url + PREFIX + "/projects/" + projectId
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
            http = httplib2.Http()
            res, body = http.request(url, 'DELETE', headers=headers)
            return body
        except Exception as e:
            logger.exception(e)
            return ""

    def listProjectMembers(self, project_id):
        self._reload()
        url = "{0}{1}/projects/{2}/members".format(self.url, PREFIX, project_id)
        headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': self.get_private_token()}
        res, body = self._get(url, headers=headers)
        return body

    def addProjectMember(self, project_id, user_id, identity):
        self._reload()
        result = False
        try:
            private_token = self.get_private_token()
            logger.debug(private_token)
            projectId = str(project_id)
            userId = str(user_id)
            project_user = {}
            # project_user["id"] = projectId
            project_user["user_id"] = userId
            project_user["access_level"] = self.ACCESS_LEVEL.get(identity.upper())
            url = self.url + PREFIX + "/projects/" + projectId + "/members"
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
            res, body = self._post(url, headers, json.dumps(project_user))
            logger.debug(body)
            result = True
        except Exception as e:
            logger.exception(e)
        return result

    def editMemberIdentity(self, project_id, user_id, identity):
        self._reload()
        level = self.ACCESS_LEVEL.get(identity.upper())
        url = "{0}{1}/projects/{2}/members/{3}".format(self.url, PREFIX, project_id, user_id)

        try:
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': self.get_private_token()}
            data = {"access_level": level}
            res, body = self._put(url, headers, json.dumps(data))
            return True
        except Exception, e:
            logger.exception("gitlab.members", e)
            return False

    def deleteProjectMember(self, project_id, user_id):
        self._reload()
        result = False
        try:
            projectId = str(project_id)
            userId = str(user_id)
            url = self.url + PREFIX + "/projects/" + projectId + "/members/" + userId
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': self.get_private_token()}
            res, body = self._delete(url, headers)
            result = True
        except Exception as e:
            logger.exception(e)
        return result

    def getProjectCommitTime(self, project_id):
        self._reload()
        result = 0
        try:
            projectId = str(project_id)
            url = self.url + PREFIX + "/projects/" + projectId + "/repository/commits"
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': self.get_private_token()}
            http = httplib2.Http()
            response, content = http.request(url, 'GET', headers=headers)
            t1 = json.loads(content)
            result = len(t1)
        except Exception as e:
            logger.exception(e)
        return result

    def getProjectBranches(self, project_id):
        self._reload()
        try:
            projectId = str(project_id)
            url = self.url + PREFIX + "/projects/" + projectId + "/repository/branches"
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': self.get_private_token()}
            response, content = self._get(url, headers=headers)
            return content
        except Exception as e:
            logger.exception(e)
        return ""

    def createWebHook(self, project_id):
        self._reload()
        result = False
        try:
            projectId = str(project_id)
            project_hook = {}
            project_hook["url"] = self.hook_url
            project_hook["push_events"] = True
            project_hook["issues_events"] = False
            project_hook["merge_requests_events"] = False
            project_hook["tag_push_events"] = False
            url = self.url + PREFIX + "/projects/" + projectId + "/hooks"
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': self.get_private_token()}
            res, body = self._post(url, headers, json.dumps(project_hook))
            logger.debug(body)
            result = True
        except Exception as e:
            logger.exception(e)
        return result

    def getPorjectByNamespaceAndPorjectName(self, namespace, project_name):
        self._reload()
        try:
            private_token = self.get_private_token()
            logger.debug(private_token)
            # %2F 表示斜杠(/)
            suffix = namespace + "/"+project_name
            suffix = urlencode({"1": suffix})[2:]
            url = self.url + PREFIX + "/projects/" + suffix
            headers = {'Content-Type': 'application/json', 'PRIVATE-TOKEN': private_token}
            http = httplib2.Http()
            res, body = http.request(url, 'GET', headers=headers)
            return res.status
        except Exception as e:
            logger.exception(e)
            return 500
