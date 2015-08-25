from django.conf import settings

from goodrain_web.base import BaseHttpClient

import json
import logging

logger = logging.getLogger('default')

PREFIX = "api/v3"
GIT_LAB_WEB_HOOK_URL = "http://user.goodrain.com/service/gitlabhook/"


class GitlabApi(BaseHttpClient):
    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive'}
        gitlab_service_info = settings.GITLAB_SERVICE_API
        for k, v in gitlab_service_info.items():
            setattr(self, k, v)
        self._generic_token()

    def _generic_token(self):
        private_token = self.get_private_token()
        print private_token
        if private_token is not None:
            self.default_headers.update({"PRIVATE-TOKEN": private_token})

    def get_private_token(self):
        try:
            body = {}
            body["login"] = self.admin_user
            body["email"] = self.admin_email
            body["password"] = self.admin_password
            url = self.url + PREFIX + "/session"
            headers = self.default_headers.copy()
            headers.update({'Content-Type': 'application/json'})
            res, body = self._post(url, headers, json.dumps(body))
            private_token = body["private_token"]
            return private_token
        except Exception as e:
            logger.exception(e)
            return None

    def getUser(self, user_id):
        git_user_id = 0
        try:
            userId = str(user_id)
            url = self.url + PREFIX + "/users/" + userId
            headers = self.default_headers.copy()
            res, body = self._get(url, headers)
            git_user_id = body["id"]
            logger.debug(git_user_id)
        except Exception as e:
            logger.exception(e)
        return git_user_id

    def createUser(self, email, password, username, name):
        git_user_id = 0
        try:
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
            headers = self.default_headers.copy()
            headers.update({'Content-Type': 'application/json'})
            res, body = self._post(url, headers, json.dumps(user))
            logger.debug(body)
            git_user_id = body["id"]
            logger.debug(git_user_id)
        except Exception as e:
            logger.exception(e)
        return git_user_id

    def createProject(self, appname):
        project_id = 0
        try:
            project = {}
            project["name"] = appname
            project["issues_enabled"] = True
            project["merge_requests_enabled"] = True
            project["wiki_enabled"] = True
            project["snippets_enabled"] = True
            project["public"] = False
            project["visibility_level"] = 0
            url = self.url + PREFIX + "/projects"
            headers = self.default_headers.copy()
            headers.update({'Content-Type': 'application/json'})
            res, body = self._post(url, headers, json.dumps(project))
            logger.debug(body)
            project_id = body["id"]
            logger.debug(project_id)
        except Exception as e:
            logger.exception(e)
        return project_id

    def createProjectForUser(self, appname, user_id):
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

            url = self.url + PREFIX + "/projects/user/" + userId
            headers = self.default_headers.copy()
            headers.update({'Content-Type': 'application/json'})
            res, body = self._post(url, headers, json.dumps(project))
            logger.debug(body)
            project_id = body["id"]
            logger.debug(project_id)
        except Exception as e:
            logger.exception(e)
        return project_id

    def deleteProject(self, project_id):
        try:
            projectId = str(project_id)
            url = self.url + PREFIX + "/projects/" + projectId
            headers = self.default_headers.copy()
            res, body = self._delete(url, headers=headers)
            return body
        except Exception as e:
            logger.exception(e)
            return ""

    def addProjectMember(self, project_id, user_id, level):
        result = False
        try:
            projectId = str(project_id)
            userId = str(user_id)
            project_user = {}
            # project_user["id"] = projectId
            project_user["user_id"] = userId
            project_user["access_level"] = level
            url = self.url + PREFIX + "/projects/" + projectId + "/members"
            headers = self.default_headers.copy()
            headers.update({'Content-Type': 'application/json'})
            res, body = self._post(url, headers, json.dumps(project_user))
            logger.debug(body)
            result = True
        except Exception as e:
            logger.exception(e)
        return result

    def deleteProjectMember(self, project_id, user_id):
        result = False
        try:
            projectId = str(project_id)
            userId = str(user_id)
            url = self.url + PREFIX + "/projects/" + projectId + "/members/" + userId
            headers = self.default_headers.copy()
            headers.update({'Content-Type': 'application/json'})
            res, body = self._delete(url, headers)
            result = True
        except Exception as e:
            logger.exception(e)
        return result

    def getProjectCommitTime(self, project_id):
        result = 0
        try:
            projectId = str(project_id)
            # url = "http://192.168.8.146:10080/api/v3/projects/2/events"
            url = self.url + PREFIX + "/projects/" + projectId + "/repository/commits"
            headers = self.default_headers.copy()
            response, content = self._get(url, headers=headers)
            result = len(content)
        except Exception as e:
            logger.exception(e)
        return result

    def getProjectBranches(self, project_id):
        try:
            projectId = str(project_id)
            url = self.url + PREFIX + "/projects/" + projectId + "/repository/branches"
            headers = self.default_headers.copy()
            headers.update({'Content-Type': 'application/json'})
            response, content = self._get(url, headers=headers)
            return content
        except Exception as e:
            logger.exception(e)
        return ""

    def createWebHook(self, project_id):
        result = False
        try:
            projectId = str(project_id)
            project_hook = {}
            project_hook["url"] = GIT_LAB_WEB_HOOK_URL
            project_hook["push_events"] = True
            project_hook["issues_events"] = False
            project_hook["merge_requests_events"] = False
            project_hook["tag_push_events"] = False
            url = self.url + PREFIX + "/projects/" + projectId + "/hooks"
            headers = self.default_headers.copy()
            headers.update({'Content-Type': 'application/json'})
            res, body = self._post(url, headers, json.dumps(project_hook))
            logger.debug(body)
            result = True
        except Exception as e:
            logger.exception(e)
        return result

    def getFile(self, project_id, filename):
        try:
            projectId = str(project_id)
            url = self.url + PREFIX + "/projects/{0}/repository/files?file_path={1}&ref=master".format(projectId, filename)
            headers = self.default_headers.copy()
            print headers
            res, body = self._get(url, headers=headers)
            return body
        except Exception, e:
            raise e
