# -*- coding: utf8 -*-
import json
from django.template.response import TemplateResponse
from django.http.response import HttpResponse, JsonResponse, Http404
# from django.db.models import Q
# from django import forms
# from django.conf import settings

from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import TenantServicesPort, TenantServiceEnvVar
from www.service_http import RegionServiceApi
from www.utils.crypt import make_uuid
# from www.servicetype import ServiceType
from www.utils import sn

from www.models import AppService, AppServiceShareInfo, AppServicePort, \
    TenantServiceVolume, ServiceGroup, ServiceExtendMethod, \
    TenantServiceRelation, TenantServiceInfo, AppServiceGroup, \
    AppServiceEnv, AppServiceVolume, AppServiceRelation

import logging
import datetime

logger = logging.getLogger('default')
regionClient = RegionServiceApi()


class ServiceGroupSharePreview(LeftSideBarMixin, AuthedView):
    """ 服务组发布 """
    def get_context(self):
        context = super(ServiceGroupSharePreview, self).get_context()
        return context

    # form提交.
    @perm_required('app_publish')
    def post(self, request, groupId, *args, **kwargs):
        # 获取要发布的服务id
        service_ids = request.POST.get("service_ids", None)
        if service_ids is None:
            data = {"success": False, "code": 404, 'msg': '请选择发布的服务!'}
            return JsonResponse(data, status=200)
        array_ids = json.loads(service_ids)
        if len(array_ids) == 0:
            data = {"success": False, "code": 404, 'msg': '请选择发布的服务!'}
            return JsonResponse(data, status=200)
        # 检查服务是否安装的镜像服务
        service_list = TenantServiceInfo.objects.filter(service_id__in=array_ids)
        category_list = [x.category for x in service_list if x.category == 'application']
        if len(category_list) == 0:
            data = {"success": False, "code": 406, 'msg': '您的应用组中没有自研应用,请重新选择。'}
            return JsonResponse(data, status=200)

        if len(array_ids) < 2:
            data = {"success": False, "code": 404, "msg": "应用组发布的应用数至少为2个"}
            return JsonResponse(data, status=200)

        # 添加服务组分享信息
        service_ids = service_ids.replace(" ", "")
        # 检查对应的service_id是否存在
        group_count = AppServiceGroup.objects.filter(service_ids=service_ids).count()
        group_share_id = make_uuid(service_ids)
        if group_count == 1:
            app_service_group = AppServiceGroup.objects.get(service_ids=service_ids)

            app_service_group.step = len(array_ids)
            next_url = "/apps/{0}/{1}/{2}/first/".format(self.tenantName, groupId, app_service_group.group_share_id)
            data = {"success": True, "code": 201, "next_url": next_url}
            return JsonResponse(data,status=200)
            # if app_service_group.is_success:
            #     data = {"success": False, "code": 405, 'msg': '相同服务组已经发布!'}
            #     return JsonResponse(data, status=200)
            # else:
            #     app_service_group.step = len(array_ids)
            #     next_url = "/apps/{0}/{1}/{2}/first/".format(self.tenantName, groupId, app_service_group.group_share_id)
            #     data = {"success": False, "code": 201, 'next_url': next_url}
            #     return JsonResponse(data, status=200)
        elif group_count > 1:
            data = {"success": False, "code": 500, 'msg': '系统异常,请联系管理员!'}
            return JsonResponse(data, status=200)
        else:
            # 添加发布记录
            now = datetime.datetime.now()
            app_service_group = AppServiceGroup(group_share_id=group_share_id,
                                                group_share_alias=group_share_id,
                                                service_ids=service_ids,
                                                is_success=False,
                                                group_id=groupId,
                                                step=len(array_ids),
                                                publish_type="services_group",
                                                group_version="0.0.1",
                                                is_market=False,
                                                desc="",
                                                installable=True,
                                                create_time=now,
                                                update_time=now)
            app_service_group.save()
        next_url = "/apps/{0}/{1}/{2}/first/".format(self.tenantName, groupId, group_share_id)
        data = {"success": False, "code": 200, 'next_url': next_url}
        return JsonResponse(data, status=200)


