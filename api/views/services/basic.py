# -*- coding: utf8 -*-
from rest_framework.response import Response

from api.views.base import APIView
from www.apiclient.regionapi import RegionInvokeApi
from www.models import TenantServiceInfo, Tenants, Users, PermRelTenant, TenantServiceVolume, TenantServicesPort
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import BaseTenantService


import logging

logger = logging.getLogger('default')

# regionClient = RegionServiceApi()
baseService = BaseTenantService()
monitorhook = MonitorHook()
region_api = RegionInvokeApi()


class SelectedServiceView(APIView):
    '''
    对单个服务的动作
    '''
    allowed_methods = ('PUT', 'POST',)

    def get(self, request, serviceId, format=None):
        """
        查看服务属性
        """
        try:
            TenantServiceInfo.objects.get(service_id=serviceId)
            return Response({"ok": True}, status=200)
        except TenantServiceInfo.DoesNotExist, e:
            return Response({"ok": False, "reason": e.__str__()}, status=404)

    def post(self, request, serviceId, format=None):
        """
        更新服务属性
        ---
        parameters:
            - name: image
              description: image_name
              required: true
              type: string
              paramType: form
        """
        logger.debug("api.service", request.data)
        image = request.data.get("image", None)
        event_id = request.data.get("event_id", "")
        if serviceId is None or image is None:
            return Response({"success": False, "msg": "param is error!"}, status=500)
        service_num = TenantServiceInfo.objects.filter(service_id=serviceId).count()
        if service_num != 1:
            return Response({"success": False, "msg": "service num is error!"}, status=501)
        logger.debug("api.service", "now update console images")
        try:
            TenantServiceInfo.objects.filter(service_id=serviceId).update(image=image)
        except Exception as e:
            logger.exception("api.service", e)
            logger.error("api.service", "update tenant service image failed! service_id is {}".format(serviceId))
            return Response({"success": False, "msg": "update console failed!"}, status=502)
        # 查询服务
        service = TenantServiceInfo.objects.get(service_id=serviceId)
        # 更新region库
        logger.debug("api.service", "now update region images")
        tenant = Tenants.objects.get(tenant_id=service.tenant_id)
        try:
            region_api.update_service(service.service_region,
                                      tenant.tenant_name,
                                      service.service_alias,
                                      {"image_name": image,"enterprise_id":tenant.enterprise_id})
        except Exception as e:
            logger.exception("api.service", e)
            logger.error("api.service", "update region service image failed!")
            return Response({"success": False, "msg": "update region failed!"}, status=503)
        # 启动服务
        try:
            user_id = service.creater
            user = Users.objects.get(pk=user_id)
            body = {
                "deploy_version": service.deploy_version,
                "operator": user.nick_name,
                "event_id": event_id,
                "enterprise_id": tenant.enterprise_id
            }
            region_api.start_service(service.service_region, tenant.tenant_name, service.service_alias,
                                     body)
            monitorhook.serviceMonitor(user.nick_name, service, 'app_start', True)
        except Exception as e:
            logger.exception("api.service", e)
            logger.error("api.service", "start service error!")
        return Response({"success": True, "msg": "success!"}, status=200)

    def put(self, request, serviceId, format=None):
        """
        更新服务属性,只针对docker image
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
            # 判断是否有 "port_list、"volume_list"、"env_list"
            logger.debug("api.basic", data)
            port_list = data.pop("port_list", None)
            volume_list = data.pop("volume_list", None)
            logger.debug(port_list)
            logger.debug(volume_list)

            TenantServiceInfo.objects.filter(service_id=serviceId).update(**data)
            service = TenantServiceInfo.objects.get(service_id=serviceId)
            tenant = Tenants.objects.get(tenant_id=service.tenant_id)
            region_api.update_service(service.service_region, tenant.tenant_name, service.service_alias,
                                      {"image_name" : data.get("image"),"enterprise_id":tenant.enterprise_id})

            # 添加端口
            default_port_del = True
            region_port_list = []
            if port_list:
                for port in port_list.keys():
                    if int(port) == 5000:
                        default_port_del = False
                        continue
                    num = TenantServicesPort.objects.filter(tenant_id=service.tenant_id,
                                                            service_id=service.service_id,
                                                            container_port=int(port)).count()
                    if num == 0:
                        baseService.addServicePort(service,
                                                   False,
                                                   container_port=int(port),
                                                   protocol="http",
                                                   port_alias='',
                                                   is_inner_service=False,
                                                   is_outer_service=False)
                        port_info = {
                            "tenant_id": service.tenant_id,
                            "service_id": service.service_id,
                            "container_port": int(port),
                            "mapping_port": 0,
                            "protocol": "http",
                            "port_alias": '',
                            "is_inner_service": False,
                            "is_outer_service": False
                        }
                        region_port_list.append(port_info)
            if default_port_del:
                # 删除region的5000
                # data = {"action": "delete", "port_ports": [5000]}
                region_api.delete_service_port(service.service_region,
                                               tenant.tenant_name,
                                               service.service_alias,
                                               5000,
                                               tenant.enterprise_id)
                #                                service.service_id,
                #                                json.dumps(data))
                # 删除console的5000
                TenantServicesPort.objects.filter(tenant_id=service.tenant_id,
                                                  service_id=service.service_id,
                                                  container_port=5000).delete()
            if len(region_port_list) > 0:
                # data = {"action": "add", "ports": region_port_list}
                region_api.add_service_port(service.service_region,
                                            tenant.tenant_name,
                                            service.service_alias,
                                            {"port": region_port_list,"enterprise_id":tenant.enterprise_id})
            # 添加持久化记录
            if volume_list:
                v_number = 1
                for volume_path in volume_list:
                    num = TenantServiceVolume.objects.filter(service_id=service.service_id,
                                                             volume_path=volume_path).count()
                    if num == 0:
                        baseService.add_volume_v2(tenant, service, "dockerfile_volume"+str(v_number), volume_path, "share-file")
                        v_number += 1

            return Response({"ok": True}, status=201)
        except TenantServiceInfo.DoesNotExist as e:
            logger.error(e)
            return Response({"ok": False, "reason": e.__str__()}, status=404)

    def transform_fields(self, data):
        field_map = (('container_env', 'env'), ('image_name', 'image'),
                     ('container_cmd', 'cmd'), ('container_memory', 'memory'),
                     ('replicas', 'node'))
        for local_name, remote_name in field_map:
            if remote_name in data:
                data[local_name] = data[remote_name]
                del data[remote_name]
        return data


class PublishServiceView(APIView):
    allowed_methods = ('post',)

    def init_data(self, app, slug, image):
        data = {}
        data["service_key"] = app.service_key
        data["publisher"] = app.publisher
        data["service_name"] = app.app_alias
        data["pic"] = app.logo
        data["info"] = app.info
        data["desc"] = app.desc
        # 修改为根据app_service status数据
        data["status"] = "published"
        if app.status == "private":
            data["status"] = app.status
        data["category"] = "app_publish"
        data["is_service"] = app.is_service
        data["is_web_service"] = app.is_web_service
        data["version"] = app.app_version
        data["update_version"] = 1
        if image != "":
            data["image"] = image
        else:
            data["image"] = app.image
        data["slug"] = slug
        data["extend_method"] = app.extend_method
        data["cmd"] = app.cmd
        data["setting"] = ""
        # SLUG_PATH=/app_publish/redis-stat/20151201175854.tgz,
        if slug != "":
            data["env"] = app.env + ",SLUG_PATH=" + slug + ","
        else:
            data["env"] = app.env
        data["dependecy"] = ""
        data["min_node"] = app.min_node
        data["min_cpu"] = app.min_cpu
        data["min_memory"] = app.min_memory
        data["inner_port"] = app.inner_port
        data["volume_mount_path"] = app.volume_mount_path
        data["service_type"] = app.service_type
        data["is_init_accout"] = app.is_init_accout
        data["creater"] = app.creater
        data["namespace"] = app.namespace
        if hasattr(app, "show_app"):
            data["show_app"] = app.show_app
        if hasattr(app, "show_assistant"):
            data["show_assistant"] = app.show_assistant
        # 租户信息
        data["tenant_id"] = app.tenant_id
        return data


class QueryTenantView(APIView):
    """根据用户email查询用户所有的租户信息"""
    allowed_methods = ('post',)

    def post(self, request, format=None):
        """
        根据用户的email获取当前用户的所有租户信息
        ---
        parameters:
            - name: email
              description: email
              required: true
              type: string
              paramType: form
        """
        user_id = request.data['user_id']
        logger.debug('---user user_id:{}---'.format(user_id))
        # 获取用户对应的
        try:
            user_info = Users.objects.get(user_id=user_id)
            nick_name = user_info.nick_name
            data = {"nick_name": nick_name}

            # 获取所有的租户信息
            prt_list = PermRelTenant.objects.filter(user_id=user_id)
            tenant_id_list = [x.tenant_id for x in prt_list]
            # 查询租户信息
            tenant_list = Tenants.objects.filter(pk__in=tenant_id_list)
            tenant_map_list = []
            for tenant in list(tenant_list):
                tenant_map_list.append({"tenant_id": tenant.tenant_id,
                                        "tenant_name": tenant.tenant_name})
            data["tenant_list"] = tenant_map_list
            return Response({'data': data}, status=200)
        except Users.DoesNotExist:
            logger.error("---no user info for:{}".format(user_id))
        return Response(status=500)
