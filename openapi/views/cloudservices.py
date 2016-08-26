# -*- coding: utf8 -*-
from rest_framework.response import Response

from www.models import Tenants, TenantServiceInfo, ServiceInfo, \
    TenantServiceAuth, TenantServiceEnvVar, TenantServiceRelation, \
    TenantServiceVolume
from www.utils import crypt
from django.conf import settings
import re

from openapi.views.base import BaseAPIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager
manager = OpenTenantServiceManager()

import logging
logger = logging.getLogger("default")


class CreateCloudServiceView(BaseAPIView):

    allowed_methods = ('POST',)

    def post(self, request, service_name, *args, **kwargs):
        """
        创建云市服务接口
        ---
        parameters:
            - name: service_name
              description: 服务名称
              required: true
              type: string
              paramType: path
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: form
            - name: region
              description: 数据中心
              required: true
              type: string
              paramType: form
            - name: service_key
              description: 镜像key
              required: true
              type: string
              paramType: form
            - name: version
              description: 镜像version
              required: true
              type: string
              paramType: form
            - name: uid
              description: 创建人id
              required: true
              type: int
              paramType: form
            - name: username
              description: 创建人姓名
              required: true
              type: string
              paramType: form
            - name: service_memory
              description: 服务的内存大小
              required: false
              type: int
              paramType: form
        """
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        # 数据中心
        region = request.data.get("region")
        if region is None:
            return Response(status=406, data={"success": False, "msg": u"数据中心名称为空"})
        # 根据service_key, version创建服务
        service_key = request.data.get("service_key")
        if service_key is None:
            return Response(status=408, data={"success": False, "msg": u"镜像key为空!"})
        # 服务描述
        version = request.data.get("version")
        if version is None:
            return Response(status=409, data={"success": False, "msg": u"镜像version为空!"})
        # 非必填字段
        user_id = request.data.get("user_id", "1")
        username = request.data.get("username", "system")
        service_memory = request.data.get("service_memory")

        logger.debug("openapi.cloudservice", "now create service: service_name:{0}, tenant_name:{1}, region:{2}, key:{3}, version:{4}".format(service_name, tenant_name, region, service_key, version))
        r = re.compile("^[a-z][a-z0-9-]*[a-z0-9]$")
        if not r.match(service_name):
            return Response(status=412, data={"success": False, "msg": u"服务名称不合法!"})
        # 根据租户名称获取租户信息
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.cloudservice", "Tenant {0} is not exists".format(tenant_name))
            return Response(status=413, data={"success": False, "msg": u"查询不到租户"})

        # 检查租户是否欠费
        # if tenantAccountService.isOwnedMoney(tenant, region):

        # 检查服务名称是否存在
        num = TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id,
                                               service_alias=service_name).count()
        if num > 0:
            logger.error("openapi.cloudservice", "Tenant {0} region {1} service:{2} is exists=!".format(tenant_name, region, service_name))
            return Response(status=414, data={"success": False, "msg": u"服务名称已经存在"})

        # get base service
        need_download_image = False
        try:
            service = ServiceInfo.objects.get(service_key=service_key, version=version)
        except ServiceInfo.DoesNotExist:
            logger.error("openapi.cloudservice", "service_key={0} version={1} service is not exists".format(service_key, version))
            need_download_image = True
        # 没有模版从app下载模版
        if need_download_image:
            manager.download_remote_service(service_key, version)

        # 生成随机service_id
        service_id = crypt.make_uuid(tenant.tenant_id)
        service.desc = ''
        if service_memory != "":
            cm = int(service_memory)
            if cm >= 128:
                ccpu = int(cm / 128) * 20
                service.min_cpu = ccpu
                service.min_memory = cm

        # 查询服务的依赖信息

        # 计算服务资源
        tenant_service_info = TenantServiceInfo()
        tenant_service_info.min_memory = service.min_memory
        tenant_service_info.service_region = region
        tenant_service_info.min_node = service.min_node
        diffMemory = service.min_node * service.min_memory
        rt_type, flag = manager.predict_next_memory(tenant, tenant_service_info, diffMemory, False)
        if not flag:
            if rt_type == "memory":
                logger.error("openapi.cloudservice", "Tenant {0} region {1} service:{2} memory!".format(tenant_name, region, service_name))
                return Response(status=416, data={"success": False, "msg": u"内存已经到最大值"})
            else:
                logger.error("openapi.cloudservice", "Tenant {0} region {1} service:{2} memory!".format(tenant_name, region, service_name))
                return Response(status=417, data={"success": False, "msg": u"资源已经到最大值"})

        # 创建依赖的服务
        # create console service
        try:
            newTenantService = manager.create_service(service_id,
                                                      tenant.tenant_id,
                                                      service_name,
                                                      service,
                                                      user_id,
                                                      region=region)
            manager.add_service_extend(newTenantService, service)

        except Exception as e:
            logger.error("openapi.cloudservice", "create console service failed!", e)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service_id).delete()
            return Response(status=418, data={"success": False, "msg": u"创建控制台服务失败!"})

        # create region service
        try:
            manager.create_region_service(newTenantService,
                                          tenant_name,
                                          region,
                                          username)
        except Exception as e:
            logger.error("openapi.cloudservice", "create region service failed!", e)
            return Response(status=419, data={"success": False, "msg": u"创建region服务失败!"})

        wild_domain = ""
        if hasattr(settings.WILD_DOMAINS, region):
            wild_domain = settings.WILD_DOMAINS[newTenantService.service_region]
        http_port_str = ""
        if hasattr(settings.WILD_PORTS, region):
            http_port_str = settings.WILD_PORTS[region]
        http_port_str = ":" + http_port_str
        url = "http://{0}.{1}{2}{3}".format(newTenantService.service_alias,
                                            tenant_name,
                                            wild_domain,
                                            http_port_str)
        json_data = {
            "service_id": newTenantService.service_id,
            "tenant_id": newTenantService.tenant_id,
            "service_key": newTenantService.service_key,
            "service_alias": newTenantService.service_alias,
            "url": url,
        }
        return Response(status=200, data={"success": True, "service": json_data})