class ServiceGroupShareOneView(LeftSideBarMixin, AuthedView):
    """服务组发布，设置服务名称"""
    def get_context(self):
        context = super(ServiceGroupShareOneView, self).get_context()
        return context

    @perm_required('app_publish')
    def get(self, request, groupId, shareId, *args, **kwargs):
        # 跳转到服务发布页面
        context = self.get_context()
        try:
            app_service_group = AppServiceGroup.objects.get(group_share_id=shareId)
            service_group = ServiceGroup.objects.get(pk=groupId)
            context.update({"service_group": service_group,
                            "tenant_name": self.tenantName,
                            "group_id": groupId,
                            "share_id": shareId,
                            "app_service_group": app_service_group})
        except AppServiceGroup.DoesNotExist:
            logger.error("service group not exist")
            raise Http404

        return TemplateResponse(request,
                                'www/service/groupShare_step_one.html',
                                context)

    # form提交.
    @perm_required('app_publish')
    def post(self, request, groupId, shareId, *args, **kwargs):
        # todo 添加校验，group_id是否属于当前租户、用户
        logger.debug("service group publish:{0}".format(groupId))
        try:
            service_share_alias = request.POST.get("alias", None)
            publish_type = request.POST.get("publish_type", None)
            group_version = request.POST.get("group_version", "0.0.1")
            desc = request.POST.get("desc", None)
            is_market = request.POST.get("is_market", True)
            installable = request.POST.get("installable", True)
            if service_share_alias and publish_type:
                app_service_group = AppServiceGroup.objects.get(group_share_id=shareId)
                app_service_group.group_share_alias = service_share_alias
                app_service_group.publish_type = publish_type
                app_service_group.group_version = group_version
                app_service_group.desc = desc
                app_service_group.is_market = is_market
                app_service_group.installable = installable
                app_service_group.update_time = datetime.datetime.now()
                app_service_group.save()
        except AppServiceGroup.DoesNotExist:
            logger.error("service group not exist")
            data = {"success": False, "code": 500, 'msg': '系统异常!'}
            return JsonResponse(data, status=200)

        data = {"success": True, "code": 200, 'msg': '更新成功!'}
        return JsonResponse(data, status=200)
        # return TemplateResponse(self.request,
        #                         'www/service/groupShare_step_two.html',
        #                         context)


