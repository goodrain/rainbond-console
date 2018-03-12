# -*- coding: utf8 -*-
import datetime
import json
import logging

import os

from django.conf import settings
from django.http.response import JsonResponse
from django.template.response import TemplateResponse

from api.back_service_install import BackServiceInstall
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.models import AppServiceShareInfo, ServiceGroup, TenantServiceInfo, AppServiceGroup
from www.models import ServiceEvent
from www.services import tenant_svc, enterprise_svc, app_group_svc, publish_app_svc
from www.utils.crypt import make_uuid
from www.views import AuthedView, LeftSideBarMixin
from www.utils import sn
from www.utils.crypt import make_uuid
from www.views import AuthedView, LeftSideBarMixin


logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class ServiceGroupSharePreview(LeftSideBarMixin, AuthedView):
    """ 服务组发布 """

    def get_context(self):
        context = super(ServiceGroupSharePreview, self).get_context()
        return context

    # form提交.
    @perm_required('share_service')
    def post(self, request, groupId, *args, **kwargs):
        try:
            # groupId 为服务所在组的ID
            groupId = int(groupId)
            if groupId < 1:
                data = {"success": False, "code": 406, 'msg': '未分组应用不可分享'}
                return JsonResponse(data, status=200)
            group = tenant_svc.get_tenant_group_on_region_by_id(self.tenant, groupId, self.response_region)
            if not group:
                return JsonResponse({"success": False, "code": 404, 'msg': u"组不存在"}, status=200)
            service_list = tenant_svc.list_tenant_group_service(self.tenant, group)

            # appcation 类型的应用和 app_publish类型且language不为None(即image和compose类型)的服务
            can_publish_list = [x for x in service_list if
                                x.category == "application" or (
                                        x.category == "app_publish" and x.language is not None)]

            if not can_publish_list:
                data = {"success": False, "code": 406, 'msg': '此组中的应用全部来源于云市,无法发布'}
                return JsonResponse(data, status=200)
            # 判断非云市安装应用是否全部运行中
            for s in can_publish_list:
                body = region_api.check_service_status(s.service_region, self.tenantName, s.service_alias,
                                                       self.tenant.enterprise_id)
                status = body["bean"]["cur_status"]
                if status != "running":
                    data = {"success": False, "code": 412, 'msg': '您的应用{0}未运行。'.format(s.service_cname)}
                    return JsonResponse(data, status=200)
            next_url = "/apps/{0}/{1}/first/".format(self.tenantName, groupId)
            data = {"success": False, "code": 200, 'next_url': next_url}
            return JsonResponse(data, status=200)

        except Exception as e:
            logger.exception("group.publish", e)


