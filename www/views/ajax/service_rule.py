# -*- coding: utf8 -*-
from django.http import JsonResponse

from www.views import AuthedView
from www.models import ServiceRule, TenantServicesPort
from www.decorator import perm_required

import logging

logger = logging.getLogger('default')


class ServiceRuleManage(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        """
        增加规则
        """
        result = {}
        try:
            item = request.POST.get("item", "")
            if item != "tp" and item != "rt" and item != "on":
                result["status"] = "failure"
                result["message"] = "规则项不支持"
                return JsonResponse(result)
            
            minvalue = int(request.POST.get("minvalue", 0))
            maxvalue = int(request.POST.get("maxvalue", 0))
            if minvalue >= maxvalue:
                result["status"] = "failure"
                result["message"] = "大值不能小于小值"
                return JsonResponse(result)
            node_number = request.POST.get("nodenum", 1)
            
            port = request.POST.get("port", "5000")
            ports = TenantServicesPort.objects.filter(service_id=self.service.service_id,
                                                      container_port=port, is_outer_service=True)
            if ports.count() != 1:
                result["status"] = "failure"
                result["message"] = "端口不能用于自动伸缩"
                return JsonResponse(result)
            else:
                
                rule = ServiceRule(tenant_id=self.service.tenant_id, service_id=self.service.service_id,
                                   tenant_name=self.tenant.tenant_name, service_alias=self.service.service_alias,
                                   service_region=self.service.service_region, port_type=self.service.port_type,
                                   item=item, minvalue=minvalue, maxvalue=maxvalue,
                                   status=0, count=0, node_number=node_number, port=port)
                rule.save()
                result["status"] = "success"
                result["message"] = "添加成功"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "添加失败"
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
                tmp["minvalue"] = rule.minvalue
                tmp["maxvalue"] = rule.maxvalue
                tmp["status"] = rule.status
                tmp["region"] = rule.service_region
                tmp["count"] = rule.count
                tmp["port"] = rule.port
                tmp["node_number"] = rule.node_number
                rejson[rule.ID] = tmp
            result["status"] = "success"
            result["data"] = rejson
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)


class ServiceRuleUpdate(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        
        """
        修改规则
        """
        result = {}
        try:
            item = request.POST.get("item", "")
            if item != "tp" and item != "rt" and item != "on":
                result["status"] = "failure"
                result["message"] = "规则项不支持"
                return JsonResponse(result)
            
            minvalue = int(request.POST.get("minvalue", 0))
            maxvalue = int(request.POST.get("maxvalue", 0))
            if minvalue >= maxvalue:
                result["status"] = "failure"
                result["message"] = "大值不能小于小值"
                return JsonResponse(result)
            node_number = request.POST.get("nodenum", 1)
            
            port = request.POST.get("port", "5000")
            count = TenantServicesPort.objects.filter(service_id=self.service.service_id,
                                                      container_port=port, is_outer_service=True).count()
            if count != 1:
                result["status"] = "failure"
                result["message"] = "端口不能用于自动伸缩"
                return JsonResponse(result)
            
            rule_id = int(request.POST.get("id", 0))
            rules = ServiceRule.objects.filter(tenant_id=self.service.tenant_id, service_id=self.service.service_id,
                                               ID=rule_id)
            if rules.count() != 1:
                result["status"] = "failure"
                result["message"] = "参数错误"
                return JsonResponse(result)
            rules.update(item=item, minvalue=minvalue, maxvalue=maxvalue, node_number=node_number, port=port)
            result["status"] = "success"
            result["message"] = "更新成功"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "更新失败"
        return JsonResponse(result)


class ServiceRuleUpdateStatus(AuthedView):
    @perm_required('manage_service')
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
    @perm_required('manage_service')
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