class ServiceGroupShareTwoView(LeftSideBarMixin, AuthedView):
    """ 服务参数配置页面 """
    def get_context(self):
        context = super(ServiceGroupShareTwoView, self).get_context()
        return context

    @perm_required('app_publish')
    def get(self, request, groupId, shareId, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        try:
            app_service_group = AppServiceGroup.objects.get(group_share_id=shareId)
            service_ids = app_service_group.service_ids
            array_ids = json.loads(service_ids)
            # 查询服务信息
            service_list = TenantServiceInfo.objects.filter(service_id__in=array_ids)
            # 查询服务端口信息
            port_list = TenantServicesPort.objects.filter(service_id__in=array_ids)
            service_port_map = {}
            for port in port_list:
                service_id = port.service_id
                tmp_list = []
                if service_id in service_port_map.keys():
                    tmp_list = service_port_map.get(service_id)
                tmp_list.append(port)
                service_port_map[service_id] = tmp_list
            # 查询服务依赖信息
            relation_list = TenantServiceRelation.objects.filter(service_id__in=array_ids)
            dep_service_map = {}
            for dep_service in relation_list:
                service_id = dep_service.service_id
                tmp_list = []
                if service_id in dep_service_map.keys():
                    tmp_list = dep_service_map.get(service_id)
                dep_service_info = TenantServiceInfo.objects.filter(service_id=dep_service.dep_service_id )[0]
                tmp_list.append(dep_service_info)
                dep_service_map[service_id] = tmp_list
            # relation_id_list = [x.dep_service_id for x in relation_list]
            # relation_info_list = TenantServiceInfo.objects.filter(service_id__in=relation_id_list)
            # relation_info_map = {x.service_id: x for x in relation_info_list}
            # 查询服务环境变量(可变、不可变)
            env_list = TenantServiceEnvVar.objects.filter(service_id__in=array_ids, container_port__lte=0)
            env_change_list = [x for x in env_list if x.is_change]
            env_nochange_list = [x for x in env_list if not x.is_change]
            service_env_change_map = {}
            for env in env_change_list:
                service_id = env.service_id
                tmp_list = []
                if service_id in service_env_change_map.keys():
                    tmp_list = service_env_change_map.get(service_id)
                tmp_list.append(env)
                service_env_change_map[service_id] = tmp_list
            service_env_nochange_map = {}
            for env in env_nochange_list:
                service_id = env.service_id
                tmp_list = []
                if service_id in service_env_nochange_map.keys():
                    tmp_list = service_env_nochange_map.get(service_id)
                tmp_list.append(env)
                service_env_nochange_map[service_id] = tmp_list
            # 查询服务持久化信息
            volume_list = TenantServiceVolume.objects.filter(service_id__in=array_ids)
            service_volume_map = {}
            for volume in volume_list:
                service_id = volume.service_id
                tmp_list = []
                if service_id in service_volume_map.keys():
                    tmp_list = service_volume_map.get(service_id)
                tmp_list.append(volume)
                service_volume_map[service_id] = tmp_list

            context.update({"service_list": service_list,
                            "port_map": service_port_map,
                            "relation_info_map": dep_service_map,
                            "env_change_map": service_env_change_map,
                            "env_nochange_map": service_env_nochange_map,
                            "volume_map": service_volume_map})
            context.update({"tenant_name": self.tenantName,
                            "group_id": groupId,
                            "share_id": shareId})
        except Exception as e:
            logger.error("service group not exist")
            logger.exception(e)
            raise Http404
        return TemplateResponse(request,
                                'www/service/groupShare_step_two.html',
                                context)

    # form提交
    @perm_required('app_publish')
    def post(self, request, groupId, shareId, *args, **kwargs):
        # todo 添加服务组校验
        logger.debug("service group publish: {0}-{1}".format(groupId, shareId))
        env_data = request.POST.get("env_data", None)
        if env_data is not None:
            env_json = json.loads(env_data)
            app_share_list = []
            for env_service_id in env_json:
                env_map = env_json.get(env_service_id)
                for env_id in env_map:
                    is_change = env_map.get(env_id)
                    # 判断是否存在
                    num = AppServiceShareInfo.objects.filter(tenant_id=self.tenant.tenant_id,
                                                             service_id=env_service_id,
                                                             tenant_env_id=env_id).count()
                    if num == 1:
                        AppServiceShareInfo.objects.filter(tenant_id=self.tenant.tenant_id,
                                                           service_id=env_service_id,
                                                           tenant_env_id=env_id).update(is_change=bool(is_change))
                    elif num > 1:
                        AppServiceShareInfo.objects.filter(tenant_id=self.tenant.tenant_id,
                                                           service_id=env_service_id,
                                                           tenant_env_id=env_id).delete()
                    if num != 1:
                        tmp_info = AppServiceShareInfo(tenant_id=self.tenant.tenant_id,
                                                       service_id=env_service_id,
                                                       tenant_env_id=env_id,
                                                       is_change=bool(is_change))
                        app_share_list.append(tmp_info)
            # 批量增加
            if len(app_share_list) > 0:
                AppServiceShareInfo.objects.bulk_create(app_share_list)
        data = {"success": True, "code": 200, 'msg': '更新成功!'}
        return JsonResponse(data, status=200)


class ServiceGroupShareThreeView(LeftSideBarMixin, AuthedView):
    """ 服务基本信息配置页面 """
    def get_context(self):
        context = super(ServiceGroupShareThreeView, self).get_context()
        return context

    @perm_required('app_publish')
    def get(self, request, groupId, shareId, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        try:
            app_service_group = AppServiceGroup.objects.get(group_share_id=shareId)
            service_ids = app_service_group.service_ids
            array_ids = json.loads(service_ids)
            # 查询服务信息
            service_list = TenantServiceInfo.objects.filter(service_id__in=array_ids)
            service_id_list = [x.service_id for x in service_list]
            # 查询是否已经发布过
            app_service_list = AppService.objects.filter(service_id__in=service_id_list)
            app_service_map = {x.service_id:x for x in app_service_list}
            context.update({"service_list": service_list,
                            "app_service_map": app_service_map})
            context.update({"tenant_name": self.tenantName,
                            "group_id": groupId,
                            "share_id": shareId})
        except Exception as e:
            logger.error("service group not exist")
            raise Http404
        return TemplateResponse(request,
                                'www/service/groupShare_step_three.html',
                                context)

    # form提交
    @perm_required('app_publish')
    def post(self, request, groupId, shareId, *args, **kwargs):
        logger.debug("service group publish: {0}-{1}".format(groupId, shareId))

        pro_data = request.POST.get("pro_data", None)
        service_ids = request.POST.get("service_ids", "[]")
        try:
        # todo 这里需要一个问题，对于依赖的服务如何设置依赖信息
            if pro_data is not None:
                service_ids = json.loads(service_ids)
                service_list = TenantServiceInfo.objects.filter(service_id__in=service_ids)
                service_map = {x.service_id: x for x in service_list}
                pro_json = json.loads(pro_data)

                app_service_map = {}
                app_service_group = AppServiceGroup.objects.get(group_share_id=shareId)
                for pro_service_id in pro_json:
                    pro_map = pro_json.get(pro_service_id)

                    app_alias = pro_map.get("name")
                    app_version = pro_map.get("version")
                    app_content = pro_map.get("content")
                    # is_init = pro_map.get("is_init") == 1
                    # 默认初始化账户
                    is_init = True
                    is_outer = app_service_group.is_market == 1
                    is_private = app_service_group.is_market == 0
                    # 云帮不显示
                    show_assistant = False
                    show_cloud = app_service_group.is_market == 1

                    # 添加app_service记录
                    service = service_map.get(pro_service_id)
                    app_service = self.add_app_service(service, app_alias, app_version, app_content, is_init, is_outer, is_private, show_assistant, show_cloud)
                    app_service_map[pro_service_id] = app_service
                    # 保存service_port
                    port_list = self.add_app_port(service, app_service.service_key, app_version)
                    logger.debug(u'group.share.service. now add group shared service port for service {0} ok'.format(service.service_id))
                    # 保存env
                    self.add_app_env(service, app_service.service_key, app_version, port_list)
                    logger.debug(u'group.share.service. now add group shared service env for service {0} ok'.format(service.service_id))
                    # 保存extend_info
                    self.add_app_extend_info(service, app_service.service_key, app_version)
                    logger.debug(u'group.share.service. now add group shared service extend method for service {0} ok'.format(service.service_id))
                    # 保存持久化设置
                    self.add_app_volume(service, app_service.service_key, app_version)
                    logger.debug(u'group.share.service. now add group share service volume for service {0} ok'.format(service.service_id))
                # 处理服务依赖关系
                for pro_service_id in pro_json:
                    # 服务依赖关系
                    service = service_map.get(pro_service_id)
                    app_service = app_service_map.get(pro_service_id)
                    self.add_app_relation(service, app_service.service_key, app_service.app_version, app_service.app_alias)
                    logger.debug(u'group.share.service. now add group share service relation for service {0} ok'.format(service.service_id))

                # 设置所有发布服务状态为未发布
                for pro_service_id in pro_json:
                    service = service_map.get(pro_service_id)
                    app_service = app_service_map.get(pro_service_id)
                    app_service.dest_yb = False
                    app_service.dest_ys = False
                    app_service.save()
                    # 发送事件
                    if app_service.is_slug():
                        logger.debug("service group publish slug.")
                        self.upload_slug(app_service, service, shareId)
                    elif app_service.is_image():
                        logger.debug("service group publish image.")
                        self.upload_image(app_service, service, shareId)

            # if len(app_share_list) > 0:
            #     AppServiceShareInfo.objects.bulk_create(app_share_list)
        except Exception as e:
            logger.error("service group publish failed")
            logger.exception(e)
            data = {"success": False, "code": 500, 'msg': '系统异常!'}
        data = {"success": True, "code": 200, 'msg': '更新成功!'}
        return JsonResponse(data, status=200)

    def add_app_service(self, service, app_alias, app_version, app_content, is_init_accout, is_outer, is_private, show_assistant, show_cloud):
        # 获取表单信息
        app_service_list = AppService.objects.filter(service_id=service.service_id).order_by('-ID')[:1]
        app_service = AppService()
        if len(app_service_list) == 1:
            app_service = list(app_service_list)[0]
        else:
            namespace = sn.instance.username
            if service.language == "docker":
                namespace = sn.instance.cloud_assistant
            app_service.tenant_id = service.tenant_id
            app_service.service_id = service.service_id
            app_service.service_key = make_uuid(service.service_alias)
            app_service.creater = self.user.pk
            app_service.status = ''
            app_service.category = "app_publish"
            app_service.is_service = service.is_service
            app_service.is_web_service = service.is_web_service
            app_service.image = service.image
            app_service.namespace = namespace
            app_service.slug = ''
            app_service.extend_method = service.extend_method
            app_service.cmd = service.cmd
            app_service.env = service.env
            app_service.min_node = service.min_node
            app_service.min_cpu = service.min_cpu
            app_service.min_memory = service.min_memory
            app_service.inner_port = service.inner_port
            app_service.volume_mount_path = service.volume_mount_path
            # todo 这里需要注意分享应用为application类型
            app_service.service_type = 'application'
            app_service.show_category = ''
            app_service.is_base = False
            app_service.publisher = self.user.email
            app_service.is_ok = 0
            if service.is_slug():
                app_service.slug = '/app_publish/{0}/{1}.tgz'.format(app_service.service_key, app_version)
            # 更新status、show_app、show_assistant
        app_service.app_alias = app_alias
        app_service.app_version = app_version
        app_service.info = app_content
        app_service.is_init_accout = is_init_accout
        app_service.is_outer = is_outer
        if is_private:
            app_service.status = "private"
        app_service.show_app = show_cloud
        app_service.show_assistant = show_assistant
        app_service.save()
        return app_service

    def add_app_port(self, service, service_key, app_version):
        # query all port
        port_list = TenantServicesPort.objects.filter(tenant_id=service.tenant_id,
                                                      service_id=service.service_id)
        container_port_list = [x.container_port for x in port_list]
        # 删除app_service_port中不存在的port
        AppServicePort.objects.filter(service_key=service_key, app_version=app_version).exclude(container_port__in=container_port_list).delete()
        port_data = []
        for port in list(port_list):
            try:
                app_port = AppServicePort.objects.get(service_key=service_key, app_version=app_version, container_port=port.container_port)
                app_port.protocol = port.protocol
                app_port.port_alias = port.port_alias
                app_port.is_inner_service = port.is_inner_service
                app_port.is_outer_service = port.is_outer_service
                app_port.save()
            except AppServicePort.DoesNotExist as e:
                app_port = AppServicePort(service_key=service_key,
                                          app_version=app_version,
                                          container_port=port.container_port,
                                          protocol=port.protocol,
                                          port_alias=port.port_alias,
                                          is_inner_service=port.is_inner_service,
                                          is_outer_service=port.is_outer_service)
                port_data.append(app_port)
        if len(port_data) > 0:
            AppServicePort.objects.bulk_create(port_data)
        return port_list

    def add_app_env(self, service, service_key, app_version, port_list):
        # 排除端口参数
        exclude_port = [x.container_port for x in port_list]
        env_list = TenantServiceEnvVar.objects.filter(service_id=service.service_id) \
            .exclude(container_port__in=exclude_port) \
            .values('ID', 'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        attr_name_list = [x["attr_name"] for x in env_list]
        # 删除未保留参数
        AppServiceEnv.objects.filter(service_key=service_key, app_version=app_version).exclude(attr_name__in=attr_name_list).delete()
        # 获取参数类型
        share_info_list = AppServiceShareInfo.objects.filter(service_id=service.service_id) \
            .values("tenant_env_id", "is_change")
        share_info_map = {x["tenant_env_id"]: x["is_change"] for x in list(share_info_list)}

        env_data = []
        for env in list(env_list):
            is_change = env["is_change"]
            if env["ID"] in share_info_map.keys():
                is_change = share_info_map.get(env["ID"])
            try:
                app_env = AppServiceEnv.objects.get(service_key=service_key,
                                                    app_version=app_version,
                                                    attr_name=env["attr_name"])
                app_env.app_env = env["name"]
                app_env.attr_value = env["attr_value"]
                app_env.scope = env["scope"]
                app_env.is_change = is_change
                app_env.container_port = env["container_port"]
                app_env.save()
            except AppServiceEnv.DoesNotExist as e:
                app_env = AppServiceEnv(service_key=service_key,
                                        app_version=app_version,
                                        name=env["name"],
                                        attr_name=env["attr_name"],
                                        attr_value=env["attr_value"],
                                        scope=env["scope"],
                                        is_change=is_change,
                                        container_port=env["container_port"])
                env_data.append(app_env)
        if len(env_data) > 0:
            AppServiceEnv.objects.bulk_create(env_data)

    def add_app_extend_info(self, service, service_key, app_version):
        count = ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version).count()
        if count == 0:
            extend_method = ServiceExtendMethod(
                service_key=service_key,
                app_version=app_version,
                min_node=service.min_node,
                max_node=20,
                step_node=1,
                min_memory=service.min_memory,
                max_memory=65536,
                step_memory=128,
                is_restart=False)
            extend_method.save()
        else:
            ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version) \
                .update(min_node=service.min_node, min_memory=service.min_memory)

    def add_app_volume(self, service, service_key, app_version):
        if service.category == "application":
            volume_list = TenantServiceVolume.objects.filter(service_id=service.service_id)
            volume_path_list = [x.volume_path for x in volume_list]
            AppServiceVolume.objects.filter(service_key=service_key,
                                            app_version=app_version)\
                .exclude(volume_path__in=volume_path_list).delete()

            volume_data = []
            for volume in list(volume_list):
                count = AppServiceVolume.objects.filter(service_key=service_key,
                                                        app_version=app_version,
                                                        volume_path=volume.volume_path).count()
                if count == 0:
                    app_volume = AppServiceVolume(service_key=service_key,
                                                  app_version=app_version,
                                                  category=volume.category,
                                                  volume_path=volume.volume_path)
                    volume_data.append(app_volume)
            if len(volume_data) > 0:
                AppServiceVolume.objects.bulk_create(volume_data)

    def add_app_relation(self, service, service_key, app_version, app_alias):
        relation_list = TenantServiceRelation.objects.filter(service_id=service.service_id)
        dep_service_ids = [x.dep_service_id for x in list(relation_list)]
        if len(dep_service_ids) == 0:
            return None
        # 依赖服务的信息
        try:
            dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_service_ids)
            app_relation_list = []
            if len(dep_service_list) > 0:
                for dep_service in dep_service_list:
                    dep_app_count = 0
                    if dep_service.service_key != 'application':
                        # 首先检查key-version，不存在检查service_id,取最近的一个
                        dep_app_count = AppService.objets.filter(service_key=dep_service.service_key,app_version=dep_service.version).count()
                    if dep_app_count == 0:
                        # service_key, version不存在, 检查service_id取最近的一个
                        dep_app_count = AppService.objets.filter(service_id=dep_service.service_id).count()
                    else:
                        dep_app_service = AppService.objects.get(service_key=dep_service.service_key,app_version=dep_service.version)

                    if dep_app_count > 0:
                        dep_app_service = AppService.objects.filter(service_id=dep_service.service_id).order_by("-ID")[0]
                    else:
                        # 不存在对应的app_service, 逻辑异常
                        return 404

                    # 检查是否存在对应的app_relation
                    relation_count = AppServiceRelation.objects.filter(service_key=service_key,
                                                                       app_version=app_version,
                                                                       dep_service_key=dep_app_service.service_key,
                                                                       dep_app_version=dep_app_service.version).count()
                    if relation_count == 0:
                        app_relation = AppServiceRelation(service_key=service_key,
                                                          app_version=app_version,
                                                          app_alias=app_alias,
                                                          dep_service_key=dep_app_service.service_key,
                                                          dep_app_version=dep_app_service.version,
                                                          dep_app_alias=dep_app_service.app_alias)
                        app_relation_list.append(app_relation)
                # 批量添加发布依赖
                if len(app_relation_list) > 0:
                    AppServiceRelation.objects.bulk_create(app_relation_list)
            else:
                # 依赖服务的实力已经被删除,理论上不存在这种情况
                return 400
        except Exception as e:
            logger.error(
                "add app relation error service_key {0},app_version{1},app_alias{2}".format(service_key, app_version,
                                                                                            app_alias))

    def _create_publish_event(self, service, info):
        template = {
            "user_id": self.user.nick_name,
            "tenant_id": service.tenant_id,
            "service_id": service.service_id,
            "type": "publish",
            "desc": info + u"应用发布中...",
            "show": True,
        }
        try:
            body = regionClient.create_event(service.service_region, json.dumps(template))
            return body.event_id
        except Exception as e:
            logger.exception("service.publish", e)
            return None

    def upload_slug(self, app, service, share_id):
        """ 上传slug包 """
        oss_upload_task = {
            "service_key": app.service_key,
            "app_version": app.app_version,
            "service_id": service.service_id,
            "deploy_version": service.deploy_version,
            "tenant_id": service.tenant_id,
            "action": "create_new_version",
            "is_outer": app.is_outer,
            "share_id": share_id,
        }
        try:
            event_id = self._create_publish_event(service, u'云帮')
            oss_upload_task.update({"dest": "yb", "event_id": event_id})
            regionClient.send_task(service.service_region, 'app_slug', json.dumps(oss_upload_task))
            if app.is_outer:
                event_id = self._create_publish_event(service, u"云市")
                oss_upload_task.update({"dest": "ys", "event_id": event_id})
                regionClient.send_task(service.service_region, 'app_slug', json.dumps(oss_upload_task))
        except Exception as e:
            logger.error("service.publish",
                         "service group upload_slug for {0}({1}), but an error occurred".format(app.service_key, app.app_version))
            logger.exception("service.publish", e)

    def upload_image(self, app, service, share_id):
        """ 上传image镜像 """
        image_upload_task = {
            "service_key": app.service_key,
            "app_version": app.app_version,
            "action": "create_new_version",
            "image": service.image,
            "is_outer": app.is_outer,
            "share_id": share_id,
        }
        try:
            event_id = self._create_publish_event(service, u"云帮")
            image_upload_task.update({"dest": "yb", "event_id": event_id})
            regionClient.send_task(service.service_region, 'app_image', json.dumps(image_upload_task))
            if app.is_outer:
                event_id = self._create_publish_event(service, u"云市")
                image_upload_task.update({"dest": "ys", "event_id": event_id})
                regionClient.send_task(service.service_region, 'app_image', json.dumps(image_upload_task))
        except Exception as e:
            logger.error("service.publish",
                         "service group upload_image for {0}({1}), but an error occurred".format(app.service_key, app.app_version))
            logger.exception("service.publish", e)


