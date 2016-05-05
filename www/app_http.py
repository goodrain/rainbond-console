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
        res, body = self._post(url, self.default_headers, body)
        return body
    
    def getServiceData(self, body):
        url = self.url + "/api/v0/services/published"
        res, body = self._post(url, self.default_headers, body)
        return body