class ServiceGroupShareOneView(LeftSideBarMixin, AuthedView):
    """服务组发布，设置服务名称"""

    def get_context(self):
        context = super(ServiceGroupShareOneView, self).get_context()
        return context

    @perm_required('share_service')
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
            # 获取企业激活状态
            enterprise = enterprise_svc.get_enterprise_by_tenant(self.tenant)
            if enterprise.is_active:
                is_enterprise_active = 1
            else:
                is_enterprise_active = 0
            context.update({"is_enterprise_active": is_enterprise_active})
            context.update({"enterprise_id": enterprise.enterprise_id})

        except Exception as e:
            logger.error("group.publish", e)
        return TemplateResponse(request,
                                'www/service/groupShare_step_one.html',
                                context)

    @perm_required('share_service')
    def post(self, request, groupId, *args, **kwargs):
        logger.debug("group.publish", "service group publish:{0}".format(groupId))
        try:
            service_share_alias = request.POST.get("alias", None)
            publish_type = request.POST.get("publish_type", None)
            group_version = request.POST.get("group_version", "0.0.1")
            desc = request.POST.get("desc", None)
            is_market = request.POST.get("is_market", True)
            installable = request.POST.get("installable", True)
            share_scope = request.POST.get("share_scope", "market")

            logger.debug("params: service_share_alias {0} ,publish_type {1},group_version {2},desc {3}, is_market {4} ,"
                         "installable {5}, share_scope{6}".format(service_share_alias, publish_type, group_version,
                                                                  desc, is_market, installable, share_scope))

            service_list = tenant_svc.list_tenant_group_service_by_group_id(self.tenant,
                                                                            self.response_region,
                                                                            groupId)

            service_id_list = [x.service_id for x in service_list]
            service_ids = ",".join(service_id_list)
            # application 类型的应用和 app_publish类型且language不为None(即image和compose类型)的服务
            can_publish_list = [x for x in service_list if
                                x.category == "application" or (x.category == "app_publish" and x.language is not None)]
            now = datetime.datetime.now()
            # 不同版本的发布可以有多个版本的应用组存在
            app_service_group = app_group_svc.get_app_group_by_id(groupId)
            enterprise = enterprise_svc.get_enterprise_by_tenant(self.tenant)
            fields_dict = {"group_share_alias": service_share_alias, "service_ids": service_ids,
                           "step": len(can_publish_list), "publish_type": publish_type,
                           "group_version": group_version, "desc": desc, "is_market": is_market,
                           "installable": installable, "group_id": groupId,
                           "share_scope": share_scope, "enterprise_id": enterprise.ID, "is_publish_to_market": False}
            """
             1.首先判断应用是否发布过应用组，发布过就进而通过 group_share_id 和group_version获取信息。如果
             没有，说明应用组的版本有更新，需要重新创建；如果有，说明是重复发布，将原有信息替换掉。需求中，服务组可以重复
             发布，而且可以存在多个版本的应用组
            """
            if app_service_group:
                group_share_id = app_service_group.group_share_id
                group_service = app_group_svc.get_app_service_group_by_unique(group_share_id, group_version)
                if group_service:
                    # update app_group_service
                    group_service = app_group_svc.update_app_group_service(group_service, **fields_dict)
                else:
                    # create app_group_service
                    fields_dict.update({"is_success": False, "group_share_id": group_share_id})
                    group_service = app_group_svc.create_app_group_service(**fields_dict)
            else:
                group_share_id = make_uuid(service_ids)
                fields_dict.update({"is_success": False, "group_share_id": group_share_id})
                group_service = app_group_svc.create_app_group_service(**fields_dict)

            share_pk = group_service.ID

        except Exception as e:
            logger.error("group.publish", e)
            data = {"success": False, "code": 500, 'msg': '系统异常!'}
            return JsonResponse(data, status=200)
        next_url = "/apps/{0}/{1}/{2}/second/".format(self.tenantName, groupId, share_pk)
        data = {"success": True, "code": 200, 'msg': '更新成功!', 'next_url': next_url}
        return JsonResponse(data, status=200)


