# -*- coding: utf8 -*-

from rest_framework.response import Response

from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceRule, ServiceRuleHistory, TenantServiceInfo, Tenants, ServiceEvent
from api.views.base import APIView
from www.tenantservice.baseservice import TenantUsedResource
import logging
import time
import json
from www.service_http import RegionServiceApi

logger = logging.getLogger("default")

tenantUsedResource = TenantUsedResource()

class RulesController(APIView):
    """规则查询模块"""
    allowed_methods = ('GET',)
    
    def get(self, request, service_region, *args, **kwargs):
        """
        获取当前数据中心的自动伸缩规则
        ---
        parameters:
            - name: service_region
              description: 服务所在数据中心
              required: true
              type: string
              paramType: path

        """
        if service_region is None:
            logger.error("openapi.rules", "规则所在数据中心不能为空!")
            return Response(status=405, data={"success": False, "msg": u"规则所在数据中心不能为空"})
        try:
            rules = ServiceRule.objects.filter(service_region=service_region).all()
            rejson = []
            for rule in rules:
                tmp = {}
                tmp["item"] = rule.item
                tmp["minvalue"] = rule.minvalue
                tmp["maxvalue"] = rule.maxvalue
                tmp["status"] = rule.status
                tmp["region"] = rule.service_region
                tmp["count"] = rule.count
                tmp["tenant_name"] = rule.tenant_name
                tmp["service_alias"] = rule.service_alias
                tmp["rule_id"] = rule.ID
                tmp["tenant_id"] = rule.tenant_id
                tmp["service_id"] = rule.service_id
                tmp["node_number"] = rule.node_number
                tmp["port"] = rule.port
                tmp["port_type"] = rule.port_type
                rejson.append(tmp)
            return Response(status=200, data={"success": True, "data": rejson})
        except Exception, e:
            logger.error(e)
            return Response(status=406, data={"success": False, "msg": u"发生错误！"})


class ServiceInfo(APIView):
    """规则查询模块"""
    allowed_methods = ('GET',)
    
    def get(self, request, service_id, *args, **kwargs):
        """
        获取service节点信息
        ---
        parameters:
            - name: service_id
              description: 服务id
              required: true
              type: string
              paramType: path

        """
        try:
            rejson = {}
            service = TenantServiceInfo.objects.get(service_id=service_id)
            
            rejson["min_node"] = service.min_node
            
            return Response(status=200, data={"success": True, "data": rejson})
        except Exception, e:
            logger.error(e)
            return Response(status=406, data={"success": False, "msg": u"发生错误！"})
