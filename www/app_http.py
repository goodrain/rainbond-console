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

    def getRemoteServices(self, limit=10, key=None):
        url = self.url + "/api/v0/services/published"
        if key is not None:
            url += "?key={0}&limit={1}".format(key, limit)
        res, body = self._get(url, self.default_headers)
        return res, body

    def post_statics_tenant(self, tenant_id, statics_id):
        try:
            url = self.url + "/api/v0/services/statics/{}/{}/".format(tenant_id, statics_id)
            res, body = self._post(url, self.default_headers)
            return res, body
        except Exception:
            pass
