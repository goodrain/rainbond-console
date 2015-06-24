from django.conf import settings

from goodrain_web.base import BaseHttpClient

import json
import logging
import httplib2

logger = logging.getLogger('default')


class GitHubApi(object):
    def __init__(self, *args, **kwargs):
        self.default_headers = {'Connection':'keep-alive'}
        github_service_info = settings.GITHUB_SERVICE_API
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
        try:
            kw = {}
            kw["client_id"] = self.client_id
            kw["redirect_uri"] = self.redirect_uri
            kw["scope"] = "user,public_repo"
            kw["state"] = state
            return 'https://github.com/login/oauth/authorize?%s' % self._encode_params(kw)
        except Exception as e:
            logger.exception(e)
        return ""
    
    def get_access_token(self, code, state=None):
        try:
            kw = {}
            kw["client_id"] = self.client_id
            kw["client_secret"] = self.client_secret
            kw["redirect_uri"] = self.redirect_uri
            kw["code"] = code
            url = 'https://github.com/login/oauth/access_token'
            http = httplib2.Http()
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'} 
            response, content = http.request(url, 'POST' , headers=headers, body=json.dumps(kw))
            logger.debug(content)
            return content
        except Exception as e:
            logger.exception(e)
        return ""
    
    def getUser(self, token):
        try:
            url = "https://api.github.com/user?access_token=" + token
            http = httplib2.Http()
            headers = {'Content-Type': 'application/json', 'Authorization': token + 'OAUTH-TOKEN'} 
            response, content = http.request(url, 'GET', headers=headers)
            logger.debug(content)
            return content
        except Exception as e:
            logger.exception(e)
        return ""
    
    def getRepos(self, username):
        try:
            url = "https://api.github.com/users/" + username + "/repos"
            http = httplib2.Http()
            headers = {'Content-Type': 'application/json'} 
            response, content = http.request(url, 'GET', headers=headers)
            logger.debug(content)
            return content
        except Exception as e:
            logger.exception(e)
        return ""