class ServiceGroupShareTwoView(LeftSideBarMixin, AuthedView):
    """ 服务参数配置页面 """

    def get_context(self):
        context = super(ServiceGroupShareTwoView, self).get_context()
        return context

    @perm_required('share_service')
    def get(self, request, groupId, share_pk, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        try:
            service_list = tenant_svc.list_tenant_group_service_by_group_id(self.tenant,
                                                                            self.response_region,
                                                                            groupId)
            array_ids = [x.service_id for x in service_list]
            # 查询服务端口信息
            service_port_map = publish_app_svc.get_service_ports_by_ids(array_ids)
            # 查询服务依赖
            dep_service_map = publish_app_svc.get_service_dependencys_by_ids(array_ids)
            # 查询服务可变参数和不可变参数
            service_env_change_map, service_env_nochange_map = publish_app_svc.get_service_env_by_ids(array_ids)
            # 查询服务持久化信息
            service_volume_map = publish_app_svc.get_service_volume_by_ids(array_ids)

            context.update({"service_list": service_list,
                            "port_map": service_port_map,
                            "relation_info_map": dep_service_map,
                            "env_change_map": service_env_change_map,
                            "env_nochange_map": service_env_nochange_map,
                            "volume_map": service_volume_map,
                            "tenant_name": self.tenantName,
                            "group_id": groupId,
                            "share_id": share_pk})
        except Exception as e:
            logger.exception("group.publish", e)
        return TemplateResponse(request,
                                'www/service/groupShare_step_two.html',
                                context)

    # form提交
    @perm_required('share_service')
    def post(self, request, groupId, share_pk, *args, **kwargs):
        logger.debug("group.publish", "service group publish: {0}-{1}".format(groupId, share_pk))
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
            logger.exception("group.publish", e)
            data = {"success": False, "code": 500, 'msg': '更新失败'}
        return JsonResponse(data, status=200)


class ServiceGroupShareThreeView(LeftSideBarMixin, AuthedView):
    """ 服务基本信息配置页面 """

    def get_context(self):
        context = super(ServiceGroupShareThreeView, self).get_context()
        return context

    @perm_required('share_service')
    def get(self, request, groupId, share_pk, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        try:
            # 查询服务信息
            service_list = tenant_svc.list_tenant_group_service_by_group_id(self.tenant,
                                                                            self.response_region,
                                                                            groupId)
            array_ids = [x.service_id for x in service_list]

            # 查询是否已经发布过
            app_service_list = publish_app_svc.get_app_service_by_ids(array_ids)
            app_service_map = {x.service_id: x for x in app_service_list}
            has_published_map = {}
            for app in service_list:
                # 非自研应用取出应用已发布的信息
                if app.category == "app_publish" and app.language is None:
                    has_pubilshed = publish_app_svc.get_app_service_by_unique(app.service_key, app.version)
                    if has_pubilshed:
                        has_published_map[app.service_id] = has_pubilshed
            context.update({"service_list": service_list,
                            "app_service_map": app_service_map})

            context.update({"tenant_name": self.tenantName,
                            "group_id": groupId,
                            "share_id": share_pk})
            context.update({"has_published_map": has_published_map})
        except Exception as e:
            logger.error("group.publish", e)
        return TemplateResponse(request,
                                'www/service/groupShare_step_three.html',
                                context)

    # form提交
    @perm_required('share_service')
    def post(self, request, groupId, share_pk, *args, **kwargs):
        logger.debug("group.publish", "service group publish: {0}-{1}".format(groupId, share_pk))

        pro_data = request.POST.get("pro_data", None)
        service_ids = request.POST.get("service_ids", "[]")
        try:
            if pro_data:
                service_ids = json.loads(service_ids)
                service_list = TenantServiceInfo.objects.filter(service_id__in=service_ids)
                service_map = {x.service_id: x for x in service_list}
                pro_json = json.loads(pro_data)

                app_service_map = {}
                app_service_group = app_group_svc.get_app_group_by_pk(share_pk)
                step = 0
                for pro_service_id in pro_json:
                    is_published, app = publish_app_svc.is_published(pro_service_id, self.response_region)
                    # 已发布的应用,缓存app_service_map,并跳过此次循环
                    if is_published:
                        app_service_map[pro_service_id] = app
                        continue
                    pro_map = pro_json.get(pro_service_id)

                    app_alias = pro_map.get("name")
                    app_version = pro_map.get("version")
                    app_content = pro_map.get("content")
                    is_init = pro_map.get("is_init") == 1
                    is_outer = app_service_group.share_scope == "market"
                    is_private = app_service_group.share_scope == "company"
                    # 云帮不显示
                    show_assistant = False
                    show_cloud = app_service_group.share_scope == "market"

                    # 添加app_service记录
                    service = service_map.get(pro_service_id)
                    app_service = publish_app_svc.add_app_service(service, self.user, app_alias, app_version,
                                                                  app_content, is_init, is_outer,
                                                                  is_private, show_assistant, show_cloud)
                    app_service_map[pro_service_id] = app_service
                    # 保存service_port
                    port_list = publish_app_svc.add_app_port(service, app_service.service_key, app_version)
                    # 保存env
                    publish_app_svc.add_app_env(service, app_service.service_key, app_version, port_list)
                    # 保存extend_info
                    publish_app_svc.add_app_extend_info(service, app_service.service_key, app_version)
                    # 保存持久化设置
                    publish_app_svc.add_app_volume(service, app_service.service_key, app_version)
                    # 设置需要发布的步数
                    step += 1
                app_service_group.step = step
                app_service_group.save()
                logger.debug("group.publish", "step ===> {}".format(step))
                # 处理服务依赖关系
                for pro_service_id in pro_json:
                    # 服务依赖关系
                    service = service_map.get(pro_service_id)
                    app_service = app_service_map.get(pro_service_id)
                    result = publish_app_svc.add_app_relation(service, app_service.service_key, app_service.app_version,
                                                              app_service.app_alias)
                    logger.debug("group.publish",
                                 u'group.share.service. now add group share service relation for service {0} ok'.format(
                                     service.service_id), result)
                # 服务和组的关系，先删除，后创建
                publish_app_svc.delete_group_service_relation_by_group_pk(app_service_group.ID)
                publish_app_svc.update_or_create_group_service_relation(app_service_map, app_service_group)

                # 设置所有发布服务状态为未发布
                for pro_service_id in pro_json:
                    is_published, rt_app = publish_app_svc.is_published(pro_service_id, self.response_region)
                    # 跳过已发布的服务
                    if is_published:
                        continue
                    service = service_map.get(pro_service_id)
                    app_service = app_service_map.get(pro_service_id)
                    app_service.dest_yb = False  # 云帮未发布成功
                    app_service.dest_ys = False  # 云市未发布成功
                    app_service.save()
                    # 发送事件
                    if app_service.is_slug():
                        logger.debug("group.publish", "service group publish slug.")
                        self.upload_slug(app_service, service, share_pk)
                    elif app_service.is_image():
                        logger.debug("group.publish", "service group publish image.")
                        self.upload_image(app_service, service, share_pk)

            data = {"success": True, "code": 200, 'msg': '更新成功!'}
        except Exception as e:
            logger.error("group.publish", "service group publish failed")
            data = {"success": False, "code": 500, 'msg': '系统异常!'}
            logger.exception("group.publish", e)

        return JsonResponse(data, status=200)

    def _create_publish_event(self, service, info):
        try:
            import datetime
            event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                                 tenant_id=self.tenant.tenant_id, type="share-{0}".format(info),
                                 deploy_version=service.deploy_version,
                                 old_deploy_version=service.deploy_version,
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
            event_id = self._create_publish_event(service, 'yb')
            oss_upload_task.update({"dest": "yb", "event_id": event_id})
            body = {}
            body["kind"] = "app_slug"
            tenant_region = tenant_svc.get_tenant_region_info(self.tenant, service.service_region)
            oss_upload_task["tenant_id"] = tenant_region.region_tenant_id
            body["slug"] = oss_upload_task
            body["enterprise_id"] = self.tenant.enterprise_id
            logger.debug("group.publish", u"=========> slug 云帮发布任务 !")
            region_api.share_clound_service(self.response_region, self.tenant.tenant_name, body)

            if app.is_outer:
                event_id = self._create_publish_event(service, "ys")
                oss_upload_task.update({"dest": "ys", "event_id": event_id})
                body["slug"] = oss_upload_task
                logger.debug("group.publish", u"=========> slug 云市发布任务 !")
                region_api.share_clound_service(self.response_region, self.tenant.tenant_name, body)
        except Exception as e:
            if self.event:
                self.event.message = u"生成发布事件错误，{0}".format(e)
                self.event.final_status = "complete"
                self.event.status = "failure"
                self.event.save()
            logger.exception("group.publish", e)
            raise e

    def upload_image(self, app, service, share_id):
        """ 上传image镜像 """
        image_upload_task = {
            "service_key": app.service_key,
            "app_version": app.app_version,
            "action": "create_new_version",
            "image": service.image,
            "service_id": service.service_id,
            "is_outer": app.is_outer,
            "share_id": share_id,
        }
        try:
            body = {}
            event_id = self._create_publish_event(service, "yb")
            image_upload_task.update({"dest": "yb", "event_id": event_id})
            body["kind"] = "app_image"
            body["image"] = image_upload_task
            body["enterprise_id"] = self.tenant.enterprise_id
            logger.debug("group.publish", u"=========> image 云帮发布任务 !")
            # regionClient.send_task(service.service_region, 'app_image', json.dumps(image_upload_task))
            region_api.share_clound_service(self.response_region, self.tenant.tenant_name, body)
            if app.is_outer:
                event_id = self._create_publish_event(service, "ys")
                image_upload_task.update({"dest": "ys", "event_id": event_id})
                body["image"] = image_upload_task
                logger.debug("group.publish", u"=========> image 云市发布任务 !")
                # regionClient.send_task(service.service_region, 'app_image', json.dumps(image_upload_task))
                region_api.share_clound_service(self.response_region, self.tenant.tenant_name, body)
        except Exception as e:
            if self.event:
                self.event.message = u"生成发布事件错误，{0}".format(e)
                self.event.final_status = "complete"
                self.event.status = "failure"
                self.event.save()
            logger.exception("group.publish", e)
            raise e


class ServiceGroupShareFourView(LeftSideBarMixin, AuthedView):
    def get_context(self):
        context = super(ServiceGroupShareFourView, self).get_context()
        return context

    @perm_required('share_service')
    def get(self, request, groupId, share_pk, *args, **kwargs):
        context = self.get_context()
        service_list = tenant_svc.list_tenant_group_service_by_group_id(self.tenant,
                                                                        self.response_region,
                                                                        groupId)
        need_published_service = []
        no_need_publishe_service = []
        for service in service_list:
            if service.category == "application" or (
                    service.category == "app_publish" and service.language is not None):
                need_published_service.append(service)
            else:
                no_need_publishe_service.append(service)

        app_service_group = AppServiceGroup.objects.get(ID=share_pk)

        apps = publish_app_svc.list_published_group_app_services(share_pk)
        service_id_app_map = {app.service_id: app for app in apps}

        context.update({"tenant_name": self.tenant.tenant_name,
                        "group_id": groupId,
                        "share_id": share_pk,
                        "service_id_app_map": service_id_app_map,
                        "need_published_service": need_published_service,
                        "no_need_publishe_service": no_need_publishe_service,
                        "app_service_group": app_service_group,
                        "eid": self.tenant.enterprise_id
                        })

        return TemplateResponse(request, 'www/service/groupShare_step_four.html', context)

    @perm_required('share_service')
    def post(self, request, groupId, share_pk, *args, **kwargs):
        apps = request.POST.dict().get("apps")
        apps = json.loads(apps)
        all_success = True
        app_list = []
        app_service_group = app_group_svc.get_app_group_by_pk(share_pk)
        if not app_service_group:
            return JsonResponse({"success": False, "msg": "应用组不存在"})
        try:
            for app in apps:
                data = {}
                res, body = region_api.get_service_publish_status(self.response_region, self.tenantName, app["app_key"],
                                                                  app["app_version"])
                logger.debug(res, body)

                bean = body["bean"]
                status = bean["Status"]
                if status == "failure" or status == "pushing":
                    all_success = False
                elif status == "success":
                    # 单个应用发布成功更新数据
                    publish_app_svc.upate_app_service_by_key_and_version(app["app_key"], app["app_version"], bean)
                data["id"] = str(app["app_key"]) + "_" + str(app["app_version"])
                data["app_key"] = app["app_key"]
                data["app_version"] = app["app_version"]
                data["status"] = status
                app_list.append(data)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"success": False, "msg": "系统异常"})

        result = {"app_list": app_list, "all_success": all_success}

        return JsonResponse({"success": True, "msg": "成功", "data": result})


class ServiceGroupShareToMarketView(LeftSideBarMixin, AuthedView):

    @perm_required('share_service')
    def post(self, request, groupId, share_pk, *args, **kwargs):
        try:
            app_service_group = app_group_svc.get_app_group_by_pk(share_pk)
            if not app_service_group:
                return JsonResponse({"success": False, "msg": "应用组不存在"})

            # 所有需要发布的应用发布成功，更新发布的组应用信息
            app_service_group.is_success = True
            app_service_group.save()
            logger.debug("----------------> {0} ------ {1}".format(app_service_group.share_scope,
                                                                   app_service_group.is_publish_to_market))
            # 判断是否发布到云市，如果发布到云市，就调用接口将数据发布出去
            if app_service_group.share_scope == "market" and (not app_service_group.is_publish_to_market):
                logger.debug("send message to app market !")
                param_data = {}
                url_map = {}
                logger.debug("+=========+ {0}".format("start to push data to market !"))
                publish_app_svc.send_group_service_data_to_market(app_service_group, self.tenant, self.response_region,
                                                                  groupId, param_data, url_map)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"success": False, "msg": "推送信息至云市失败"})

        return JsonResponse({"success": True, "msg": "成功"})
