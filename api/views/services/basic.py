# -*- coding: utf8 -*-
from rest_framework.response import Response
from django.http.response import JsonResponse
from api.views.base import APIView
from www.models import TenantServiceInfo, AppService, ServiceInfo, \
    AppServiceRelation, AppServicePort, AppServiceEnv, ServiceExtendMethod, \
    Tenants, Users, PermRelTenant, TenantServiceVolume, TenantServicesPort, \
    AppServiceExtend
from www.service_http import RegionServiceApi
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import BaseTenantService
import json
from api.views.services.sendapp import AppSendUtil
from django.conf import settings
from www.region import RegionInfo

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()
baseService = BaseTenantService()
monitorhook = MonitorHook()


class SelectedServiceView(APIView):
    '''
    对单个服务的动作
    '''
    allowed_methods = ('PUT','POST',)

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
        try:
            regionClient.update_service(service.service_region, serviceId, {"image": image})
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
                "operator": user.nick_name
            }
            regionClient.start(service.service_region, service.service_id, json.dumps(body))
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
            port_list = data.pop("port_list", None)
            volume_list = data.pop("volume_list", None)
            logger.debug(port_list)
            logger.debug(volume_list)

            TenantServiceInfo.objects.filter(service_id=serviceId).update(**data)
            service = TenantServiceInfo.objects.get(service_id=serviceId)
            regionClient.update_service(service.service_region, serviceId, data)
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
                data = {"action": "delete", "port_ports": [5000]}
                regionClient.createServicePort(service.service_region,
                                               service.service_id,
                                               json.dumps(data))
                # 删除console的5000
                TenantServicesPort.objects.filter(tenant_id=service.tenant_id,
                                                  service_id=service.service_id,
                                                  container_port=5000).delete()
            if len(region_port_list) > 0:
                data = {"action": "add", "ports": region_port_list}
                regionClient.createServicePort(service.service_region,
                                               service.service_id,
                                               json.dumps(data))
            # 添加持久化记录
            if volume_list:
                for volume_path in volume_list:
                    num = TenantServiceVolume.objects.filter(service_id=service.service_id,
                                                             volume_path=volume_path).count()
                    if num == 0:
                        host_path, volume_id = baseService.add_volume_list(service, volume_path)
                        json_data = {
                            "service_id": service.service_id,
                            "category": service.category,
                            "host_path": host_path,
                            "volume_path": volume_path
                        }
                        regionClient.createServiceVolume(service.service_region,
                                                         service.service_id,
                                                         json.dumps(json_data))

            return Response({"ok": True}, status=201)
        except TenantServiceInfo.DoesNotExist as e:
            logger.error(e)
            return Response({"ok": False, "reason": e.__str__()}, status=404)


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
        isys = False
        try:
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
            if slug != "" and not slug.startswith("/"):
                slug = "/" + slug
            if isok:
                update_version = 1
                serviceInfo = None
                try:
                    serviceInfo = ServiceInfo.objects.get(service_key=service_key, version=app_version)
                    update_version = serviceInfo.update_version + 1
                except Exception:
                    pass
                if serviceInfo is None:
                    serviceInfo = ServiceInfo()
                serviceInfo.service_key = app.service_key
                serviceInfo.publisher = app.publisher
                serviceInfo.service_name = app.app_alias
                serviceInfo.pic = app.logo
                serviceInfo.info = app.info
                serviceInfo.desc = app.desc
                serviceInfo.status = "published"
                if app.status == "private":
                    serviceInfo.status = app.status
                serviceInfo.category = "app_publish"
                serviceInfo.is_service = app.is_service
                serviceInfo.is_web_service = app.is_web_service
                serviceInfo.version = app.app_version
                serviceInfo.update_version = update_version
                if image != "":
                    serviceInfo.image = image
                else:
                    serviceInfo.image = app.image
                serviceInfo.slug = slug
                serviceInfo.extend_method = app.extend_method
                serviceInfo.cmd = app.cmd
                serviceInfo.setting = ""
                # SLUG_PATH=/app_publish/redis-stat/20151201175854.tgz,
                if slug != "":
                    serviceInfo.env = app.env + ",SLUG_PATH=" + slug + ","
                else:
                    serviceInfo.env = app.env
                serviceInfo.dependecy = ""
                serviceInfo.min_node = app.min_node
                serviceInfo.min_cpu = app.min_cpu
                serviceInfo.min_memory = app.min_memory
                serviceInfo.inner_port = app.inner_port
                serviceInfo.volume_mount_path = app.volume_mount_path
                serviceInfo.service_type = app.service_type
                serviceInfo.is_init_accout = app.is_init_accout
                serviceInfo.creater = app.creater
                serviceInfo.namespace = app.namespace
                serviceInfo.save()
            app.is_ok = isok
            if slug != "":
                app.slug = slug
            if image != "":
                app.image = image
            app.save()
            isys = app.dest_ys
        except Exception as e:
            logger.exception(e)

        # 发布到云市,调用http接口发送数据
        if isok and isys and settings.MODULES["Publish_YunShi"]:
            data = self.init_data(app, slug, image)
            apputil = AppSendUtil(service_key, app_version)
            # 发送服务参数不发送图片参数
            if data.get("pic") is not None:
                data.pop('pic')
            data["show_category"] = app.show_category
            # 添加租户信息
            try:
                tenant = Tenants.objects.get(tenant_id=data["tenant_id"])
                data["tenant_name"] = tenant.tenant_name
            except Tenants.DoesNotExist:
                logger.error("tenant is not exists,tenant_id={}".format(data["tenant_id"]))
            # 添加发布类型信息: publish or share
            # AppServiceExtend存在信息
            num = AppServiceExtend.objects.filter(service_key=service_key, app_version=app_version).count()
            if num == 1:
                data["publish_flow_type"] = 1
            apputil.send_services(data)
            # 发送图片
            if str(app.logo) is not None and str(app.logo) != "":
                image_url = str(app.logo)
                logger.debug('send service logo:{}'.format(image_url))
                apputil.send_image('app_logo', image_url)
            # 发送请求到所有的数据中心进行数据同步
            # self.downloadImage(serviceInfo)

        return Response({"ok": True}, status=200)

    def downloadImage(self, base_info):
        if base_info is None:
            return
        try:
            download_task = {}
            if base_info.is_slug():
                download_task = {"action": "download_and_deploy", "app_key": base_info.service_key, "app_version": base_info.version, "namespace": base_info.namespace, "dep_sids": json.dumps([])}
                for region in RegionInfo.valid_regions():
                    logger.info(region)
                    regionClient.send_task(region, 'app_slug', json.dumps(download_task))
            else:
                download_task = {"action": "download_and_deploy", "image": base_info.image, "namespace": base_info.namespace, "dep_sids": json.dumps([])}
                for region in RegionInfo.valid_regions():
                    regionClient.send_task(region, 'app_image', json.dumps(download_task))
        except Exception as e:
            logger.exception(e)


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
                base_info.service_key = service_data.get("service_key")
                base_info.publisher = service_data.get("publisher")
                base_info.service_name = service_data.get("service_name")
                base_info.pic = service_data.get("pic")
                base_info.info = service_data.get("info")
                base_info.desc = service_data.get("desc")
                base_info.status = service_data.get("status")
                base_info.category = service_data.get("category")
                base_info.is_service = service_data.get("is_service")
                base_info.is_web_service = service_data.get("is_web_service")
                base_info.version = service_data.get("app_version")
                base_info.update_version = service_data.get("update_version")
                base_info.image = service_data.get("image")
                base_info.slug = service_data.get("slug")
                base_info.extend_method = service_data.get("extend_method")
                base_info.cmd = service_data.get("cmd")
                base_info.setting = service_data.get("setting")
                base_info.env = service_data.get("env")
                base_info.dependecy = service_data.get("dependecy")
                base_info.min_node = service_data.get("min_node")
                base_info.min_cpu = service_data.get("min_cpu")
                base_info.min_memory = service_data.get("min_memory")
                base_info.inner_port = service_data.get("inner_port")
                # base_info.publish_time = service_data.publish_time
                base_info.volume_mount_path = service_data.get("volume_mount_path")
                base_info.service_type = service_data.get("service_type")
                base_info.is_init_accout = service_data.get("is_init_accout")
                base_info.save()
                logger.debug('---add app service---ok---')
                # 保存service_env
                pre_list = json_data.get('pre_list', None)
                suf_list = json_data.get('suf_list', None)
                env_list = json_data.get('env_list', None)
                port_list = json_data.get('port_list', None)
                extend_list = json_data.get('extend_list', None)

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
                        app_env = AppServiceEnv(service_key=env.get("service_key"),
                                                app_version=env.get("app_version"),
                                                name=env.get("name"),
                                                attr_name=env.get("attr_name"),
                                                attr_value=env.get("attr_value"),
                                                scope=env.get("scope"),
                                                is_change=env.get("is_change"),
                                                container_port=env.get("container_port"))
                        env_data.append(app_env)
                    AppServiceEnv.objects.bulk_create(env_data)
                logger.debug('---add app service env---ok---')
                # 端口信息
                if port_list:
                    port_data = []
                    for port in port_list:
                        app_port = AppServicePort(service_key=port.get("service_key"),
                                                  app_version=port.get("app_version"),
                                                  container_port=port.get("container_port"),
                                                  protocol=port.get("protocol"),
                                                  port_alias=port.get("port_alias"),
                                                  is_inner_service=port.get("is_inner_service"),
                                                  is_outer_service=port.get("is_outer_service"))
                        port_data.append(app_port)
                    AppServicePort.objects.bulk_create(port_data)
                logger.debug('---add app service port---ok---')
                # 扩展信息
                if extend_list:
                    extend_data = []
                    for extend in extend_list:
                        app_port = ServiceExtendMethod(service_key=extend.get("service_key"),
                                                       app_version=extend.get("app_version"),
                                                       min_node=extend.get("min_node"),
                                                       max_node=extend.get("max_node"),
                                                       step_node=extend.get("step_node"),
                                                       min_memory=extend.get("min_memory"),
                                                       max_memory=extend.get("max_memory"),
                                                       step_memory=extend.get("step_memory"))
                        extend_data.append(app_port)
                    ServiceExtendMethod.objects.bulk_create(extend_data)
                logger.debug('---add app service extend---ok---')
                # 服务依赖关系
                relation_data = []
                if pre_list:
                    for relation in pre_list:
                        app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                          app_version=relation.get("app_version"),
                                                          app_alias=relation.get("app_alias"),
                                                          dep_service_key=relation.get("dep_service_key"),
                                                          dep_app_version=relation.get("dep_app_version"),
                                                          dep_app_alias=relation.get("dep_app_alias"))
                        relation_data.append(app_relation)
                if suf_list:
                    for relation in suf_list:
                        app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                          app_version=relation.get("app_version"),
                                                          app_alias=relation.get("app_alias"),
                                                          dep_service_key=relation.get("dep_service_key"),
                                                          dep_app_version=relation.get("dep_app_version"),
                                                          dep_app_alias=relation.get("dep_app_alias"))
                        relation_data.append(app_relation)
                AppServiceRelation.objects.bulk_create(relation_data)
                logger.debug('---add app service relation---ok---')
        except Exception as e:
            logger.exception(e)

        return Response({"ok": True}, status=200)


