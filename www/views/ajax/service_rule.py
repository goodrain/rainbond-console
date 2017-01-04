# -*- coding: utf8 -*-
from django.http import JsonResponse

from www.views import AuthedView
from www.models import ServiceRule

import logging

logger = logging.getLogger('default')


class ServiceRuleManage(AuthedView):
    def post(self, request, *args, **kwargs):
        """
        增加规则
        """
        result = {}
        try:
            rule = ServiceRule(tenant_id=self.service.tenant_id, service_id=self.service.service_id)
            result["status"] = "success"
            result["rule"] = rule
        
        except Exception, e:
            logger.exception(e)
        result["status"] = "failure"
        
        return JsonResponse(result)
    
    def get(self, request, *args, **kwargs):
        
        """
        获取规则
        """
        
        result = {}
        try:
            rule = ServiceRule(tenant_id=self.service.tenant_id, service_id=self.service.service_id)
            result["status"] = "success"
            result["rule"] = rule
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)
    
    def put(self, request, *args, **kwargs):
        
        """
        修改规则
        """
        result = {}
        try:
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)
    
    def delete(self, request, *args, **kwargs):
        
        """
        删除规则
        """
        
        result = {}
        try:
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)
