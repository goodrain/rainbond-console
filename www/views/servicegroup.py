# -*- coding: utf8 -*-
import json
from django.template.response import TemplateResponse
from django.http.response import HttpResponse, JsonResponse, Http404
# from django.db.models import Q
# from django import forms
# from django.conf import settings

from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import TenantServicesPort, TenantServiceEnvVar, ServiceInfo, PublishedGroupServiceRelation, \
    ServiceGroupRelation, ServiceEvent
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
        try:
            groupId = int(groupId)
            if groupId < 1:
                data = {"success": False, "code": 406, 'msg': '该组应用不可分享'}
                return JsonResponse(data, status=200)
            tenant_service_id_list = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id, group_id=groupId,region_name=self.response_region).values_list("service_id", flat=True)
            service_list = TenantServiceInfo.objects.filter(service_id__in=tenant_service_id_list)
            # appcation 类型的应用和 app_publish类型且language不为None(即image和compose类型)的服务
            can_publish_list = [x for x in service_list if
                                x.category == "application" or (x.category == "app_publish" and x.language is not None)]
            if not can_publish_list:
                data = {"success": False, "code": 406, 'msg': '此组中的应用全部来源于云市,无法发布'}
                return JsonResponse(data, status=200)
            # 判断非云市安装应用是否全部运行中
            # for s in can_publish_list:
            #     body = regionClient.check_service_status(self.response_region,s.service_id)
            #     status = body["status"]
            #     if status != "running":
            #         data = {"success": False, "code": 412, 'msg': '您的应用{0}未运行。'.format(s.service_cname)}
            #         return JsonResponse(data, status=200)
            next_url = "/apps/{0}/{1}/first/".format(self.tenantName, groupId)
            data = {"success": False, "code": 200, 'next_url': next_url}
            return JsonResponse(data, status=200)

        except Exception as e:
            logger.exception(e)


