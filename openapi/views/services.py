# -*- coding: utf8 -*-
from rest_framework.response import Response

from www.apiclient.regionapi import RegionInvokeApi
from www.models import *
from www.service_http import RegionServiceApi
from www.utils import crypt
import re

from openapi.views.base import BaseAPIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager
manager = OpenTenantServiceManager()

import logging
logger = logging.getLogger("default")
region_api = RegionInvokeApi()

class CreateServiceView(BaseAPIView):

    allowed_methods = ('POST',)

    def post(self, request, service_name, *args, **kwargs):
        """
        服务创建接口
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
            - name: service_desc
              description: 服务描述
              required: false
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
        service_desc = request.data.get("service_desc")
        user_id = request.data.get("user_id")
        if user_id is None:
            return Response(status=410, data={"success": False, "msg": u"用户id为空!"})
        username = request.data.get("username")
        if username is None:
            return Response(status=411, data={"success": False, "msg": u"用户名为空!!"})
        service_memory = request.data.get("service_memory")
        # 检查挂载目录项
        mnts = request.data.get("mnts")
        if mnts:
            for mnt in mnts:
                # mnt必须是绝对路径
                if not mnt.startswith("/"):
                    return Response(status=420, data={"success": False, "msg": u"挂载目录必须是绝对路径!"})

        logger.debug("openapi.services", "now create service: service_name:{0}, tenant_name:{1}, region:{2}, key:{3}, version:{4}".format(service_name, tenant_name, region, service_key, version))
        r = re.compile("^[a-z][a-z0-9-]*[a-z0-9]$")
        if not r.match(service_name):
            return Response(status=412, data={"success": False, "msg": u"服务名称不合法!"})
        # 根据租户名称获取租户信息
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
            return Response(status=413, data={"success": False, "msg": u"查询不到租户"})

        # 检查租户是否欠费
        # if tenantAccountService.isOwnedMoney(tenant, region):

        # 检查服务名称是否存在
        num = TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id,
                                               service_alias=service_name).count()
        if num > 0:
            logger.error("openapi.services", "Tenant {0} region {1} service:{2} is exists=!".format(tenant_name, region, service_name))
            return Response(status=414, data={"success": False, "msg": u"服务名称已经存在"})

        # get base service
        try:
            service = ServiceInfo.objects.get(service_key=service_key, version=version)
        except ServiceInfo.DoesNotExist:
            logger.error("openapi.services", "service_key={0} version={1} service is not exists".format(service_key, version))
            return Response(status=415, data={"success": False, "msg": u"镜像不存在!"})

        # 生成随机service_id
        service_id = crypt.make_uuid(tenant.tenant_id)
        service.desc = service_desc
        if service_memory != "":
            cm = int(service_memory)
            if cm >= 64:
                ccpu = int(cm / 64) * 20
                service.min_cpu = ccpu
                service.min_memory = cm

        # 查询服务的依赖信息

        # 计算服务资源
        tenant_service_info = TenantServiceInfo()
        tenant_service_info.min_memory = service.min_memory
        tenant_service_info.service_region = region
        tenant_service_info.min_node = service.min_node
        diffMemory = service.min_node * service.min_memory
        limit = request.data.get("limit", True)
        if limit:
            rt_type, flag = manager.predict_next_memory(tenant, tenant_service_info, diffMemory, False)
            if not flag:
                if rt_type == "memory":
                    logger.error("openapi.services", "Tenant {0} region {1} service:{2} memory!".format(tenant_name, region, service_name))
                    return Response(status=416, data={"success": False, "msg": u"内存已经到最大值"})
                else:
                    logger.error("openapi.services", "Tenant {0} region {1} service:{2} memory!".format(tenant_name, region, service_name))
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
            logger.error("openapi.services", "create console service failed!", e)
            TenantServiceInfo.objects.filter(service_id=service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service_id).delete()
            return Response(status=418, data={"success": False, "msg": u"创建控制台服务失败!"})

        # mnt code
        if mnts:
            for mnt in mnts:
                host_path, volume_path = mnt.split(":")
                # 添加到持久化目录
                # manager.create_service_mnt(tenant.tenant_id,
                #                            service_id,
                #                            dest_path,
                #                            src_path,
                #                            region)
                volume_id = manager.save_mnt_volume(newTenantService, host_path, volume_path)
                if volume_id is None:
                    logger.error("openapi.services", "service volume failed!")

        # create region service
        try:
            manager.create_region_service(newTenantService,
                                          tenant_name,
                                          region,
                                          username)
        except Exception as e:
            logger.error("openapi.services", "create region service failed!", e)
            return Response(status=419, data={"success": False, "msg": u"创建region服务失败!"})

        json_data = {
            "service_id": newTenantService.service_id,
            "tenant_id": newTenantService.tenant_id,
            "service_key": newTenantService.service_key,
            "service_alias": newTenantService.service_alias
        }
        return Response(status=200, data={"success": True, "service": json_data})


class DeleteServiceView(BaseAPIView):
    allowed_methods = ('DELETE',)

    def delete(self, request, service_name, *args, **kwargs):
        """
        删除服务接口
        ---
        parameters:
            - name: service_name
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: form
            - name: username
              description: 删除服务人名称
              required: true
              type: string
              paramType: form

        """
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            logger.error("openapi.services", "租户名称为空!")
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "租户不存在!")
            return Response(status=408, data={"success": False, "msg": u"租户不存在"})
        try:
            service = TenantServiceInfo.objects.get(service_alias=service_name, tenant_id=tenant.tenant_id)
        except TenantServiceInfo.DoesNotExist:
            logger.error("openapi.services", "service_id不存在!")
            return Response(status=406, data={"success": False, "msg": u"服务不存在"})
        username = request.data.get("username", "system")
        # 删除用户服务
        status, success, msg = manager.delete_service(tenant, service, username)
        return Response(status=status, data={"success": success, "msg": msg})


class StartServiceView(BaseAPIView):
    allowed_methods = ('POST',)

    def post(self, request, service_name, *args, **kwargs):
        """
        启动服务接口
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
            - name: username
              description: 启动服务人名称
              required: true
              type: string
              paramType: form

        """
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            logger.error("openapi.services", "租户名称为空!")
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})

        username = request.data.get("username")

        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
            return Response(status=406, data={"success": False, "msg": u"租户不存在,请检查租户名称"})
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} ServiceAlias {1} is not exists".format(tenant_name, service_name))
            return Response(status=408, data={"success": False, "msg": u"服务不存在"})
        # 判断是否云市服务
        if service.service_origin == "cloud":
            # 查询并启动依赖服务
            relation_list = TenantServiceRelation.objects.filter(service_id=service.service_id)
            dep_id_list = [x.dep_service_id for x in list(relation_list)]
            dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_id_list)
            for dep_service in list(dep_service_list):
                status, success, msg = manager.start_service(tenant, dep_service, username)
                logger.debug("openapi.services", "dep service:{0} status:{1},{2},{3}".format(dep_service.service_alias, status, success, msg))

        # 启动服务
        status, success, msg = manager.start_service(tenant, service, username)
        return Response(status=status, data={"success": success, "msg": msg})


class StopServiceView(BaseAPIView):
    allowed_methods = ('POST',)

    def post(self, request, service_name, *args, **kwargs):
        """
        停止服务接口
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
            - name: username
              description: 停止服务人名称
              required: true
              type: string
              paramType: form

        """
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            logger.error("openapi.services", "租户名称为空!")
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        username = request.data.get("username", "system")

        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
            return Response(status=406, data={"success": False, "msg": u"租户不存在,请检查租户名称"})
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} ServiceAlias {1} is not exists".format(tenant_name, service_name))
            return Response(status=408, data={"success": False, "msg": u"服务名称不存在"})
        # 停止服务
        status, success, msg = manager.stop_service(service, username)
        # 判断是否云市服务
        if service.service_origin == "cloud":
            # 查询并停止依赖服务
            relation_list = TenantServiceRelation.objects.filter(service_id=service.service_id)
            dep_id_list = [x.dep_service_id for x in list(relation_list)]
            dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_id_list)
            for dep_service in list(dep_service_list):
                status, success, msg = manager.stop_service(dep_service, username)
                logger.debug("openapi.services", "dep service:{0} status:{1},{2},{3}".format(dep_service.service_alias, status, success, msg))
        return Response(status=status, data={"success": success, "msg": msg})


class StatusServiceView(BaseAPIView):
    allowed_methods = ('GET',)

    def get(self, request, service_name, *args, **kwargs):
        """
        服务状态查询接口
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
              paramType: query

        """
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            logger.error("openapi.services", "租户名称为空!")
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
            return Response(status=406, data={"success": False, "msg": u"租户不存在,请检查租户名称"})
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} ServiceAlias {1} is not exists".format(tenant_name, service_name))
            return Response(status=408, data={"success": False, "msg": u"服务不存在"})
        # 查询服务状态服务
        status, success, msg = manager.status_service(service)
        return Response(status=status, data={"success": success, "service_id":service.service_id, "msg": msg})


class RestartServiceView(BaseAPIView):
    """重启服务"""
    allowed_methods = ('POST',)

    def post(self, request, service_id, *args, **kwargs):
        """
        启动服务接口
        ---
        parameters:
            - name: service_id
              description: 服务ID
              required: true
              type: string
              paramType: path
            - name: username
              description: 启动服务人名称
              required: true
              type: string
              paramType: form

        """
        logger.debug("openapi.services", request.data)
        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            logger.error("openapi.services", "服务不存在!")
            return Response(status=405, data={"success": False, "msg": u"service_id不存在"})
        tenant_id = service.tenant_id
        try:
            tenant = Tenants.objects.get(tenant_id=tenant_id)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "租户不存在!")
            return Response(status=405, data={"success": False, "msg": u"租户不存在"})
        service_name = service.service_alias
        username = request.data.get("username", "system")
        try:
            service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} ServiceAlias {1} is not exists".format(tenant.tenant_name, service_name))
            return Response(status=408, data={"success": False, "msg": u"服务不存在"})
        # 启动服务
        limit = request.data.get("limit", True)
        # 启动依赖服务
        relation_list = TenantServiceRelation.objects.filter(service_id=service.service_id)
        if len(relation_list) > 0:
            dep_service_id_list = [x.dep_service_id for x in list(relation_list)]
            dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_service_id_list)
            dep_service_map = {x.service_id: x for x in dep_service_list}
            for relation in relation_list:
                dep_service = dep_service_map.get(relation.dep_service_id)
                manager.restart_service(tenant, dep_service, username, limit)
        status, success, msg = manager.restart_service(tenant, service, username, limit)
        return Response(status=status, data={"success": success, "msg": msg})


class UpdateServiceView(BaseAPIView):
    """更新服务"""
    allowed_methods = ('POST',)

    def post(self, request, service_id, *args, **kwargs):
        """
        更新服务接口
        ---
        parameters:
            - name: service_id
              description: 服务ID
              required: true
              type: string
              paramType: path
            - name: action
              description: 更新类型
              required: true
              type: string
              paramType: form
            - name: version
              description: 更新服务的版本
              required: true
              type: string
              paramType: form
            - name: memory
              description: 服务内存
              required: true
              type: string
              paramType: form
            - name: node
              description: 服务节点数
              required: true
              type: string
              paramType: form
            - name: limit
              description: 是否限制资源
              required: false
              type: string
              paramType: form
        """
        logger.debug("openapi.services", request.data)
        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            logger.error("openapi.services", "service_id不存在!")
            return Response(status=405, data={"success": False, "msg": u"service_id不存在"})
        tenant_id = service.tenant_id
        try:
            tenant = Tenants.objects.get(tenant_id=tenant_id)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "租户不存在!")
            return Response(status=405, data={"success": False, "msg": u"租户不存在"})

        action = request.data.get("action", None)
        limit = request.data.get("limit", True)
        username = request.data.get("username", "system")
        if action is None:
            logger.error("openapi.services", "操作类型不能为空!")
            return Response(status=405, data={"success": False, "msg": u"操作类型不能为空"})
        if action == "version":
            # 版本更新
            version = request.data.get("version", None)
            if version is None:
                logger.error("openapi.services", "更新版本不能为空!")
                return Response(status=405, data={"success": False, "msg": u"更新版本不能为空"})
            # todo update
            status, success, msg = manager.update_service_version(service)
            return Response(status=status, data={"success": success, "msg": msg})
        elif action == "extend":
            # 更新内存
            memory = request.data.get("memory", None)
            node = request.data.get("node", None)
            if memory is None:
                logger.error("openapi.services", "设置内存不能为空!")
                return Response(status=405, data={"success": False, "msg": u"设置内存不能为空"})
            if node is None:
                logger.error("openapi.services", "设置节点不能为空!")
                return Response(status=405, data={"success": False, "msg": u"设置节点不能为空"})
            # 先更改内存,在修改节点
            status, success, msg = manager.update_service_memory(tenant, service, username, memory, limit)
            if status == 200:
                status, success, msg = manager.update_service_node(tenant, service, username, node, limit)
                return Response(status=status, data={"success": success, "msg": msg})
            else:
                return Response(status=status, data={"success": success, "msg": msg})

        elif action == "memory":
            memory = request.data.get("memory", None)
            if memory is None:
                logger.error("openapi.services", "设置内存不能为空!")
                return Response(status=405, data={"success": False, "msg": u"设置内存不能为空"})
            status, success, msg = manager.update_service_memory(tenant, service, username, memory, limit)
            return Response(status=status, data={"success": success, "msg": msg})
        elif action == "node":
            node = request.data.get("node", None)
            if node is None:
                logger.error("openapi.services", "设置节点不能为空!")
                return Response(status=405, data={"success": False, "msg": u"设置节点不能为空"})
            status, success, msg = manager.update_service_node(tenant, service, username, node, limit)
            return Response(status=status, data={"success": success, "msg": msg})
        else:
            return Response(status=200, data={"success": True, "msg": "you do nothing!"})


class QueryServiceView(BaseAPIView):
    """查询服务信息"""
    allowed_methods = ('POST',)

    def post(self, request, service_id, *args, **kwargs):
        status = 200
        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
        except Exception as e:
            logger.exception("openapi.services", e)
            return Response(status=405, data={"success": False, "msg": u"服务不存在"})
        service_key = service.service_key
        version = service.version
        region = service.service_region
        # 查询服务的版本
        service_list = ServiceInfo.objects.filter(service_key=service_key, version=version).order_by("-ID")
        data = {"new_version": service.update_version}
        if len(service_list) > 0:
            new_service = list(service_list)[-1]
            data["new_version"] = new_service.update_version
        # 查询服务状态
        status_code, success, msg = manager.status_service(service)
        data["status"] = msg["status"]
        if msg["status"] == "running":
            wild_domain = ""
            if region in settings.WILD_DOMAINS.keys():
                wild_domain = settings.WILD_DOMAINS[service.service_region]
            http_port_str = ""
            if region in settings.WILD_PORTS.keys():
                http_port_str = settings.WILD_PORTS[region]
            http_port_str = ":" + http_port_str
            # 只有http服务返回url
            access_url = ""
            tenant_id = service.tenant_id
            tenant_name = ""
            try:
                tenant_info = Tenants.objects.get(tenant_id=tenant_id)
                tenant_name = tenant_info.tenant_name
            except Exception:
                logger.error("openapi.services", "tenant missing, id:{0}".format(tenant_id))

            if TenantServicesPort.objects.filter(service_id=service_id,
                                                 is_outer_service=True,
                                                 protocol='http').exists():
                access_url = "http://{0}.{1}{2}{3}".format(
                    service.service_alias,
                    tenant_name,
                    wild_domain,
                    http_port_str)
            data["access_url"] = access_url

        return Response(status=status, data=data)


class RemoveServiceView(BaseAPIView):
    allowed_methods = ('DELETE',)

    def delete(self, request, service_id, *args, **kwargs):
        """
        删除服务接口
        ---
        parameters:
            - name: service_id
              description: 服务ID
              required: true
              type: string
              paramType: path
            - name: username
              description: 删除服务人名称
              required: true
              type: string
              paramType: form

        """
        logger.debug("openapi.services", request.data)
        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            logger.error("openapi.services", "service_id不存在!")
            return Response(status=406, data={"success": False, "msg": u"服务不存在"})
        tenant_id = service.tenant_id
        try:
            tenant = Tenants.objects.get(tenant_id=tenant_id)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "租户不存在!")
            return Response(status=408, data={"success": False, "msg": u"租户不存在"})
        username = request.data.get("username", "system")
        if service.service_origin == "cloud":
            logger.debug("openapi.services", "now remove cloud service")
            # 删除依赖服务
            status, success, msg = manager.remove_service(tenant, service, username)
        else:
            status, success, msg = manager.delete_service(tenant, service, username)
        return Response(status=status, data={"success": success, "msg": msg})


class PublishedView(BaseAPIView):
    allowed_methods = ('GET',)

    def get(self, request, service_name, *args, **kwargs):
        """
        获取服务service_key和service_version接口
        ---
        parameters:
            - name: service_name
              description: 服务名称
              required: true
              type: string
              paramType: path

        """
        if service_name is None:
            logger.error("openapi.services", "service_name为空!")
            return Response(status=405, data={"success": False, "msg": u"服务名称为空"})

        try:
            result_list = []
            service_list = ServiceInfo.objects.filter(service_name=service_name)
            for service in service_list:
                result_list.append({"service_name": service.service_name, "service_key": service.service_key,
                                    "version": service.version})
            return Response(status=200, data={"success": True, "msg": result_list})
        except Exception:
            logger.error("openapi.services", "ServiceInfo {0} is exception".format(service_name))
            return Response(status=406, data={"success": False, "msg": u"系统异常"})


class UpgradeView(BaseAPIView):
    allowed_methods = ('POST',)

    def post(self, request, service_name, *args, **kwargs):
        """
        升级服务接口
        ---
        parameters:
            - name: service_name
              description: 服务名
              required: true
              type: string
              paramType: path
            - name: tenant_name
              description: 租户名
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
            - name: service_memory
              description: 服务内存大小
              required: false
              type: int
              paramType: form
            - name: service_node
              description: 服务节点数
              required: false
              type: int
              paramType: form

        """
        logger.debug("openapi.services", request.data)
        tenant_name = request.data.get("tenant_name")
        if tenant_name is None:
            logger.error("openapi.services", "租户名称为空!")
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        # 根据service_key, version创建服务
        service_key = request.data.get("service_key")
        if service_key is None:
            return Response(status=406, data={"success": False, "msg": u"镜像key为空!"})
        # 服务描述
        version = request.data.get("version")
        if version is None:
            return Response(status=408, data={"success": False, "msg": u"镜像version为空!"})
        # 服务内存大小
        service_memory = request.data.get("service_memory", 0)
        # 服务节点数
        service_node = request.data.get("service_node", 0)
        try:
            try:
                tenant = Tenants.objects.get(tenant_name=tenant_name)
            except Tenants.DoesNotExist:
                logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
                return Response(status=409, data={"success": False, "msg": u"查询不到租户"})
            
            # 根据tenant_name 查询出服务名
            try:
                tenant_service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
            except TenantServiceInfo.DoesNotExist:
                logger.error("openapi.services", "service_id不存在!")
                return Response(status=410, data={"success": False, "msg": u"服务不存在"})
            
            # 根据service_key、version到服务模板中查出image
            try:
                service = ServiceInfo.objects.get(service_key=service_key, version=version)
            except ServiceInfo.DoesNotExist:
                logger.error("openapi.services", "service_key={0} version={1} service is not exists".format(service_key, version))
                return Response(status=411, data={"success": False, "msg": u"镜像不存在!"})
        
            # 调用region 更新region中的数据
            if int(service_memory) == 0:
                service_memory = tenant_service.min_memory
                
            if int(service_node) == 0:
                service_node = tenant_service.min_node
            region_api.update_service(tenant_service.service_region,
                                      tenant_name,
                                      tenant_service.service_alias,
                                      {"container_memory": service_memory,
                                                  "node": service_node,
                                                  "image_name": service.image,
                                                  "enterprise_id":tenant.enterprise_id}
                                      )


            # 根据查询到的service,更新 tenant_service中的memory、node、imag
            tenant_service.min_memory = service_memory
            tenant_service.min_node = service_node
            tenant_service.image = service.image
            tenant_service.save()
            return Response(status=200, data={"success":True, "msg":u"升级成功"})
        except Exception as e:
            logger.error("openapi.services", e)
            return Response(status=412, data={"success": False, "msg": u"系统异常"})


class StopCloudServiceView(BaseAPIView):
    allowed_methods = ('POST',)

    def post(self, request, service_id, *args, **kwargs):
        """
        停止服务接口
        ---
        parameters:
            - name: service_id
              description: 服务id
              required: true
              type: string
              paramType: path

        """
        username = request.data.get("username", "system")
        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            logger.error("openapi.services", "service id={0} is not exists".format(service_id))
            return Response(status=406, data={"success": False, "msg": u"服务不存在"})
        # 停止服务
        status, success, msg = manager.stop_service(service, username)
        # 判断是否云市服务
        if service.service_origin == "cloud":
            # 查询并停止依赖服务
            relation_list = TenantServiceRelation.objects.filter(service_id=service.service_id)
            dep_id_list = [x.dep_service_id for x in list(relation_list)]
            dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_id_list)
            for dep_service in list(dep_service_list):
                status, success, msg = manager.stop_service(dep_service, username)
                logger.debug("openapi.services", "dep service:{0} status:{1},{2},{3}".format(dep_service.service_alias, status, success, msg))
        return Response(status=status, data={"success": success, "msg": msg})


