from django.conf import settings

from goodrain_web.base import BaseHttpClient

import json
import logging
import httplib2
from goodrain_web.custom_config import custom_config

logger = logging.getLogger('default')

GIT_HUB_WEB_HOOK_URL = "https://user.goodrain.com/service/githubhook/"
GIT_HUB_SECRET = "goodrain"


class GitHubApi(BaseHttpClient):

    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive'}
        self.base_url = 'https://api.github.com'
    
    def _reload(self):
        github_service_info = custom_config.GITHUB_SERVICE_API
        for k, v in github_service_info.items():
            setattr(self, k, v)
            
    def _encode_params(self, kw):
        args = []
        for k, v in kw.items():
            try:
                qv = v.encode('utf-8') if isinstance(v, unicode) else str(v)
            except:
                qv = v
            args.append('%s=%s' % (k, qv))
        return '&'.join(args)

    def authorize_url(self, state):
        self._reload()
        try:
            kw = {}
            kw["client_id"] = self.client_id
            kw["redirect_uri"] = self.redirect_uri
            kw["scope"] = "user,repo"
            kw["state"] = state
            return 'https://github.com/login/oauth/authorize?%s' % self._encode_params(kw)
        except Exception as e:
            logger.exception(e)
        return ""

    def get_access_token(self, code, state=None):
        self._reload()
        try:
            kw = {}
            kw["client_id"] = self.client_id
            kw["client_secret"] = self.client_secret
            kw["redirect_uri"] = self.redirect_uri
            kw["code"] = code
            url = 'https://github.com/login/oauth/access_token'
            http = httplib2.Http()
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            response, content = http.request(url, 'POST', headers=headers, body=json.dumps(kw))
            return content
        except Exception as e:
            logger.exception(e)
        return ""

    def getAllRepos(self, token):
        self._reload()
        try:
            url = "https://api.github.com/user/repos?access_token=" + token + "&per_page=200"
            http = httplib2.Http()
            headers = {'Content-Type': 'application/json'}
            response, content = http.request(url, 'GET', headers=headers)
            return content
        except Exception as e:
            logger.exception(e)
        return ""

    def getReposRefs(self, user, repos, token):
        self._reload()
        try:
            url = "https://api.github.com/repos/" + user + "/" + repos + "/git/refs?access_token=" + token + "&per_page=200"
            http = httplib2.Http()
            headers = {'Content-Type': 'application/json'}
            response, content = http.request(url, 'GET', headers=headers)
            return content
        except Exception as e:
            logger.exception(e)
        return ""

    def cloneReposUrl(self, user, repos, token, version):
        cmd = "git clone --branch " + version + " --depth 1 https://" + token + "@github.com/" + user + "/" + repos + ".git"
        return cmd

    def getUser(self, token):
        self._reload()
        try:
            url = "https://api.github.com/user?access_token=" + token
            http = httplib2.Http()
            headers = {'Accept': 'application/json'}
            response, content = http.request(url, 'GET', headers=headers)
            return content
        except Exception as e:
            logger.exception(e)
        return ""

    def getRepos(self, username):
        self._reload()
        try:
            url = "https://api.github.com/users/" + username + "/repos"
            http = httplib2.Http()
            headers = {'Content-Type': 'application/json'}
            response, content = http.request(url, 'GET', headers=headers)
            return content
        except Exception as e:
            logger.exception(e)
        return ""

    def getProjectCommitTime(self, user, repos, token):
        self._reload()
        result = 0
        try:
            url = "https://api.github.com/repos/" + user + "/" + repos + "/commits?access_token=" + token
            http = httplib2.Http()
            response, content = http.request(url, 'GET', headers=headers)
            t1 = json.loads(content)
            result = len(t1)
        except Exception as e:
            logger.exception(e)
        return result

    def createReposHook(self, user, repos, token):
        self._reload()
        result = False
        try:
            url = "https://api.github.com/repos/" + user + "/" + repos + "/hooks?access_token=" + token
            logger.debug(url)
            headers = {'Content-Type': 'application/json'}
            data = {}
            data["name"] = "web"
            data["active"] = True
            data["events"] = ["push"]
            d = {}
            d["url"] = GIT_HUB_WEB_HOOK_URL
            d["content_type"] = "json"
            d["secret"] = GIT_HUB_SECRET
            d["insecure_ssl"] = "0"
            data["config"] = d
            http = httplib2.Http()
            logger.debug(json.dumps(data))
            response, content = http.request(url, 'POST', headers=headers, body=json.dumps(data))
            logger.debug(content)
            result = True
        except Exception as e:
            logger.exception(e)
        return result
