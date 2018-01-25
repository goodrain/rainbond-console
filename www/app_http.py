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

    def getGroupData(self, body):
        url = self.url + "/api/v0/services/get_group"
        res, body = self._post(url, self.default_headers, body)
        return res, body

    def uploadFiles(self, body, files):
        url = self.url + "/api/v0/services/logo"
        res, body = self._post(url, self.default_headers, body, files=files)
        return res, body

    def getRemoteServices(self, limit=10, key=None, timeout=None):
        url = self.url + "/api/v0/services/published"
        if key is not None:
            url += "?key={0}&limit={1}".format(key, limit)
        if timeout is None:
            res, body = self._get(url, self.default_headers)
        else:
            res, body = self._get(url, self.default_headers, timeout=timeout)
        return res, body

    def getRemoteGroupServices(self, limit=10, key=None, timeout=None, page=1):
        url = self.url + "/api/v0/services/get_group"
        if key is not None:
            url += "?key={0}&limit={1}&page={2}".format(key, limit, page)
        else:
            url += "?fa=1"
        if timeout is None:
            res, body = self._get(url, self.default_headers)
        else:
            res, body = self._get(url, self.default_headers, timeout=timeout)
        return res, body

    def getPublishedGroupAndService(self,limit=10, key=None, timeout=None):
        url = self.url + "/api/v0/services/get_published"
        if key is not None:
            url += "?key={0}&limit={1}".format(key, limit)
        if timeout is None:
            res, body = self._get(url, self.default_headers)
        else:
            res, body = self._get(url, self.default_headers, timeout=timeout)
        return res, body

    def post_statics_tenant(self, tenant_id, statics_id):
        try:
            url = self.url + "/api/v0/services/statics/{}/{}/".format(tenant_id, statics_id)
            res, body = self._post(url, self.default_headers)
            return res, body
        except Exception:
            pass

    def post_admin_info(self, data):
        try:
            url = self.url + "/api/v0/assistant/register"
            res, body = self._post(url, self.default_headers, data)
            return res, body
        except Exception as e:
            logger.exception("account.register", e)
            logger.error("account.register", "after register admin.send data to app failed!")
        return None, None

    def publish_service_group(self, body):
        url = self.url + "/api/v0/services/published_group"
        res, body = self._post(url, self.default_headers, body)
        return res, body

    def publish_all_service_group_data(self, enterprise_id, token, data):
        url = self.url + "/openapi/v1/market/apps/publish"
        import copy
        header = copy.deepcopy(self.default_headers)
        header.update({"X_ENTERPRISE_ID": enterprise_id, "X_ENTERPRISE_TOKEN": token})
        res, body = self._post(url, header, json.dumps(data))
        return res, body
