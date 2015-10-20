# -*- coding: utf8 -*-
from rest_framework.response import Response
from api.views.base import APIView
from www.models import TenantServiceInfo, ServiceInfo, TenantServiceAuth, TenantServiceEnv
from www.service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService
import json

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()


class SelectedServiceView(APIView):

    '''
    对单个服务的动作
    '''
    allowed_methods = ('PUT',)

    def get(self, request, serviceId, format=None):
        """
        查看服务属性
        """
        try:
            TenantServiceInfo.objects.get(service_id=serviceId)
            return Response({"ok": True}, status=200)
        except TenantServiceInfo.DoesNotExist, e:
            return Response({"ok": False, "reason": e.__str__()}, status=404)

    def put(self, request, serviceId, format=None):
        """
        更新服务属性
        ---
        parameters:
            - name: attribute_list
              description: 属性列表
              required: true
              type: string
              paramType: body
        """
        try:
            data = request.data
            TenantServiceInfo.objects.filter(service_id=serviceId).update(**data)
            service = TenantServiceInfo.objects.get(service_id=serviceId)
            regionClient.update_service(service.service_region, serviceId, data)
            return Response({"ok": True}, status=201)
        except TenantServiceInfo.DoesNotExist, e:
            logger.error(e)
            return Response({"ok": False, "reason": e.__str__()}, status=404)


class ServiceEnvVarView(APIView):

    def post(self, request, format=None):
        """
        同步环境变量到区域中心
        ---
        parameters:
            - name: service_type
              description: 服务类型
              required: true
              type: string
              paramType: form
        """
        service_type = request.data.get('service_type', "")
        try:
            baseService = BaseTenantService()
            serviceInfo = ServiceInfo.objects.get(service_type=service_type)
            tsList = TenantServiceInfo.objects.filter(service_key=serviceInfo.service_key, ID__gte=4120)
            logger.debug(service_type + " rsync size =" + str(len(tsList)))
            for service in tsList:
                env = {}
                env[service.service_key.upper() + "_HOST"] = "127.0.0.1"
                env[service.service_key.upper() + "_PORT"] = service.service_port

                baseService.saveServiceEnvVar(
                    service.tenant_id, service.service_id, u"连接地址", service.service_key.upper() + "_HOST", "127.0.0.1", False)
                baseService.saveServiceEnvVar(
                    service.tenant_id, service.service_id, u"端口", service.service_key.upper() + "_PORT", service.service_port, False)
                if serviceInfo.is_init_accout:
                    password = TenantServiceAuth.objects.get(service_id=service.service_id).password
                    baseService.saveServiceEnvVar(
                        service.tenant_id, service.service_id, u"用户名", service.service_key.upper() + "_USER", "admin", True)
                    baseService.saveServiceEnvVar(
                        service.tenant_id, service.service_id, u"密码", service.service_key.upper() + "_PASSWORD", password, True)
                    env[service.service_key.upper() + "_USER"] = "admin"
                    env[service.service_key.upper() + "_PASSWORD"] = password
                task = {}
                task["tenant_id"] = service.tenant_id
                task["attr"] = env
                regionClient.createServiceEnv(service.service_region, service.service_id, json.dumps(task))
        except Exception as e:
            logger.exception(e)
        return Response({"ok": True}, status=200)


class GitCheckCodeView(APIView):
    
    @never_cache
    def post(self, request, format=None):
        result = {}
        try:
            service_id = request.data.get('service_id', "")
            dependency = request.data.get("condition", "")
            logger.debug(service_id + "=" + dependency)
            if service_id != "" and dependency != "":
                dps = json.loads(dependency)
                language = dps["language"]
                if language is not None and language != "" and language != "no":
                    try:
                        tse = TenantServiceEnv.objects.get(service_id=service_id)
                        tse.language = language
                        tse.check_dependency = dependency
                        tse.save()
                    except Exception:
                        tse = TenantServiceEnv(service_id=service_id, language=language, check_dependency=dependency)
                        tse.save()
                    service = TenantServiceInfo.objects.get(service_id=service_id)
                    if language != "false":
                        if language.find("Java") > -1:
                            service.min_memory = 256
                            data = {}
                            data["language"] = "java"
                            regionClient.changeMemory(service.service_region, service_id, json.dumps(data))
                        service.language = language
                        service.save()
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return HttpResponse(json.dumps(result))
