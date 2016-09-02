# -*- coding: utf8 -*-
from rest_framework.response import Response

from www.models import Tenants, TenantServiceInfo, ServiceInfo, \
    TenantServiceAuth, TenantServiceEnvVar, TenantServiceRelation, \
    TenantServiceVolume, AppServiceRelation, TenantServicesPort
from www.utils import crypt
from django.conf import settings
from django.db.models import Q
import re
import logging
from www.utils import sn
from www.monitorservice.monitorhook import MonitorHook
from openapi.views.base import BaseAPIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager
manager = OpenTenantServiceManager()
monitorhook = MonitorHook()
logger = logging.getLogger("default")


class CloudServiceInstallView(BaseAPIView):

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
            - env_list: env_list
              description: 服务的环境参数
              required: false
              type: array
              paramType: form
            - limit: limit
              description: 是否检查资源限制
              required: false
              type: bool
              paramType: form
        """
        logger.debug("openapi.cloudservice", request.data)
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
        service_memory = request.data.get("service_memory", "")

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

        # 没有模版从app下载模版\根据模版查询服务依赖信息
        status, success, dep_map, msg = manager.download_service(service_key, version)
        if status == 500:
            logger.error("openapi.cloudservice", msg)
            return Response(status=status, data={"success": success, "msg": msg})
        # relation_list 从后向前安装服务
        dep_required_memory = 0
        dep_service_list = None
        if len(dep_map) > 0:
            dep_query = Q()
            for tmp_key, tmp_version in dep_map.items():
                dep_query = dep_query | (Q(service_key=tmp_key) & Q(version=tmp_version))
            dep_service_list = ServiceInfo.objects.filter(dep_query)
            if len(dep_service_list) > 0:
                dep_required_memory = reduce(lambda x, y: x + y, [s.min_memory for s in dep_service_list])

        # 生成随机service_id
        service_id = crypt.make_uuid(tenant.tenant_id)
        # 查询服务模版
        service = ServiceInfo.objects.get(service_key=service_key, version=version)
        service.desc = ''
        if service_memory != "":
            cm = int(service_memory)
            if cm >= 128:
                ccpu = int(cm / 128) * 20
                service.min_cpu = ccpu
                service.min_memory = cm
        # 计算服务资源
        tenant_service_info = TenantServiceInfo()
        tenant_service_info.min_memory = service.min_memory
        tenant_service_info.service_region = region
        tenant_service_info.min_node = service.min_node
        diffMemory = dep_required_memory + service.min_node * service.min_memory
        # 是否检查资源限制
        limit = request.data.get("limit", True)
        if limit:
            rt_type, flag = manager.predict_next_memory(tenant, tenant_service_info, diffMemory, False)
            if not flag:
                if rt_type == "memory":
                    logger.error("openapi.cloudservice", "Tenant {0} region {1} service:{2} memory!".format(tenant_name, region, service_name))
                    return Response(status=416, data={"success": False, "msg": u"内存已经到最大值"})
                else:
                    logger.error("openapi.cloudservice", "Tenant {0} region {1} service:{2} memory!".format(tenant_name, region, service_name))
                    return Response(status=417, data={"success": False, "msg": u"资源已经到最大值"})
        logger.debug("openapi.cloudservice", "now install dep service and service,memory:{0}".format(diffMemory))

        # 创建依赖的服务
        tenant_service_list = []
        if dep_service_list is not None:
            # 服务从后向前安装
            dep_service_list.reverse()
            for dep_service in dep_service_list:
                dep_service_id = crypt.make_uuid(dep_service.service_key)
                logger.debug("openapi.cloudservice", "install dep service:{0}".format(dep_service_id))
                try:
                    depTenantService = manager.create_service(dep_service_id,
                                                              tenant.tenant_id,
                                                              dep_service.service_name.lower() + "_" + service_name,
                                                              dep_service,
                                                              user_id,
                                                              region=region)
                    manager.add_service_extend(depTenantService, dep_service)
                    monitorhook.serviceMonitor(username, depTenantService, 'create_service', True)
                    tenant_service_list.append(depTenantService)
                except Exception as e:
                    logger.exception("openapi.cloudservice", e)
                    TenantServiceInfo.objects.filter(service_id=service_id).delete()
                    TenantServiceAuth.objects.filter(service_id=service_id).delete()
                    TenantServiceEnvVar.objects.filter(service_id=service_id).delete()
                    TenantServiceRelation.objects.filter(service_id=service_id).delete()
                    TenantServiceVolume.objects.filter(service_id=service_id).delete()
                    return Response(status=418, data={"success": False, "msg": u"创建控制台依赖服务失败!"})
                logger.debug("openapi.cloudservice", "install dep service:{0} over".format(dep_service_id))
                logger.debug("openapi.cloudservice", "install dep region service,region:{0}".format(region))
                try:
                    manager.create_region_service(depTenantService,
                                                  tenant_name,
                                                  region,
                                                  username)
                    monitorhook.serviceMonitor(username, depTenantService, 'init_region_service', True)
                except Exception as e:
                    logger.error("openapi.cloudservice", "create region service failed!", e)
                    return Response(status=419, data={"success": False, "msg": u"创建region服务失败!"})
                logger.debug("openapi.cloudservice", "install dep region service,region:{0} over".format(region))
                logger.debug("openapi.cloudservice", "install dep relation")
                # 依赖关系 todo 无法处理多层依赖关系,
                manager.create_service_dependency(tenant.tenant_id,
                                                  service_id,
                                                  dep_service_id,
                                                  region)
                logger.debug("openapi.cloudservice", "install dep relation over")

        # create console service
        logger.debug("openapi.cloudservice", "install current service now")
        try:
            newTenantService = manager.create_service(service_id,
                                                      tenant.tenant_id,
                                                      service_name,
                                                      service,
                                                      user_id,
                                                      region=region)
            manager.add_service_extend(newTenantService, service)
            monitorhook.serviceMonitor(username, newTenantService, 'create_service', True)
            tenant_service_list.append(newTenantService)
        except Exception as e:
            logger.error("openapi.cloudservice", "create console service failed!", e)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service_id).delete()
            return Response(status=418, data={"success": False, "msg": u"创建控制台服务失败!"})
        logger.debug("openapi.cloudservice", "install current service now success!")
        env_list = request.data.get("env_list", None)
        if env_list is not None:
            env_var_list = TenantServiceEnvVar.objects.filter(service_id=service_id, tenant_id=tenant.tenant_id, is_change=True)
            env_var_map = {x.attr_name: x for x in list(env_var_list)}
            for env_var in env_list:
                env = env_var_map.get(env_var.attr_name, None)
                env.attr_value = env_var.attr_value
                env.save()
        logger.debug("openapi.cloudservice", "install service env success!")
        # create region service
        logger.debug("openapi.cloudservice", "install region service {0}!".format(region))
        try:
            manager.create_region_service(newTenantService,
                                          tenant_name,
                                          region,
                                          username)
            monitorhook.serviceMonitor(username, newTenantService, 'init_region_service', True)
        except Exception as e:
            logger.error("openapi.cloudservice", "create region service failed!", e)
            return Response(status=419, data={"success": False, "msg": u"创建region服务失败!"})
        logger.debug("openapi.cloudservice", "install region service {0} success!".format(region))

        wild_domain = ""
        if hasattr(settings.WILD_DOMAINS, region):
            wild_domain = settings.WILD_DOMAINS[newTenantService.service_region]
        http_port_str = ""
        if hasattr(settings.WILD_PORTS, region):
            http_port_str = settings.WILD_PORTS[region]
        http_port_str = ":" + http_port_str
        access_url = "http://{0}.{1}{2}{3}".format(newTenantService.service_alias,
                                            tenant_name,
                                            wild_domain,
                                            http_port_str)
        logger.debug("openapi.cloudservice", "service access url {0}".format(access_url))
        json_data = {}
        json_data["cloud_assistant"] = sn.instance.cloud_assistant
        json_data["url"] = access_url
        json_data["service"] = newTenantService
        tenant_service_list.pop(newTenantService)
        json_data["dep_service"] = tenant_service_list
        # 服务env+依赖服务env
        # dep_service_ids = [x.service_id for x in tenant_service_list]
        # env_list = TenantServiceEnvVar.objects.filter(service_id__in=dep_service_ids)
        # json_data["env_list"] = env_list
        # 服务port+依赖服务port
        # port_list = TenantServicesPort.objects.filter(service_id__in=dep_service_ids)
        # json_data["port_list"] = port_list
        # 服务volume+依赖服务
        # TenantServiceVolume.objects.filter(service_id__in=dep_service_ids)
        return Response(status=200, data={"success": True, "service": json_data})


