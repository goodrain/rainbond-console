# -*- coding: utf8 -*-
import json

from django.conf import settings

from goodrain_web.base import BaseHttpClient

import logging

logger = logging.getLogger('default')


class YouPaiApi(BaseHttpClient):
    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection': 'keep-alive', 'Content-Type': 'application/json'}
        youpai_infos = settings.YOUPAI
        self.default_headers.update({"Authorization": "Bearer " + youpai_infos["ACCESS_TOKEN"]})
        self.BaseAPIURL = youpai_infos["URL"]
    
    def getUserInfo(self):
        url = self.BaseAPIURL + "accounts/profile/"
        res, body = self._get(url, self.default_headers)
        return res, body
    
    def createService(self, body):
        url = self.BaseAPIURL + "buckets"
        res, body = self._put(url, self.default_headers, body)
        return res, body
    
    def getDomainList(self, bucket):
        url = self.BaseAPIURL + "buckets/domains?bucket_name={0}&limit=50&page=1".format(bucket)
        res, body = self._get(url, self.default_headers)
        return res, body
    
    def addDomain(self, body):
        url = self.BaseAPIURL + "buckets/domains"
        res, body = self._put(url, self.default_headers, body)
        return res, body
    
    def deleteDomain(self, bucket, domain):
        url = self.BaseAPIURL + "buckets/domains?bucket_name={0}&domain={1}".format(bucket, domain)
        res, body = self._delete(url, self.default_headers)
        return res, body
    
    def checkDomain(self, domain):
        url = self.BaseAPIURL + "buckets/domain/detect?domain={0}".format(domain)
        res, body = self._get(url, self.default_headers)
        return res, body
    
    def getOperatorsList(self, bucket):
        url = self.BaseAPIURL + "buckets/operators?bucket_name={0}".format(bucket)
        res, body = self._get(url, self.default_headers)
        return res, body
    
    def addOperator(self, body):
        url = self.BaseAPIURL + "operators"
        res, body = self._put(url, self.default_headers, body)
        return res, body
    
    def deleteOperator(self, operator):
        url = self.BaseAPIURL + "operators?operator_name={0}".format(operator)
        res, body = self._delete(url, self.default_headers)
        return res, body
    
    def disableOperator(self, operator):
        url = self.BaseAPIURL + "operators/disable?operator_name={0}".format(operator)
        res, body = self._post(url, self.default_headers)
        return res, body
    
    def enableOperator(self, operator):
        url = self.BaseAPIURL + "operators/enable"
        body = {"operator_name": operator}
        res, body = self._post(url, self.default_headers, json.dumps(body))
        return res, body
    
    def addOperatorAuth(self, body):
        url = self.BaseAPIURL + "buckets/operators"
        res, body = self._put(url, self.default_headers, body)
        return res, body
    
    def deleteOperatorAuth(self, bucket, operator):
        url = self.BaseAPIURL + "buckets/operators?bucket_name={0}&operator_name={1}".format(bucket, operator)
        res, body = self._delete(url, self.default_headers)
        return res, body
    
    def openApp(self, bucket_name):
        url = self.BaseAPIURL + "buckets/visible"
        body = {"bucket_name": bucket_name, "visible": True}
        res, body = self._post(url, self.default_headers, json.dumps(body))
        return res, body
    
    def stopApp(self, bucket_name):
        url = self.BaseAPIURL + "buckets/visible"
        body = {"bucket_name": bucket_name, "visible": False}
        res, body = self._post(url, self.default_headers, json.dumps(body))
        return res, body
    
    def purge(self, bucket_name):
        url = self.BaseAPIURL + "buckets/purge"
        body = {"bucket_name": bucket_name}
        res, body = self._post(url, self.default_headers, json.dumps(body))
        return res, body
    
    def cdn_source(self, body):
        url = self.BaseAPIURL + "v2/buckets/cdn/source/"
        res, body = self._post(url, self.default_headers, body)
        return res, body
    
    def get_cdn_source(self, bucket_name):
        url = self.BaseAPIURL + "v2/buckets/cdn/source/?bucket_name={0}".format(bucket_name)
        res, body = self._get(url, self.default_headers)
        return res, body
