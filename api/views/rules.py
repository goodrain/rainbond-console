# -*- coding: utf8 -*-

from rest_framework.response import Response

from www.models.main import ServiceRule, ServiceRuleHistory, TenantServiceInfo, Tenants
from api.views.base import APIView
from www.tenantservice.baseservice import TenantUsedResource
import logging
import time
import json
from www.service_http import RegionServiceApi

logger = logging.getLogger("default")

tenantUsedResource = TenantUsedResource()
regionClient = RegionServiceApi()


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


class InstanceManager(APIView):
    """操作实例数"""
    allowed_methods = ('POST',)
    
    def post(self, request, rule_id, *args, **kwargs):
        """
        操作实例数，扩展或者缩减
        ---
        parameters:
            - name: service_id
              description: 服务id
              required: true
              type: string
              paramType: form
            - name: action
              description: 触发操作类别
              required: true
              type: string
              paramType: form
            - name: number
              description: 操作数量
              required: false
              type: int
              paramType: form
        """
        if rule_id is None:
            return Response(status=405, data={"success": False, "msg": u"规则id不能为空"})
        service_id = request.data.get("service_id", None)
        node_number = int(request.data.get("node_number", 1))
        if service_id is None:
            return Response(status=405, data={"success": False, "msg": u"服务id不能为空"})
        try:
            service = TenantServiceInfo.objects.filter(service_id=service_id).get()
            tenant = Tenants.objects.filter(tenant_id=service.tenant_id).get()
            body = {}
            new_node_num = 1
            action = "减少实例"
            if service.min_node < node_number:
                # calculate resource
                diff_memory = (node_number - int(service.min_node)) * service.min_memory
                rt_type, flag = tenantUsedResource.predict_next_memory(tenant, service, diff_memory, True)
                result = {}
                if not flag:
                    if rt_type == "memory":
                        result["status"] = "over_memory"
                    else:
                        result["status"] = "over_money"
                    return Response(status=405, data={"success": False, "msg": result["status"]})
                else:
                    action = "增加实例"
            
            if node_number < 1:
                node_number = 1
            
            body["node_num"] = node_number
            body["deploy_version"] = service.deploy_version
            body["operator"] = "auto_action"
            regionClient.horizontalUpgrade(service.service_region, service.service_id, json.dumps(body))
            service.min_node = node_number
            service.save()
            ServiceRule.objects.filter(ID=rule_id).update(node_number=new_node_num)
            
            trigger_time = time.strftime('%Y-%m-%d %H:%M:%S',
                                         time.localtime(time.time()))
            message = "服务实例数量改为{0}".format(node_number)
            history = ServiceRuleHistory(rule_id=rule_id, trigger_time=trigger_time,
                                         action=action, message=message)
            history.save()
            
            rule = ServiceRule.objects.filter(ID=rule_id).get()
            rule.count = int(rule.count) + 1
            rule.node_number = node_number
            rule.save()
            return Response(status=200, data={"success": True, "msg": u"操作成功"})
        except TenantServiceInfo.DoesNotExist:
            logger.error("openapi.rules", "rule {0} is not exists".format(service_id))
            return Response(status=406, data={"success": False, "msg": u"服务不存在。"})
        except Tenants.DoesNotExist:
            logger.error("openapi.rules", "rule {0} is not exists".format(service_id))
            return Response(status=406, data={"success": False, "msg": u"租户不存在。"})
        except Exception, e:
            logger.exception(e)
            return Response(status=500, data={"success": False, "msg": u"内部错误"})


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
