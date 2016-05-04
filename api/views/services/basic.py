# -*- coding: utf8 -*-
from rest_framework.response import Response
from django.http.response import JsonResponse
from api.views.base import APIView
from www.models import TenantServiceInfo, AppService, ServiceInfo, \
    AppServiceRelation,AppServicePort, AppServiceEnv, ServiceExtendMethod
from www.service_http import RegionServiceApi
import json
from api.views.services.sendapp import AppSendUtil

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
            - name: dest_yb
              description: dest_yb
              required: false
              type: boolean
              paramType: form
            - name: dest_ys
              description: dest_ys
              required: false
              type: boolean
              paramType: form

        """
        data = {}
        try:
            print request.data
            service_key = request.data.get('service_key', "")
            app_version = request.data.get('app_version', "")
            image = request.data.get('image', "")
            slug = request.data.get('slug', "")
            dest_yb = request.data.get('dest_yb', False)
            dest_ys = request.data.get('dest_ys', False)
            
            app = AppService.objects.get(service_key=service_key, app_version=app_version)
            if not app.dest_yb:
                app.dest_yb = dest_yb
            if not app.dest_ys:
                app.dest_ys = dest_ys
            isok = False
            if app.is_outer and app.dest_yb and app.dest_ys:
                isok = True
            if not app.is_outer and app.dest_yb:
                isok = True
            if isok:
                data = {}
                data["service_key"] = app.service_key
                data["publisher"] = app.publisher
                data["service_name"] = app.app_alias
                data["pic"] = app.logo
                data["info"] = app.info
                data["desc"] = app.desc
                data["status"] = ""
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
                data["volume_mount_path"] = app.volume_mount_path
                data["service_type"] = app.service_type
                data["is_init_accout"] = app.is_init_accout
                data["creater"] = app.creater
                ServiceInfo(**data).save()
            app.is_ok = isok
            app.slug = slug
            app.image = image
            app.save()
        except Exception as e:
            logger.exception(e)

        # 发送服务信息到app
        apputil = AppSendUtil(service_key, app_version)
        # 发送服务参数
        apputil.send_services(data)
        # 发送图片
        apputil.send_image('app_logo', app.logo)

        return Response({"ok": True}, status=200)


class ReceiveServiceView(APIView):
    """ receive service info from cloud market to cloud assistant"""
    allowed_methods = ('post',)

    def post(self, request, format=None):
        """
        获取从云市发送的服务信息
        ---
        parameters:
            - name: service
              description: 服务信息
              required: true
              type: string
              paramType: json
            - name: env_list
              description: 服务环境参数
              required: false
              type: string
              paramType: json
            - name: port_list
              description: 服务端口参数
              required: false
              type: string
              paramType: json
            - name: suf_list
              description: 服务被依赖信息
              required: false
              type: string
              paramType: json
            - name: pre_list
              description: 服务依赖信息
              required: false
              type: string
              paramType: json
            - name: extend_list
              description: 服务扩展信息
              required: false
              type: boolean
              paramType: json

        """
        data = {}
        try:
            print request.data
            # 处理json
            json_data = json.loads(request.body)
            logger.debug('---recive data---{}'.format(json_data))
            service_data = json_data.get('service', None)
            if not service_data:
                logger.error('there is no service data! pls check request')
                return JsonResponse({"success": False, "msg": "参数错误!", "code": 201})
            # 保存发布的服务信息
            # 判断service_key, app_version是否存在,不存在则添加
            service_key = service_data.get('service_key')
            app_version = service_data.get('version')
            num = ServiceInfo.objects.filter(service_key=service_key, version=app_version).count()
            if num == 0:
                # add service
                base_info = ServiceInfo()
                base_info.service_key = service_data.service_key
                base_info.publisher = service_data.publisher
                base_info.service_name = service_data.service_name
                base_info.pic = service_data.pic
                base_info.info = service_data.info
                base_info.desc = service_data.desc
                base_info.status = service_data.status
                base_info.category = service_data.category
                base_info.is_service = service_data.is_service
                base_info.is_web_service = service_data.is_web_service
                base_info.version = service_data.app_version
                base_info.update_version = service_data.update_version
                base_info.image = service_data.image
                base_info.slug = service_data.slug
                base_info.extend_method = service_data.extend_method
                base_info.cmd = service_data.cmd
                base_info.setting = service_data.setting
                base_info.env = service_data.env
                base_info.dependecy = service_data.dependecy
                base_info.min_node = service_data.min_node
                base_info.min_cpu = service_data.min_cpu
                base_info.min_memory = service_data.min_memory
                base_info.inner_port = service_data.inner_port
                # base_info.publish_time = service_data.publish_time
                base_info.volume_mount_path = service_data.volume_mount_path
                base_info.service_type = service_data.service_type
                base_info.is_init_accout = service_data.is_init_accout
                base_info.save()
            logger.debug('---add app service---ok---')
            # 保存service_env
            pre_list = json_data.get('pre_list', None)
            suf_list = json_data.get('suf_list', None)
            env_list = json_data.get('env_list', None)
            port_list = json_data.get('port_list', None)
            extend_list = json_data.get('extend_list', None)

            # 环境参数
            if num > 0:
                # 存在对应的service_key, app_version,清理对应的旧数据
                AppServiceEnv.objects.filter(service_key=service_key,
                                             app_version=app_version).delete()
                logger.debug('now clear AppServiceEnv ok!')
                AppServicePort.objects.filter(service_key=service_key,
                                              app_version=app_version).delete()
                logger.debug('now clear AppServicePort ok!')
                AppServiceRelation.objects.filter(service_key=service_key,
                                                  app_version=app_version).delete()
                logger.debug('now clear AppServiceRelation ok!')
                AppServiceRelation.objects.filter(dep_service_key=service_key,
                                                  dep_app_version=app_version).delete()
                logger.debug('now clear AppServiceRelation dep ok!')
                ServiceExtendMethod.objects.filter(service_key=service_key,
                                                   app_version=app_version).delete()
                logger.debug('now clear ServiceExtendMethod ok!')
            # 新增环境参数
            if env_list:
                env_data = []
                for env in env_list:
                    app_env = AppServiceEnv(service_key=env.service_key,
                                            app_version=env.app_version,
                                            name=env.name,
                                            attr_name=env.attr_name,
                                            attr_value=env.attr_value,
                                            scope=env.scope,
                                            is_change=env.is_change,
                                            container_port=env.container_port)
                    env_data.append(app_env)
                AppServiceEnv.objects.bulk_create(env_data)
            logger.debug('---add app service env---ok---')
            # 端口信息
            if port_list:
                port_data = []
                for port in port_list:
                    app_port = AppServicePort(service_key=port.service_key,
                                              app_version=port.app_version,
                                              container_port=port.container_port,
                                              protocol=port.protocol,
                                              port_alias=port.port_alias,
                                              is_inner_service=port.is_inner_service,
                                              is_outer_service=port.is_outer_service)
                    port_data.append(app_port)
                AppServicePort.objects.bulk_create(port_data)
            logger.debug('---add app service port---ok---')
            # 扩展信息
            if extend_list:
                extend_data = []
                for extend in extend_list:
                    app_port = ServiceExtendMethod(service_key=extend.service_key,
                                                   app_version=extend.app_version,
                                                   min_node=extend.min_node,
                                                   max_node=extend.max_node,
                                                   step_node=extend.step_node,
                                                   min_memory=extend.min_memory,
                                                   max_memory=extend.max_memory,
                                                   step_memory=extend.step_memory)
                    extend_data.append(app_port)
                ServiceExtendMethod.objects.bulk_create(extend_data)
            logger.debug('---add app service extend---ok---')
            # 服务依赖关系
            relation_data = []
            if pre_list:
                for relation in pre_list:
                    app_relation = AppServiceRelation(service_key=relation.service_key,
                                                      app_version=relation.app_version,
                                                      app_alias=relation.app_alias,
                                                      dep_service_key=relation.dep_service_key,
                                                      dep_app_version=relation.dep_app_version,
                                                      dep_app_alias=relation.dep_app_alias)
                    relation_data.append(app_relation)
            if suf_list:
                for relation in suf_list:
                    app_relation = AppServiceRelation(service_key=relation.service_key,
                                                      app_version=relation.app_version,
                                                      app_alias=relation.app_alias,
                                                      dep_service_key=relation.dep_service_key,
                                                      dep_app_version=relation.dep_app_version,
                                                      dep_app_alias=relation.dep_app_alias)
                    relation_data.append(app_relation)
            if len(relation_data) > 0:
                AppServiceRelation.objects.bulk_create(relation_data)
            logger.debug('---add app service relation---ok---')
        except Exception as e:
            logger.exception(e)

        return Response({"ok": True}, status=200)

