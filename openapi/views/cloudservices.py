# -*- coding: utf8 -*-
from rest_framework.response import Response

from www.apiclient.regionapi import RegionInvokeApi
from www.models import Tenants, TenantServiceInfo, ServiceInfo, \
    TenantServiceAuth, TenantServiceEnvVar, TenantServiceRelation, \
    TenantServiceVolume, AppServiceRelation, TenantServicesPort
from www.utils import crypt
from django.conf import settings
from django.db.models import Q
import re
import json
import logging
from www.utils import sn
from www.region import RegionInfo
from www.monitorservice.monitorhook import MonitorHook
from openapi.views.base import BaseAPIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager
manager = OpenTenantServiceManager()
monitorhook = MonitorHook()
logger = logging.getLogger("default")
region_api = RegionInvokeApi()


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
            - name: user_id
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
            - name: service_node
              description: 节点个数
              required: false
              type: int
              paramType: form
            - name: dep_info
              description: 套餐依赖服务的设置(json)
              required: false
              type: string
              paramType: form
            - name: env_list
              description: 服务的环境参数
              required: false
              type: array
              paramType: form
            - name: limit
              description: 是否检查资源限制
              required: false
              type: bool
              paramType: form
        """
        logger.debug("openapi.cloudservice", request.data)
        tenant_name = request.data.get("tenant_name", None)
        if tenant_name is None:
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        # 数据中心
        region = request.data.get("region", None)
        if region is None:
            return Response(status=406, data={"success": False, "msg": u"数据中心名称为空"})
        # 根据service_key, version创建服务
        service_key = request.data.get("service_key", None)
        if service_key is None:
            return Response(status=408, data={"success": False, "msg": u"镜像key为空!"})
        # 服务描述
        version = request.data.get("version", None)
        if version is None:
            return Response(status=409, data={"success": False, "msg": u"镜像version为空!"})
        # 非必填字段
        user_id = request.data.get("user_id", "1")
        username = request.data.get("username", "system")
        service_memory = request.data.get("service_memory", "")
        service_node = request.data.get("service_node", 1)
        dep_info = request.data.get("dep_info", "[]")
        dep_info_json = json.loads(dep_info)
        dep_service_info = {"{0}-{1}".format(x.get("service_key"), x.get("app_version")): x for x in dep_info_json}

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

        # 检查对应region上的tenant是否创建
        init_region_tenant = manager.init_region_tenant(region, tenant_name, tenant.tenant_id, username)
        if not init_region_tenant:
            logger.error("openapi.cloudservice", "Tenant {0} region {1} init failed!".format(tenant_name, region))
            return Response(status=470, data={"success": False, "msg": u"init region tenant failed!"})

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
                # 计算依赖服务需要的资源
                for dep_service_tmp in list(dep_service_list):
                    tmp_key = "{0}-{1}".format(dep_service_tmp.service_key, dep_service_tmp.version)
                    dep_info = dep_service_info.get(tmp_key)
                    if dep_info is not None:
                        dep_required_memory += int(dep_info["memory"]) * int(dep_info["node"])
                    else:
                        dep_required_memory += int(dep_service_tmp.min_memory)
                # dep_required_memory = reduce(lambda x, y: x + y, [s.min_memory for s in dep_service_list])

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
        if int(service_node) > 1:
            tenant_service_info.min_node = int(service_node)
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
        dep_sids = []
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
                                                              region=region,
                                                              service_origin='cloud')
                    # 更新服务节点、内存
                    tmp_key = "{0}-{1}".format(dep_service_tmp.service_key, dep_service_tmp.version)
                    dep_info = dep_service_info.get(tmp_key)
                    if dep_info is not None:
                        depTenantService.min_node = int(dep_info["node"])
                        depTenantService.min_memory = int(dep_info["memory"])
                        depTenantService.save()
                    manager.add_service_extend(depTenantService, dep_service)
                    monitorhook.serviceMonitor(username, depTenantService, 'create_service', True)
                    tenant_service_list.append(depTenantService)
                    dep_sids.append(dep_service_id)
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
                # 添加goodrain_web_api反馈
                monitorhook.serviceMonitor(username, depTenantService, 'create_service', True,
                                           origin='goodrain_web_api')

        # create console service
        logger.debug("openapi.cloudservice", "install current service now")
        try:
            newTenantService = manager.create_service(service_id,
                                                      tenant.tenant_id,
                                                      service_name,
                                                      service,
                                                      user_id,
                                                      region=region,
                                                      service_origin='cloud')
            need_update = False
            if service_memory != "" and int(service_memory) > 128:
                newTenantService.min_memory = int(service_memory)
                need_update = True
            if int(service_node) > 1:
                newTenantService.min_node = int(service_node)
                need_update = True
            if need_update:
                newTenantService.save()
            if len(dep_service_list) > 0:
                self.saveAdapterEnv(newTenantService)
            manager.add_service_extend(newTenantService, service)
            monitorhook.serviceMonitor(username, newTenantService, 'create_service', True)
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
        # query service port
        service_port_list = TenantServicesPort.objects.filter(service_id=newTenantService.service_id,
                                                              is_outer_service=True,
                                                              protocol='http')
        if env_list is not None:
            env_var_list = TenantServiceEnvVar.objects.filter(service_id=service_id, tenant_id=tenant.tenant_id, is_change=True)
            env_var_map = {x.attr_name: x for x in list(env_var_list)}
            for env_var in env_list:
                attr_name = env_var.get("attr_name")
                attr_value = env_var.get("attr_value")
                env = env_var_map.get(attr_name, None)
                if attr_name == "SITE_URL":
                    port = RegionInfo.region_port(region)
                    domain = RegionInfo.region_domain(region)
                    if len(service_port_list) > 0:
                        port_value = service_port_list[0].container_port
                        attr_value = 'http://{}.{}.{}{}:{}'.format(port_value, service_name, tenant.tenant_name, domain, port)
                    logger.debug("openapi.cloudservice", "SITE_URL = {}".format(env.attr_value))
                elif attr_name == "TRUSTED_DOMAIN":
                    port = RegionInfo.region_port(region)
                    domain = RegionInfo.region_domain(region)
                    if len(service_port_list) > 0:
                        port_value = service_port_list[0].container_port
                        attr_value = '{}.{}.{}{}:{}'.format(port_value, service_name, tenant.tenant_name, domain, port)
                    logger.debug("openapi.cloudservice", "TRUSTED_DOMAIN = {}".format(env.attr_value))

                if env is not None:
                    env.attr_value = attr_value
                else:
                    env = TenantServiceEnvVar(
                        tenant_id=tenant.tenant_id,
                        service_id=service_id,
                        container_port=env_var.get("container_port"),
                        name=env_var.get("name"),
                        attr_name=attr_name,
                        attr_value=attr_value,
                        is_change=env_var.get("is_change"),
                        scope=env_var.get("scope"),
                    )
                env.save()
        logger.debug("openapi.cloudservice", "install service env success!")
        # create region service
        logger.debug("openapi.cloudservice", "install region service {0}!".format(region))
        try:
            manager.create_region_service(newTenantService,
                                          tenant_name,
                                          region,
                                          username, dep_sids=json.dumps(dep_sids))
            monitorhook.serviceMonitor(username, newTenantService, 'init_region_service', True)
        except Exception as e:
            logger.error("openapi.cloudservice", "create region service failed!", e)
            return Response(status=419, data={"success": False, "msg": u"创建region服务失败!"})
        logger.debug("openapi.cloudservice", "install region service {0} success!".format(region))

        # 发送goodrain_web_api反馈
        # 1、依赖信息
        tmp_info = []
        for dep_service in tenant_service_list:
            tmp_array = {"dep_id": dep_service.service_id,
                         "dep_name": dep_service.service_alias}
            tmp_info.append(tmp_array)
        tmp_data = {
            "service_region": region,
            "deps": tmp_info
        }
        monitorhook.serviceMonitor(username, newTenantService, 'create_service', True,
                                   origin='goodrain_web_api',
                                   info=json.dumps(tmp_data))

        wild_domain = ""
        if region in settings.WILD_DOMAINS.keys():
            wild_domain = settings.WILD_DOMAINS[newTenantService.service_region]
        http_port_str = ""
        if region in settings.WILD_PORTS.keys():
            http_port_str = settings.WILD_PORTS[region]
        http_port_str = ":" + http_port_str
        # 只有http服务返回url
        access_url = ""

        if len(service_port_list) > 0:
            port_value = service_port_list[0].container_port
            access_url = "http://{0}.{1}.{2}{3}{4}".format(port_value,
                                                           newTenantService.service_alias,
                                                           tenant_name,
                                                           wild_domain,
                                                           http_port_str)
        logger.debug("openapi.cloudservice", "service access url {0}".format(access_url))
        json_data = {}
        json_data["cloud_assistant"] = sn.instance.cloud_assistant
        json_data["url"] = access_url
        json_data["service"] = newTenantService.to_dict()
        json_data["dep_service"] = map(lambda x: x.to_dict(), tenant_service_list)
        # 服务env+依赖服务env
        dep_service_ids = [x.service_id for x in tenant_service_list]
        if service_id not in dep_service_ids:
            dep_service_ids.append(service_id)
        env_var_list = TenantServiceEnvVar.objects.filter(service_id__in=dep_service_ids).exclude(attr_name="GD_ADAPTER")
        env_list = []
        # 过滤掉不显示字段
        for env_var in list(env_var_list):
            if env_var.name in ["GD_ADAPTER", "GR_PROXY"]:
                continue
            env_list.append(env_var)
        json_data["env_list"] = map(lambda x: x.to_dict(), env_list)
        # 服务port+依赖服务port
        # port_list = TenantServicesPort.objects.filter(service_id__in=dep_service_ids)
        # json_data["port_list"] = port_list
        # 服务volume+依赖服务
        # TenantServiceVolume.objects.filter(service_id__in=dep_service_ids)
        # 依赖的环境变量

        return Response(status=200, data={"success": True, "service": json_data})

    def saveAdapterEnv(self, service):
        num = TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="GD_ADAPTER").count()
        if num < 1:
            attr = {"tenant_id": service.tenant_id, "service_id": service.service_id, "name": "GD_ADAPTER",
                    "attr_name": "GD_ADAPTER", "attr_value": "true", "is_change": 0, "scope": "inner", "container_port":-1}
            TenantServiceEnvVar.objects.create(**attr)
            attr.update({"env_name": "GD_ADAPTER", "env_value": "true"})
            # data = {"action": "add", "attrs": attr}
            tenant = Tenants.objects.get(tenant_id=service.tenant_id)
            region_api.add_service_env(service.service_region, tenant.tenant_name, service.service_alias, attr)

class CloudServiceDomainView(BaseAPIView):
    """域名管理模块"""
    allowed_methods = ('POST', 'GET', 'DELETE')

    def get(self, request, service_id, *args, **kwargs):
        """
        获取当前服务的域名
        ---
        parameters:
            - name: service_id
              description: 服务id
              required: true
              type: string
              paramType: path
        """
        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "service_id {0} is not exists".format(service_id))
            return Response(status=408, data={"success": False, "msg": u"服务名称不存在"})
        # 查询服务
        domain_array = manager.query_domain(service)
        return Response(status=200, data={"success": True, "data": domain_array})

    def post(self, request, service_id, *args, **kwargs):
        """
        当前服务添加域名
        ---
        parameters:
            - name: service_id
              description: 服务id
              required: true
              type: string
              paramType: path
            - name: domain_name
              description: 域名
              required: true
              type: string
              paramType: form
            - name: username
              description: 操作人名称
              required: false
              type: string
              paramType: form
        """
        domain_name = request.data.get("domain_name")
        if domain_name is None:
            logger.error("openapi.services", "域名称为空!")
            return Response(status=406, data={"success": False, "msg": u"域名称为空"})
        # 名称
        username = request.data.get("username", "system")
        # 汉字校验
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(domain_name.decode('utf-8'))
        if match:
            logger.error("openapi.services", "绑定域名有汉字!")
            return Response(status=412, data={"success": False, "msg": u"绑定域名有汉字"})

        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
            tenant = Tenants.objects.get(tenant_id=service.tenant_id)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant is not exists")
            return Response(status=408, data={"success": False, "msg": u"租户不存在,请检查租户名称"})
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "service_id {0} is not exists".format(service_id))
            return Response(status=409, data={"success": False, "msg": u"服务名称不存在"})
        # 添加domain_name
        status, success, msg = manager.domain_service(action="start",
                                                      service=service,
                                                      domain_name=domain_name,
                                                      tenant_name=tenant.tenant_name,
                                                      username=username)
        return Response(status=status, data={"success": success, "msg": msg})

    def delete(self, request, service_id, *args, **kwargs):
        """
        当前服务删除域名
        ---
        parameters:
            - name: service_id
              description: 服务id
              required: true
              type: string
              paramType: path
            - name: domain_name
              description: 域名
              required: true
              type: string
              paramType: form
            - name: username
              description: 操作人名称
              required: false
              type: string
              paramType: form
        """
        domain_name = request.data.get("domain_name")
        if domain_name is None:
            logger.error("openapi.services", "域名称为空!")
            return Response(status=406, data={"success": False, "msg": u"域名称为空"})
        # 名称
        username = request.data.get("username", "system")
        # 汉字校验
        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(domain_name.decode('utf-8'))
        if match:
            logger.error("openapi.services", "绑定域名有汉字!")
            return Response(status=412, data={"success": False, "msg": u"绑定域名有汉字"})
        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
            tenant = Tenants.objects.get(tenant_id=service.tenant_id)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant is not exists")
            return Response(status=408, data={"success": False, "msg": u"租户不存在,请检查租户名称"})
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "service {0}  is not exists".format(service_id))
            return Response(status=409, data={"success": False, "msg": u"服务名称不存在"})
        # 删除domain_name
        status, success, msg = manager.domain_service(action="close",
                                                      service=service,
                                                      domain_name=domain_name,
                                                      tenant_name=tenant.tenant_name,
                                                      username=username)
        return Response(status=status, data={"success": success, "msg": msg})

