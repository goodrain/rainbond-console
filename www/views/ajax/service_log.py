# -*- coding: utf8 -*-
from django.http import JsonResponse
import json
from www.views import AuthedView
from www.models import TenantServiceRelation, TenantServiceEnvVar
from www.tenantservice.baseservice import BaseTenantService
import logging
from www.service_http import RegionServiceApi
from www.decorator import perm_required

logger = logging.getLogger('default')
baseService = BaseTenantService()

regionClient = RegionServiceApi()


class ServiceLogMatch(AuthedView):
    
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        
        """
        增加日志对接应用设置
        """
        result = {}
        print "in service log match"
        try:
            # 处理依赖应用
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            dep_service_id = request.Post.get("dep_service_id", "")
            if dep_service_id == "":
                result["status"] = "failure"
                result["message"] = "依赖应用id不能为空"
                return JsonResponse(result)
            old = TenantServiceRelation.objects.filter(service_id=service_id, dep_service_id=dep_service_id).count()
            if old == 0:
                baseService.create_service_dependency(tenant_id, service_id, dep_service_id,
                                                      self.service.service_region)
            # 设置环境变量
            dep_service_type = request.Post.get("dep_service_type", "")
            if dep_service_type == "":
                result["status"] = "failure"
                result["message"] = "依赖应用类型不能为空"
                return JsonResponse(result)
            oldenv = TenantServiceEnvVar.objects.filter(attr_name="LOG_MATCH", service_id=service_id)
            # 已存在
            if oldenv.count() > 0:
                for e in oldenv:
                    e.attr_value = dep_service_type
                    e.save()
            else:
                attr = {
                    "tenant_id": self.service.tenant_id, "service_id": self.service.service_id, "name": "",
                    "attr_name": "LOG_MATCH", "attr_value": dep_service_type, "is_change": False, "scope": "inner"
                }
                TenantServiceEnvVar.objects.create(**attr)
                data = {"action": "add", "attrs": attr}
                regionClient.createServiceEnv(self.service.service_region, self.service.service_id, json.dumps(data))
            result["status"] = "success"
            result["message"] = "对接日志应用成功。"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = e.message
        return JsonResponse(result)