class ServiceGroupShareOneView(LeftSideBarMixin, AuthedView):
    """服务组发布，设置服务名称"""
    def get_context(self):
        context = super(ServiceGroupShareOneView, self).get_context()
        return context

    @perm_required('app_publish')
    def get(self, request, groupId, *args, **kwargs):
        # 跳转到服务发布页面
        context = self.get_context()
        try:
            # 查询最新的一次记录
            group_list = AppServiceGroup.objects.filter(group_id=groupId).order_by("-ID")
            app_service_group = None
            if group_list:
                app_service_group = group_list[0]
            service_group = ServiceGroup.objects.get(pk=groupId)
            context.update({"service_group": service_group,
                            "tenant_name": self.tenantName,
                            "group_id": groupId,
                            "app_service_group": app_service_group})
        except Exception as e:
            logger.error(e)
        return TemplateResponse(request,
                                'www/service/groupShare_step_one.html',
                                context)

    # form提交.
    @perm_required('app_publish')
    def post(self, request, groupId, *args, **kwargs):
        # todo 添加校验，group_id是否属于当前租户、用户
        logger.debug("service group publish:{0}".format(groupId))
        try:
            service_share_alias = request.POST.get("alias", None)
            publish_type = request.POST.get("publish_type", None)
            group_version = request.POST.get("group_version", "0.0.1")
            desc = request.POST.get("desc", None)
            is_market = request.POST.get("is_market", True)
            installable = request.POST.get("installable", True)
            # 查找新的应用关系
            tenant_service_id_list = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id, group_id=groupId,region_name=self.response_region).values_list("service_id", flat=True)
            service_list = TenantServiceInfo.objects.filter(service_id__in=tenant_service_id_list)
            service_id_list = [x.service_id for x in service_list]
            service_ids = ",".join(service_id_list)
            # appcation 类型的应用和 app_publish类型且language不为None(即image和compose类型)的服务
            can_publish_list = [x for x in service_list if
                                x.category == "application" or (x.category == "app_publish" and x.language is not None)]
            now = datetime.datetime.now()

            share_pk = None
            app_service_group = AppServiceGroup.objects.filter(group_id=groupId).order_by("-ID")
            # 如果有记录
            if app_service_group:
                group_share_id = app_service_group[0].group_share_id
                try:
                    # 根据share_id 和 key进行查询,如果存在就进行更新操作
                    group = AppServiceGroup.objects.get(group_share_id=group_share_id, group_version=group_version)
                    group.group_share_alias = service_share_alias
                    group.service_ids = service_ids
                    group.group_id = groupId
                    group.step = len(can_publish_list)
                    group.publish_type = publish_type
                    group.group_version = group_version
                    group.desc = desc
                    group.is_market = is_market
                    group.installable = installable
                    group.update_time = datetime.datetime.now()
                    group.save()
                    share_pk = group.ID
                except AppServiceGroup.DoesNotExist:
                    # 不存在 根据key 和 version 创建新的记录
                    app_service_group = AppServiceGroup(group_share_id=group_share_id,
                                                        group_share_alias=service_share_alias,
                                                        service_ids=service_ids,
                                                        is_success=False,
                                                        group_id=groupId,
                                                        step=len(can_publish_list),
                                                        publish_type=publish_type,
                                                        group_version=group_version,
                                                        is_market=is_market,
                                                        desc=desc,
                                                        installable=installable,
                                                        create_time=now,
                                                        update_time=now)
                    app_service_group.save()
                    share_pk = app_service_group.ID
            else:
                group_share_id = make_uuid(service_ids)
                app_service_group = AppServiceGroup(group_share_id=group_share_id,
                                                    group_share_alias=service_share_alias,
                                                    service_ids=service_ids,
                                                    is_success=False,
                                                    group_id=groupId,
                                                    step=len(can_publish_list),
                                                    publish_type=publish_type,
                                                    group_version=group_version,
                                                    is_market=is_market,
                                                    desc=desc,
                                                    installable=installable,
                                                    create_time=now,
                                                    update_time=now)
                app_service_group.save()
                share_pk = app_service_group.ID

        except Exception as e:
            logger.error(e)
            data = {"success": False, "code": 500, 'msg': '系统异常!'}
            return JsonResponse(data, status=200)
        next_url = "/apps/{0}/{1}/{2}/second/".format(self.tenantName, groupId, share_pk)
        data = {"success": True, "code": 200, 'msg': '更新成功!', 'next_url': next_url}
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
    def get(self, request, groupId, share_pk, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        try:
            array_ids = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id, group_id=groupId,region_name=self.response_region).values_list("service_id", flat=True)
            # service_ids = app_service_group.service_ids
            # array_ids = json.loads(service_ids)
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
                            "share_id": share_pk})
        except Exception as e:
            logger.error("service group not exist")
            logger.exception(e)
            raise Http404
        return TemplateResponse(request,
                                'www/service/groupShare_step_two.html',
                                context)

    # form提交
    @perm_required('app_publish')
    def post(self, request, groupId, share_pk, *args, **kwargs):
        # todo 添加服务组校验
        logger.debug("service group publish: {0}-{1}".format(groupId, share_pk))
        env_data = request.POST.get("env_data", None)
        data = {}
        try:
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
        except Exception as e:
            logger.exception(e)
            data = {"success": False, "code": 500, 'msg': '更新失败'}
        return JsonResponse(data, status=200)


