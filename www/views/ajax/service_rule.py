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
            item = request.POST.get("item", "")
            if item != "tp" and item != "rt" and item != "on":
                logger.debug("get a rule item " + item)
                result["status"] = "failure"
                result["message"] = "规则项不支持"
                return JsonResponse(result)
            operator = request.POST.get("operator", "")
            if operator != "=" and operator != ">" and operator != "<":
                result["status"] = "failure"
                result["message"] = "运算项不支持"
                return JsonResponse(result)
            value = int(request.POST.get("value", 0))
            node_max = request.POST.get("node_max", 1)
            action = request.POST.get("action", "")
            if action != "add" and action != "del":
                result["status"] = "failure"
                result["message"] = "操作项不支持"
                return JsonResponse(result)
            rule = ServiceRule(tenant_id=self.service.tenant_id, service_id=self.service.service_id,
                               tenant_name=self.tenant.tenant_name, service_alias=self.service.service_alias,
                               service_region=self.service.service_region,
                               item=item, operator=operator, value=value, action=action,
                               status=0, count=0, node_number=self.service.min_node, node_max=node_max)
            rule.save()
            result["status"] = "success"
            result["message"] = "添加成功"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = e.message
        return JsonResponse(result)
    
    def get(self, request, *args, **kwargs):
        
        """
        获取规则
        """
        
        result = {}
        try:
            rules = ServiceRule.objects.filter(tenant_id=self.service.tenant_id, service_id=self.service.service_id)
            rejson = {}
            for rule in rules:
                tmp = {}
                tmp["item"] = rule.item
                tmp["operator"] = rule.operator
                tmp["value"] = rule.value
                tmp["fortime"] = rule.fortime
                tmp["action"] = rule.action
                tmp["status"] = rule.status
                tmp["region"] = rule.service_region
                tmp["count"] = rule.count
                tmp["node_max"] = rule.node_max
                rejson[rule.ID] = tmp
            result["status"] = "success"
            result["data"] = rejson
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)


class ServiceRuleUpdate(AuthedView):
    def post(self, request, *args, **kwargs):
        
        """
        修改规则
        """
        result = {}
        try:
            item = request.POST.get("item", "")
            if item != "tp" and item != "rt" and item != "on":
                logger.debug("get a rule item " + item)
                result["status"] = "failure"
                result["message"] = "规则项不支持"
                return JsonResponse(result)
            operator = request.POST.get("operator", "")
            if operator != "=" and operator != ">" and operator != "<":
                result["status"] = "failure"
                result["message"] = "运算项不支持"
                return JsonResponse(result)
            value = int(request.POST.get("value", ""))
            
            for_time = int(request.POST.get("fortime", ""))
            
            action = request.POST.get("action", "")
            if action != "add" and action != "del":
                result["status"] = "failure"
                result["message"] = "操作项不支持"
                return JsonResponse(result)
            
            rule_id = int(request.POST.get("id", 0))
            rules = ServiceRule.objects.filter(tenant_id=self.service.tenant_id, service_id=self.service.service_id,
                                               ID=rule_id)
            if rules.count() != 1:
                result["status"] = "failure"
                result["message"] = "参数错误"
                return JsonResponse(result)
            rules.update(item=item, operator=operator, value=value, fortime=for_time, action=action)
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)


class ServiceRuleUpdateStatus(AuthedView):
    def post(self, request, *args, **kwargs):
        
        """
        启用规则
        """
        result = {}
        try:
            is_start = (request.POST.get("status", "false") == "true")
            rule_id = int(request.POST.get("id", 0))
            rules = ServiceRule.objects.filter(tenant_id=self.service.tenant_id, service_id=self.service.service_id,
                                               ID=rule_id)
            if rules.count() != 1:
                result["status"] = "failure"
                result["message"] = "参数错误"
                return JsonResponse(result)
            rules.update(status=is_start)
            result["status"] = "success"
            if is_start:
                result["message"] = "启动成功"
            else:
                result["message"] = "关闭成功"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)


class ServiceRuleDelete(AuthedView):
    def post(self, request, *args, **kwargs):
        
        """
        删除规则
        """
        
        result = {}
        try:
            rule_id = int(request.POST.get("id", 0))
            rules = ServiceRule.objects.filter(tenant_id=self.service.tenant_id, service_id=self.service.service_id,
                                               ID=rule_id)
            if rules.count() != 1:
                result["status"] = "failure"
                result["message"] = "参数错误"
                return JsonResponse(result)
            rules.delete()
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)
