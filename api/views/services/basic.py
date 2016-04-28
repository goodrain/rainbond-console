# -*- coding: utf8 -*-
from rest_framework.response import Response
from api.views.base import APIView
from www.models import TenantServiceInfo, ServiceInfo, TenantServiceAuth, AppService, ServiceInfo
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
        
class PublishServiceView(APIView):
    allowed_methods = ('post',)

    def post(self, request, format=None):
        """
        获取某个租户信息(tenant_id或者tenant_name)
        ---
        parameters:
            - name: service_key
              description: 服务key
              required: true
              type: string
              paramType: form
            - name: app_version
              description: 服务版本
              required: true
              type: string
              paramType: form
            - name: image
              description: 镜像名
              required: false
              type: string
              paramType: form
            - name: slug
              description: slug包
              required: false
              type: string
              paramType: form

        """
        data = {}
        try:
            print request.data
            service_key = request.data.get('service_key', "")
            app_version = request.data.get('app_version', "")
            image = request.data.get('image', "")
            slug = request.data.get('slug', "")
            app = AppService.objects.get(service_key=service_key, app_version=app_version)
            data = {}
            data["service_key"] = app.service_key
            data["publisher"] = app.publisher
            data["service_name"] = app.app_alias
            data["pic"] = app.logo
            data["info"] = app.info
            data["desc"] = app.desc
            data["status"] = ""
            data["category"] = app.category
            data["is_service"] = app.is_service
            data["is_web_service"] = app.is_web_service
            data["version"] = app.app_version
            data["update_version"] = 1
            data["image"] = image
            data["slug"] = slug
            data["cmd"] = app.cmd
            data["env"] = app.env
            data["dependecy"] = ""
            data["min_node"] = app.min_node
            data["min_cpu"] = app.min_cpu
            data["min_memory"] = app.min_memory
            data["volume_mount_path"] = app.volume_mount_path
            data["service_type"] = app.service_type
            data["is_init_accout"] = app.is_init_accout
            data["creater"] = app.creater
            ServiceInfo(**data).save()
            app.is_ok = True
            app.slug = slug
            app.image = image
            app.save()
        except Exception as e:
            logger.exception(e)
        return Response(data, status=200)