class QueryServiceView(APIView):
    """ receive service info from cloud market to cloud assistant"""
    allowed_methods = ('post',)

    def post(self, request, format=None):
        """
        从云市查询服务信息
        ---
        parameters:
            - name: service_key
              description: service_key
              required: true
              type: string
              paramType: form
            - name: app_version
              description: app_version
              required: true
              type: string
              paramType: form
            - name: cloud_assistant
              description: 云帮标识
              required: false
              type: string
              paramType: form
        """
        try:
            print request.data

            service_key = request.POST.get('service_key')
            app_version = request.POST.get('app_version')

            utils = AppSendUtil(service_key, app_version)
            json_data = utils.query_service(service_key, app_version)
            logger.debug('---receive data---{}'.format(json_data))

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
                base_info.service_key = service_data.get("service_key")
                base_info.publisher = service_data.get("publisher")
                base_info.service_name = service_data.get("service_name")
                base_info.pic = service_data.get("pic")
                base_info.info = service_data.get("info")
                base_info.desc = service_data.get("desc")
                base_info.status = service_data.get("status")
                base_info.category = service_data.get("category")
                base_info.is_service = service_data.get("is_service")
                base_info.is_web_service = service_data.get("is_web_service")
                base_info.version = service_data.get("app_version")
                base_info.update_version = service_data.get("update_version")
                base_info.image = service_data.get("image")
                base_info.slug = service_data.get("slug")
                base_info.extend_method = service_data.get("extend_method")
                base_info.cmd = service_data.get("cmd")
                base_info.setting = service_data.get("setting")
                base_info.env = service_data.get("env")
                base_info.dependecy = service_data.get("dependecy")
                base_info.min_node = service_data.get("min_node")
                base_info.min_cpu = service_data.get("min_cpu")
                base_info.min_memory = service_data.get("min_memory")
                base_info.inner_port = service_data.get("inner_port")
                # base_info.publish_time = service_data.publish_time
                base_info.volume_mount_path = service_data.get("volume_mount_path")
                base_info.service_type = service_data.get("service_type")
                base_info.is_init_accout = service_data.get("is_init_accout")
                # base_info.save()
                logger.debug('---add app service---ok---')
                # 保存service_env
                pre_list = json_data.get('pre_list', None)
                suf_list = json_data.get('suf_list', None)
                env_list = json_data.get('env_list', None)
                port_list = json_data.get('port_list', None)
                extend_list = json_data.get('extend_list', None)
                # 新增环境参数
                if env_list:
                    env_data = []
                    for env in env_list:
                        app_env = AppServiceEnv(service_key=env.get("service_key"),
                                                app_version=env.get("app_version"),
                                                name=env.get("name"),
                                                attr_name=env.get("attr_name"),
                                                attr_value=env.get("attr_value"),
                                                scope=env.get("scope"),
                                                is_change=env.get("is_change"),
                                                container_port=env.get("container_port"))
                        env_data.append(app_env)
                    AppServiceEnv.objects.bulk_create(env_data)
                logger.debug('---add app service env---ok---')
                # 端口信息
                if port_list:
                    port_data = []
                    for port in port_list:
                        app_port = AppServicePort(service_key=port.get("service_key"),
                                                  app_version=port.get("app_version"),
                                                  container_port=port.get("container_port"),
                                                  protocol=port.get("protocol"),
                                                  port_alias=port.get("port_alias"),
                                                  is_inner_service=port.get("is_inner_service"),
                                                  is_outer_service=port.get("is_outer_service"))
                        port_data.append(app_port)
                    AppServicePort.objects.bulk_create(port_data)
                logger.debug('---add app service port---ok---')
                # 扩展信息
                if extend_list:
                    extend_data = []
                    for extend in extend_list:
                        app_port = ServiceExtendMethod(service_key=extend.get("service_key"),
                                                       app_version=extend.get("app_version"),
                                                       min_node=extend.get("min_node"),
                                                       max_node=extend.get("max_node"),
                                                       step_node=extend.get("step_node"),
                                                       min_memory=extend.get("min_memory"),
                                                       max_memory=extend.get("max_memory"),
                                                       step_memory=extend.get("step_memory"),
                                                       is_restart=extend.get("is_restart"))
                        extend_data.append(app_port)
                    ServiceExtendMethod.objects.bulk_create(extend_data)
                logger.debug('---add app service extend---ok---')
                # 服务依赖关系
                relation_data = []
                if pre_list:
                    for relation in pre_list:
                        app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                          app_version=relation.get("app_version"),
                                                          app_alias=relation.get("app_alias"),
                                                          dep_service_key=relation.get("dep_service_key"),
                                                          dep_app_version=relation.get("dep_app_version"),
                                                          dep_app_alias=relation.get("dep_app_alias"))
                        relation_data.append(app_relation)
                if suf_list:
                    for relation in suf_list:
                        app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                          app_version=relation.get("app_version"),
                                                          app_alias=relation.get("app_alias"),
                                                          dep_service_key=relation.get("dep_service_key"),
                                                          dep_app_version=relation.get("dep_app_version"),
                                                          dep_app_alias=relation.get("dep_app_alias"))
                        relation_data.append(app_relation)
                AppServiceRelation.objects.bulk_create(relation_data)
                logger.debug('---add app service relation---ok---')
        except Exception as e:
            logger.exception(e)
        return Response({"ok": True}, status=200)


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


