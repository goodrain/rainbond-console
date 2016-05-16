import json
from django.conf import settings

from goodrain_web.base import BaseHttpClient, httplib2

import logging

logger = logging.getLogger('default')


class AppServiceApi(BaseHttpClient):

    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json'}
        self.url = settings.APP_SERVICE_API["url"]

    def publishServiceData(self, body):
        url = self.url + "/api/v0/services/published"
        res, body = self._put(url, self.default_headers, body)
        return res, body
    
    def getServiceData(self, body):
        url = self.url + "/api/v0/services/published"
        res, body = self._post(url, self.default_headers, body)
        return res, body

    def uploadFiles(self, body, files):
        url = self.url + "/api/v0/services/logo"
        res, body = self._post(url, self.default_headers, body, files=files)
        return res, body

    def getRemoteServices(self):
        url = self.url + "/api/v0/services/published"
        res, body = self._get(url, self.default_headers)
        return res, body