class ServiceGroupShareThreeView(LeftSideBarMixin, AuthedView):
    """ 服务基本信息配置页面 """
    def get_context(self):
        context = super(ServiceGroupShareThreeView, self).get_context()
        return context

    @perm_required('app_publish')
    def get(self, request, groupId, share_pk, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        try:
            app_service_group = AppServiceGroup.objects.get(ID=share_pk)
            array_ids = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id, group_id=groupId,region_name=self.response_region).values_list("service_id", flat=True)
            # service_ids = app_service_group.service_ids
            # array_ids = json.loads(service_ids)
            # 查询服务信息
            service_list = TenantServiceInfo.objects.filter(service_id__in=array_ids)
            service_id_list = [x.service_id for x in service_list]
            # 查询是否已经发布过
            app_service_list = AppService.objects.filter(service_id__in=service_id_list)
            app_service_map = {x.service_id:x for x in app_service_list}
            has_published_map = {}
            for app in service_list:
                # 非自研应用取出应用已发布的信息
                if app.category == "app_publish" and app.language is None:
                    has_pubilshed = AppService.objects.filter(service_key=app.service_key,app_version=app.version)
                    if has_pubilshed:
                        has_published_map[app.service_id] = has_pubilshed[0]
                    else:
                        published_service = ServiceInfo.objects.filter(service_key=app.service_key,version=app.version)
                        if published_service:
                            ps = published_service[0]
                            ps.app_version = ps.version
                            ps.app_alias = ps.service_name
                            has_published_map[app.service_id] = ps
            context.update({"service_list": service_list,
                            "app_service_map": app_service_map})

            context.update({"tenant_name": self.tenantName,
                            "group_id": groupId,
                            "share_id": share_pk})
            context.update({"has_published_map":has_published_map})
        except Exception as e:
            logger.error("service group not exist")
            logger.error(e)
            raise Http404
        return TemplateResponse(request,
                                'www/service/groupShare_step_three.html',
                                context)

    # form提交
    @perm_required('app_publish')
    def post(self, request, groupId, share_pk, *args, **kwargs):
        logger.debug("service group publish: {0}-{1}".format(groupId, share_pk))

        pro_data = request.POST.get("pro_data", None)
        service_ids = request.POST.get("service_ids", "[]")
        try:
            if pro_data is not None:
                service_ids = json.loads(service_ids)
                service_list = TenantServiceInfo.objects.filter(service_id__in=service_ids)
                service_map = {x.service_id: x for x in service_list}
                pro_json = json.loads(pro_data)

                app_service_map = {}
                app_service_group = AppServiceGroup.objects.get(ID=share_pk)
                step = 0
                for pro_service_id in pro_json:
                    is_published, app = self.is_published(pro_service_id)
                    # 已发布的应用,缓存app_service_map,并跳过此次循环
                    if is_published:
                        app_service_map[pro_service_id] = app
                        logger.debug("")
                        continue

                    pro_map = pro_json.get(pro_service_id)

                    app_alias = pro_map.get("name")
                    app_version = pro_map.get("version")
                    app_content = pro_map.get("content")
                    is_init = pro_map.get("is_init") == 1
                    # 默认初始化账户
                    # is_init = False
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
                    # 设置需要发布的步数
                    step += 1
                app_service_group.step = step
                app_service_group.save()
                logger.debug("step ===> {}".format(step))
                # 处理服务依赖关系
                for pro_service_id in pro_json:
                    # 服务依赖关系
                    service = service_map.get(pro_service_id)
                    app_service = app_service_map.get(pro_service_id)
                    result = self.add_app_relation(service, app_service.service_key, app_service.app_version, app_service.app_alias)
                    logger.debug(u'group.share.service. now add group share service relation for service {0} ok'.format(service.service_id),result)

                PublishedGroupServiceRelation.objects.filter(group_pk=app_service_group.ID).delete()
                for s_id, app in app_service_map.items():
                    pgsr_list =  PublishedGroupServiceRelation.objects.filter(group_pk=app_service_group.ID,service_id=s_id)
                    if not pgsr_list:
                        PublishedGroupServiceRelation.objects.create(group_pk=app_service_group.ID, service_id=s_id,
                                                                     service_key=app.service_key,
                                                                     version=app.app_version)
                    else:
                        PublishedGroupServiceRelation.objects.filter(group_pk=app_service_group.ID,
                                                                     service_id=s_id).update(
                            service_key=app.service_key,
                            version=app.app_version)

                # 设置所有发布服务状态为未发布
                for pro_service_id in pro_json:
                    is_published, rt_app = self.is_published(pro_service_id)
                    # 跳过已发布的服务
                    if is_published:
                        continue
                    service = service_map.get(pro_service_id)
                    app_service = app_service_map.get(pro_service_id)
                    app_service.dest_yb = False
                    app_service.dest_ys = False
                    app_service.save()
                    # 发送事件
                    if app_service.is_slug():
                        logger.debug("service group publish slug.")
                        self.upload_slug(app_service, service, share_pk)
                    elif app_service.is_image():
                        logger.debug("service group publish image.")
                        self.upload_image(app_service, service, share_pk)


            # if len(app_share_list) > 0:
            #     AppServiceShareInfo.objects.bulk_create(app_share_list)
        except Exception as e:
            logger.error("service group publish failed")
            data = {"success": False, "code": 500, 'msg': '系统异常!'}
            logger.exception(e)
        data = {"success": True, "code": 200, 'msg': '更新成功!'}
        return JsonResponse(data, status=200)

    def is_published(self,service_id):
        """
        根据service_id判断服务是否发布过
        :param service_id: 服务 ID
        :return: 是否发布, 发布的服务对象
        """
        result = True
        rt_app = None
        service = TenantServiceInfo.objects.get(service_region=self.response_region, service_id=service_id)
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
        logger.debug("service_id {0} service_key {1} app_service {2} app_alias {3}".format(service.service_id,service_key,app_version,app_alias))
        relation_list = TenantServiceRelation.objects.filter(service_id=service.service_id)
        dep_service_ids = [x.dep_service_id for x in list(relation_list)]
        if len(dep_service_ids) == 0:
            return None
        # 依赖服务的信息
        logger.debug("depended service are {}".format(dep_service_ids))

        try:
            dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_service_ids)
            app_relation_list = []
            if len(dep_service_list) > 0:
                for dep_service in dep_service_list:
                    dep_app_service = None
                    # 不为源码构建的应用
                    if dep_service.service_key != "application" and (dep_service.language is None):
                        dep_app_list = AppService.objects.filter(service_key=dep_service.service_key, app_version=dep_service.version).order_by("-ID")
                        if not dep_app_list:
                            dep_app_list = AppService.objects.filter(service_key=dep_service.service_key).order_by("-ID")
                            if dep_app_list:
                                dep_app_service = dep_app_list[0]
                            else:
                                dep_app_list = AppService.objects.filter(service_id=dep_service.service_id).order_by("-ID")
                        else:
                            dep_app_service = dep_app_list[0]
                    else:
                        dep_app_list = AppService.objects.filter(service_id=dep_service.service_id).order_by("-ID")
                        dep_app_service = dep_app_list[0]

                    if not dep_app_service:
                        return 404

                    # 检查是否存在对应的app_relation
                    relation_count = AppServiceRelation.objects.filter(service_key=service_key,
                                                                       app_version=app_version,
                                                                       dep_service_key=dep_app_service.service_key,
                                                                       dep_app_version=dep_app_service.app_version).count()
                    if relation_count == 0:
                        app_relation = AppServiceRelation(service_key=service_key,
                                                          app_version=app_version,
                                                          app_alias=app_alias,
                                                          dep_service_key=dep_app_service.service_key,
                                                          dep_app_version=dep_app_service.app_version,
                                                          dep_app_alias=dep_app_service.app_alias)
                        app_relation_list.append(app_relation)
                # 批量添加发布依赖
                if len(app_relation_list) > 0:
                    AppServiceRelation.objects.bulk_create(app_relation_list)
            else:
                # 依赖服务的实力已经被删除,理论上不存在这种情况
                return 400
        except Exception as e:
            logger.exception(e)
            logger.error(
                "add app relation error service_key {0},app_version {1},app_alias {2}".format(service_key, app_version,
                                                                                            app_alias))

    def _create_publish_event(self, service, info):
        try:
            import datetime
            event = ServiceEvent(event_id=make_uuid(), service_id=self.service.service_id,
                                 tenant_id=self.tenant.tenant_id, type="share-{0}".format(info),
                                 deploy_version=self.service.deploy_version,
                                 old_deploy_version=self.service.deploy_version,
                                 user_name=self.user.nick_name, start_time=datetime.datetime.now())
            event.save()
            self.event = event
            return event.event_id
        except Exception as e:
            self.event = None
            raise e

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
            logger.debug("=========> slug 云帮发布任务 !")
            regionClient.send_task(service.service_region, 'app_slug', json.dumps(oss_upload_task))
            if app.is_outer:
                event_id = self._create_publish_event(service, u"云市")
                oss_upload_task.update({"dest": "ys", "event_id": event_id})
                logger.debug("=========> slug 云市发布任务 !")
                regionClient.send_task(service.service_region, 'app_slug', json.dumps(oss_upload_task))
        except Exception as e:
            if self.event:
                self.event.message = u"生成发布事件错误，" + e.message
                self.event.final_status = "complete"
                self.event.status = "failure"
                self.event.save()
            logger.exception(e)
            raise e

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
            logger.debug("=========> image 云帮发布任务 !")
            regionClient.send_task(service.service_region, 'app_image', json.dumps(image_upload_task))
            if app.is_outer:
                event_id = self._create_publish_event(service, u"云市")
                image_upload_task.update({"dest": "ys", "event_id": event_id})
                logger.debug("=========> image 云市发布任务 !")
                regionClient.send_task(service.service_region, 'app_image', json.dumps(image_upload_task))
        except Exception as e:
            if self.event:
                self.event.message = u"生成发布事件错误，" + e.message
                self.event.final_status = "complete"
                self.event.status = "failure"
                self.event.save()
            logger.exception(e)
            raise e


class ServiceGroupShareFourView(LeftSideBarMixin,AuthedView):
    def get_context(self):
        context = super(ServiceGroupShareFourView, self).get_context()
        return context

    @perm_required('app_publish')
    def get(self, request, groupId, share_pk, *args, **kwargs):
        context = self.get_context()
        app_service_group = AppServiceGroup.objects.get(ID=share_pk)
        context["app_service_group"] = app_service_group
        context["group_id"] = groupId
        return TemplateResponse(request, 'www/service/groupShare_step_four.html', context)
