# -*- coding: utf8 -*-
from django.http import JsonResponse
import json

from www.apiclient.regionapi import RegionInvokeApi
from www.views import AuthedView
from www.models import TenantServiceRelation, TenantServiceEnvVar
from www.tenantservice.baseservice import BaseTenantService
import logging
from www.decorator import perm_required

logger = logging.getLogger('default')
baseService = BaseTenantService()

region_api = RegionInvokeApi()

class ServiceLogMatch(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        
        """
        增加日志对接应用设置
        """
        result = {}
        
        try:
            # 处理依赖应用
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            dep_service_id = request.POST.get("dep_service_id", "")
            if dep_service_id == "":
                result["status"] = "failure"
                result["message"] = "依赖应用id不能为空"
                return JsonResponse(result)
            old = TenantServiceRelation.objects.filter(service_id=service_id, dep_service_id=dep_service_id).count()
            if old == 0:
                baseService.create_service_dependency(self.tenant, self.service, dep_service_id,
                                                      self.service.service_region)
            # 设置环境变量
            dep_service_type = request.POST.get("dep_service_type", "")
            if dep_service_type == "":
                result["status"] = "failure"
                result["message"] = "依赖应用类型不能为空"
                return JsonResponse(result)
            oldenv = TenantServiceEnvVar.objects.filter(attr_name="LOG_MATCH", service_id=service_id)
            # 已存在
            attr = {}
            if oldenv.count() > 0:
                for e in oldenv:
                    e.attr_value = dep_service_type
                    e.save()
                    attr = {
                        "tenant_id": e.tenant_id, "service_id": e.service_id, "name": "LOG_MATCH",
                        "attr_name": "LOG_MATCH", "attr_value": dep_service_type, "is_change": False, "scope": "inner"
                    }
            else:
                attr = {
                    "tenant_id": self.service.tenant_id, "service_id": self.service.service_id, "name": "LOG_MATCH",
                    "attr_name": "LOG_MATCH", "attr_value": dep_service_type, "is_change": False, "scope": "inner",
                    "container_port" : 0
                }
                TenantServiceEnvVar.objects.create(**attr)
                attr.update({"env_name": "LOG_MATCH", "env_value": dep_service_type,"enterprise_id":self.tenant.enterprise_id})
            region_api.add_service_env(self.service.service_region,
                                       self.tenantName,
                                       self.service.service_alias,
                                       attr)
            result["status"] = "success"
            result["message"] = "对接日志应用成功。"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = e.message
        return JsonResponse(result)


class ServiceLogMatchCheck(AuthedView):
    def get(self, request, *args, **kwargs):
        try:
            result = {}
            oldenv = TenantServiceEnvVar.objects.filter(attr_name="LOG_MATCH", service_id=self.service.service_id)
            if oldenv.count() > 0:
                result["status"] = "success"
                result["message"] = "已对接日志"
                return JsonResponse(result)
            else:
                result["status"] = "failure"
                result["message"] = "未对接日志"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = e.message
        return JsonResponse(result)


class ServiceLogMatchDelete(AuthedView):
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            oldenv = TenantServiceEnvVar.objects.filter(attr_name="LOG_MATCH",
                                                        service_id=self.service.service_id).delete()
            data = {"env_name": "LOG_MATCH","enterprise_id":self.tenant.enterprise_id}
            region_api.delete_service_env(self.service.service_region,
                                          self.tenantName,
                                          self.service.service_alias,
                                          data)
            return JsonResponse({"status": "success", "message": u"删除成功"})
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = e.message
        return JsonResponse(result)
