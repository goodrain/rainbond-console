# -*- coding: utf8 -*-
from rest_framework.response import Response
from django.http.response import JsonResponse
from api.views.base import APIView
from www.apiclient.regionapi import RegionInvokeApi
from www.models import TenantServiceInfo, AppService, ServiceInfo, \
    AppServiceRelation, AppServicePort, AppServiceEnv, ServiceExtendMethod, \
    Tenants, Users, PermRelTenant, TenantServiceVolume, TenantServicesPort, \
    AppServiceExtend, AppServiceGroup, ServiceGroupRelation
from www.service_http import RegionServiceApi
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import BaseTenantService
import json
from api.views.services.sendapp import AppSendUtil
from django.conf import settings
from www.region import RegionInfo
from api.back_service_install import BackServiceInstall
from www.utils import sn

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
                        # host_path, volume_id = baseService.add_volume_list(service, volume_path)
                        # json_data = {
                        #     "service_id": service.service_id,
                        #     "category": service.category,
                        #     "host_path": host_path,
                        #     "volume_path": volume_path,
                        #     "enterprise_id":tenant.enterprise_id
                        # }
                        # region_api.add_service_volume(service.service_region,
                        #                               tenant.tenant_name,
                        #                               service.service_alias,
                        #                               json_data)

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
            - name: share_id
              description: share_id
              required: false
              type: string
              paramType: form

        """
        data = {}
        isys = False
        serviceInfo = None
        try:
            service_key = request.data.get('service_key', "")
            app_version = request.data.get('app_version', "")
            logger.debug("group.publish", "invoke publish service method  service_key:" + service_key + " service_version" + app_version)
            image = request.data.get('image', "")
            slug = request.data.get('slug', "")
            dest_yb = request.data.get('dest_yb', False)
            dest_ys = request.data.get('dest_ys', False)

            app = AppService.objects.get(service_key=service_key, app_version=app_version)
            logger.debug("group.publish", "dest_yb ==> {0} dest_ys ==> {1}".format(dest_yb,dest_ys))
            if not app.dest_yb:
                app.dest_yb = dest_yb
            if not app.dest_ys:
                app.dest_ys = dest_ys
            isok = False
            if app.is_outer and app.dest_yb and app.dest_ys:
                isok = True
            # if app.is_outer and app.dest_ys:
            #     isok = True
            #     app.dest_yb = True
            if not app.is_outer and app.dest_yb:
                isok = True
            if slug != "" and not slug.startswith("/"):
                slug = "/" + slug
            if isok:
                update_version = 1
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
                # 判断是否为组发布
                key = request.data.get('share_id', None)
                if key:
                    serviceInfo.publish_type = "group"
                else:
                    serviceInfo.publish_type = "single"
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
            return Response({"ok": False}, status=500)

        logger.debug("group.publish"," ==> isok:{0}".format(isok))
        logger.debug("group.publish"," ==> isys:{0}".format(isys))
        logger.debug("group.publish"," ==> Publish_YunShi:{0}".format(settings.MODULES["Publish_YunShi"]))

        # 发布到云市,调用http接口发送数据
        if isok and isys and settings.MODULES["Publish_YunShi"]:
            logger.debug("group.publish"," =====> publish to app market!")
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
                logger.error("group.publish", "tenant is not exists,tenant_id={}".format(data["tenant_id"]))
            # 添加发布类型信息: publish or share
            # AppServiceExtend存在信息
            num = AppServiceExtend.objects.filter(service_key=service_key, app_version=app_version).count()
            if num == 1:
                data["publish_flow_type"] = 1

            share_id = None
            try:
                share_id = request.data.get('share_id', None)
                logger.debug("group.publish", "====> share id is " + share_id)
            except Exception as e:
                logger.exception(e)
            data["share_id"] = share_id
            apputil.send_services(data)
            # 发送图片
            if str(app.logo) is not None and str(app.logo) != "":
                image_url = str(app.logo)
                logger.debug("group.publish",'send service logo:{}'.format(image_url))
                apputil.send_image('app_logo', image_url)
            # 发送请求到所有的数据中心进行数据同步
            # self.downloadImage(serviceInfo)

            # 判断是否服务组发布,发布是否成功
            logger.debug("group.publish","========> before send app group !")
            app_service_group = None
            try:
                logger.debug(dest_ys)
                if share_id is not None and dest_ys:
                    try:
                        app_service_group = AppServiceGroup.objects.get(ID=share_id)
                    except AppServiceGroup.DoesNotExist as e:
                        logger.exception(e)
                    if app_service_group is not None:
                        curr_step = app_service_group.step
                        if curr_step > 0:
                            logger.debug("group.publish", "before remove one app from app_group ! step {}".format(curr_step))
                            curr_step -= 1
                            logger.debug("group.publish","after remove one app from app_group ! step {}".format(curr_step))
                            app_service_group.step = curr_step
                            app_service_group.save()
                        # 判断是否为最后一次调用,发布到最后一个应用后将组信息填写到云市
                        if curr_step == 0 and app_service_group.is_market:
                            logger.info("group.publish","send group publish info to app_market")
                            # 将服务组信息发送到云市
                            tenant_id = data["tenant_id"]
                            param_data = {"group_name": app_service_group.group_share_alias,
                                          "group_key": app_service_group.group_share_id,
                                          "tenant_id": tenant_id, "group_version": app_service_group.group_version,
                                          "publish_type": app_service_group.publish_type,
                                          "desc": app_service_group.desc,
                                          "installable": app_service_group.installable}
                            # tmp_ids = app_service_group.service_ids
                            # service_id_list = json.loads(tmp_ids)
                            logger.debug("group.publish", "===> group_id {0}".format(app_service_group.group_id))
                            service_id_list = ServiceGroupRelation.objects.filter(group_id=app_service_group.group_id).values_list("service_id", flat=True)
                            if len(service_id_list) > 0:
                                # 查询最新发布的信息发送到云市。现在同一service_id会发布不同版本存在于云市,取出最新发布的
                                app_service_list = self.get_newest_published_service(service_id_list)
                                tenant_service_list = TenantServiceInfo.objects.filter(service_id__in=service_id_list,
                                                                                       tenant_id=tenant_id)
                                service_category_map = {x.service_id: "self" if x.category == "application" else "other"
                                                        for x in tenant_service_list}
                                logger.debug("group.publish", "===> service_category_map {}".format(service_category_map))
                                service_data = []
                                for app in app_service_list:
                                    owner = service_category_map.get(app.service_id,"other")
                                    service_map = {"service_key": app.service_key,
                                                   "version": app.app_version,
                                                   "owner": owner}

                                    service_data.append(service_map)
                                param_data["data"] = service_data
                                # 执行后台安装应用组流程,仅公有云
                                is_publish = sn.instance.cloud_assistant == "goodrain" and (not sn.instance.is_private())
                                if is_publish:
                                    backServiceInstall = BackServiceInstall()
                                    group_id, grdemo_service_ids, url_map, region_name = backServiceInstall.install_services(share_id)
                                    grdemo_console_url = "https://user.goodrain.com/apps/grdemo/myservice/?gid={0}&region={1}".format(
                                        str(group_id), region_name)

                                    param_data.update({"console_url": grdemo_console_url})
                                    param_data.update({"preview_urls": url_map})
                                # 发送组信息到云市
                                num = apputil.send_group(param_data)
                                if num != 0:
                                    logger.exception("publish service group failed!")
                            # 应用组发布成功
                            app_service_group.is_success = True
                            app_service_group.save()
            except Exception as e:
                app_service_group.is_success = False
                app_service_group.save()
                logger.exception("group.publish", e)
                logger.error("group.publish", "publish service group failed!")

        return Response({"ok": True}, status=200)

    def is_published(self,service_id):
        """
        根据service_id判断服务是否发布过
        :param service_id: 服务 ID
        :return: 是否发布, 发布的服务对象
        """
        result = True
        rt_app = None
        service = TenantServiceInfo.objects.get(service_id=service_id)
        if service.category != "app_publish":
            result = False
        else:
            app_list = AppService.objects.filter(service_key=service.service_key, app_version=service.version).order_by(
                "-ID")
            if len(app_list) == 0:
                app_list = AppService.objects.filter(service_key=service.service_key).order_by("-ID")
                if len(app_list) == 0:
                    result = False
                else:
                    rt_app = app_list[0]
            else:
                rt_app = app_list[0]
        return result, rt_app

    def get_newest_published_service(self, service_id_list):
        result = []
        logger.debug("group.publish", "===> service_id_list {0}".format(service_id_list))
        for service_id in service_id_list:
            is_pubilsh, app = self.is_published(service_id)
            if is_pubilsh:
                result.append(app)
                continue
            apps = AppService.objects.filter(service_id=service_id).order_by("-ID")
            if apps:
                result.append(apps[0])
        return result

    # def downloadImage(self, base_info):
    #     if base_info is None:
    #         return
    #     try:
    #         download_task = {}
    #         if base_info.is_slug():
    #             download_task = {"action": "download_and_deploy", "app_key": base_info.service_key,
    #                              "app_version": base_info.version, "namespace": base_info.namespace,
    #                              "dep_sids": json.dumps([])}
    #             for region in RegionInfo.valid_regions():
    #                 logger.info(region)
    #                 regionClient.send_task(region, 'app_slug', json.dumps(download_task))
    #         else:
    #             download_task = {"action": "download_and_deploy", "image": base_info.image,
    #                              "namespace": base_info.namespace, "dep_sids": json.dumps([])}
    #             for region in RegionInfo.valid_regions():
    #                 regionClient.send_task(region, 'app_image', json.dumps(download_task))
    #     except Exception as e:
    #         logger.exception(e)


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
