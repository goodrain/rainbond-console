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
        url = self.BaseAPIURL + "buckets/domains?bucket_name={0}".format(bucket)
        res, body = self._get(url, self.default_headers)
        return res, body
    
    def addDomain(self, body):
        url = self.BaseAPIURL + "buckets/domains"
        res, body = self._put(url, self.default_headers, body)
        return res, body
    
    def deleteDomain(self, bucket, domain):
        url = self.BaseAPIURL + "/buckets/domains?bucket_name={0}&domain={1}".format(bucket, domain)
        res, body = self._delete(url, self.default_headers)
        return res, body
    
    def getOperatorsList(self):
        url = self.BaseAPIURL + "/operators"
        res, body = self._get(url, self.default_headers)
        return res, body
    
    def addOperator(self, body):
        url = self.BaseAPIURL + "/operators"
        res, body = self._put(url, self.default_headers, body)
        return res, body
    
    def deleteOperator(self, operator):
        url = self.BaseAPIURL + "/operators?operator_name={0}".format(operator)
        res, body = self._delete(url, self.default_headers)
        return res, body
    
    def disableOperator(self, operator):
        url = self.BaseAPIURL + "/operators/disable?operator_name={0}".format(operator)
        res, body = self._post(url, self.default_headers)
        return res, body
    
    def enableOperator(self, operator):
        url = self.BaseAPIURL + "/operators/enable?operator_name={0}".format(operator)
        res, body = self._post(url, self.default_headers)
        return res, body
