# -*- coding: utf8 -*-
import datetime
import json
import logging

from django.http import Http404, HttpResponse
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from share.manager.region_provier import RegionProviderManager
from www.apiclient.regionapi import RegionInvokeApi
from www.app_http import AppServiceApi
from www.decorator import perm_required
from www.models import (ServiceInfo, TenantServiceInfo, AppServiceRelation, AppServiceVolume, AppServiceGroup, PublishedGroupServiceRelation)
from www.models.main import ServiceGroup, GroupCreateTemp, TenantServiceVolume, ServiceEvent
from www.monitorservice.monitorhook import MonitorHook
from www.services import tenant_svc
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, \
    AppCreateService
from www.utils.crypt import make_uuid
from www.views import AuthedView, LeftSideBarMixin

logger = logging.getLogger('default')

region_api = RegionInvokeApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
appClient = AppServiceApi()
rpmManager = RegionProviderManager()
appCreateService = AppCreateService()


class GroupServiceDeployView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, *args, **kwargs):
        group_key = request.GET.get("group_key", None)
        group_version = request.GET.get("group_version", None)
        share_group_pk = request.GET.get("gid", None)
        region = request.GET.get("region", None)

        try:
            if share_group_pk:
                if not AppServiceGroup.objects.filter(pk=int(share_group_pk)).exists():
                    raise Http404

                context = self.get_context()
                context["createApp"] = "active"
                context["tenantName"] = self.tenantName
                response = self.redirect_to("/apps/{0}/group-deploy/{1}/step1/".format(self.tenantName, share_group_pk))
                if region:
                    response.set_cookie('region', region)
                return response

            if group_key is None:
                raise Http404
            context = self.get_context()
            app_groups = AppServiceGroup.objects.filter(group_share_id=group_key, group_version=group_version).order_by(
                "-update_time")
            if len(app_groups) > 1:
                logger.error("group for group_key:{0} and group_version:{1} is more than one ! ".format(group_key,
                                                                                                        group_version))
                share_group_pk = app_groups[0].ID
            elif len(app_groups) == 0:
                app_groups = AppServiceGroup.objects.filter(group_share_id=group_key).order_by("-update_time")
                if len(app_groups) == 0:
                    code, group_info, msg = baseService.download_group_info(group_key, group_version, None)
                    if not group_info:
                        raise Http404
                    else:
                        share_group_pk = group_info.ID
                else:
                    share_group_pk = app_groups[0].ID
            else:
                logger.debug("install group apps! group_key {0} group_version {1}".format(group_key, group_version))
                share_group_pk = app_groups[0].ID

            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
        except Http404 as e_404:
            logger.exception(e_404)
            return HttpResponse("<html><body>Group Service Not Found !</body></html>")
        except Exception as e:
            logger.exception(e)
        return self.redirect_to("/apps/{0}/group-deploy/{1}/step1/".format(self.tenantName, share_group_pk))


class GroupServiceDeployStep1(LeftSideBarMixin, AuthedView):
    """组应用创建第一步,填写组信息"""

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, groupId, *args, **kwargs):

        context = self.get_context()
        try:
            # 根据key 和 version获取应用组名
            groupId = int(groupId)
            group = AppServiceGroup.objects.get(ID=groupId)
            context["group"] = group
            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/group/group_app_create_step_1.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, groupId, *args, **kwargs):
        data = {}
        # 获取应用组的group_share_id 和 version
        service_group_id = request.POST.get("select_group_id", None)
        try:
            service_group_id = int(service_group_id)
            if service_group_id != -3:
                service_group = None
                if service_group_id != "":
                    group_id = int(service_group_id)
                    if group_id > 0:
                        service_group = ServiceGroup.objects.get(ID=group_id, tenant_id=self.tenant.tenant_id,
                                                                 region_name=self.response_region)
                if not service_group:
                    return JsonResponse({"success": False, "info": u"请选择服务所在组"}, status=200)
                else:
                    group_id = service_group.ID
            else:
                group_name = request.POST.get("group_name")

                sg = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                                    group_name=group_name)
                if not sg:
                    # 创建组
                    group = ServiceGroup.objects.create(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                                        group_name=group_name)
                    group_id = group.ID
                else:
                    group = sg[0]
                    group_id = group.ID

            next_url = "/apps/{0}/group-deploy/{1}/step2/?group_id={2}".format(self.tenantName, groupId, group_id)
            data.update({"success": True, "info": "create group success!", "next_url": next_url})

        except Exception as e:
            data.update({"success": False, "info": "创建失败"})
            logger.exception(e)
        return JsonResponse(data, status=200)


class GroupServiceDeployStep2(LeftSideBarMixin, AuthedView):
    """组应用创建第二步,应用内存信息"""

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    # 判断资源是否超出限制
    def preprocess(self, services):
        need_create_service = []
        is_pass = True
        data = {}
        ts_list = []
        for ts in services:
            service_key = ts.get("service_key")
            service_version = ts.get("service_version")
            service_name = ts.get("service_name")
            if not service_name:
                data["status"] = "failure"
                is_pass = False
                return need_create_service, is_pass, data
            service_model_list = ServiceInfo.objects.filter(service_key=service_key, version=service_version)
            if not service_model_list:
                data["status"] = "notexist"
                is_pass = False
                return need_create_service, is_pass, data
            service = service_model_list[0]
            temp_ts = TenantServiceInfo()
            temp_ts.min_memory = service.min_memory
            temp_ts.min_node = service.min_node
            ts_list.append(temp_ts)
        res = tenantUsedResource.predict_batch_services_memory(self.tenant, ts_list, self.response_region)
        if not res:
            data["status"] = "over_memory"
            data["tenant_type"] = self.tenant.pay_type
            is_pass = False
            return need_create_service, is_pass, data

        for s in services:
            service_key = s.get("service_key")
            service_version = s.get("service_version")
            service_name = s.get("service_name")
            if not service_name:
                data["status"] = "failure"
                is_pass = False
                return need_create_service, is_pass, data
            service_model_list = ServiceInfo.objects.filter(service_key=service_key, version=service_version)
            if not service_model_list:
                data["status"] = "notexist"
                is_pass = False
                return need_create_service, is_pass, data
            service = service_model_list[0]

            # calculate resource
            tempService = TenantServiceInfo()
            tempService.min_memory = service.min_memory
            tempService.service_region = self.response_region
            tempService.min_node = service.min_node
            diffMemory = service.min_memory * service.min_node
            rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, tempService, diffMemory, False)
            if not flag:
                if rt_type == "memory":
                    data["status"] = "over_memory"
                    data["tenant_type"] = self.tenant.pay_type
                else:
                    data["status"] = "over_money"
                is_pass = False
                return need_create_service, is_pass, data

            ccpu = int(service.min_memory / 128) * 20
            service.min_cpu = ccpu
            service.service_cname = service_name
            need_create_service.append(service)
            data["status"] = "success"
        return need_create_service, is_pass, data

    def get_published_service_info(self, groupId):
        result = []
        pgsr_list = PublishedGroupServiceRelation.objects.filter(group_pk=groupId)
        for pgsr in pgsr_list:
            apps = ServiceInfo.objects.filter(service_key=pgsr.service_key, version=pgsr.version).order_by("-ID")
            if apps:
                result.append(apps[0])
            else:
                code, base_info, dep_map, error_msg = baseService.download_service_info(pgsr.service_key, pgsr.version)
                if code == 500:
                    logger.error(error_msg)
                    return []
                else:
                    apps = ServiceInfo.objects.filter(service_key=pgsr.service_key, version=pgsr.version).order_by(
                        "-ID")
                    if apps:
                        result.append(apps[0])
                    else:
                        apps = ServiceInfo.objects.filter(service_key=pgsr.service_key).order_by("-ID")
                        if apps:
                            result.append(apps[0])
        return result

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, groupId, *args, **kwargs):
        context = self.get_context()
        try:
            # 新创建的组ID
            group_id = request.GET.get("group_id")
            service_group = ServiceGroup.objects.filter(pk=group_id)
            if not service_group:
                raise Http404
            context["group_id"] = group_id

            app_service_list = self.get_published_service_info(groupId)
            published_service_list = []
            for app_service in app_service_list:
                logger.debug("app_service info:" + app_service.service_key + "  -  " + app_service.version)
                services = ServiceInfo.objects.filter(service_key=app_service.service_key, version=app_service.version)
                services = list(services)
                # 没有服务模板,需要下载模板
                if len(services) == 0:
                    code, base_info, dep_map, error_msg = baseService.download_service_info(app_service.service_key,
                                                                                            app_service.version)
                    if code == 500:
                        logger.error(error_msg)
                    else:
                        services.append(base_info)
                if len(services) > 0:
                    published_service_list.append(services[0])
                else:
                    logger.error(
                        "service_key {0} version {1} is not found in table service or can be download from market".format(
                            app_service.service_key, app_service.version))
            # 发布的应用有不全的信息
            if len(published_service_list) != len(app_service_list):
                logger.debug("published_service_list ===== {0}".format(len(published_service_list)))
                logger.debug("service_id_list ===== {}".format(len(app_service_list)))
                logger.error("publised service is not found in table service")
                context["success"] = False
                return TemplateResponse(self.request, "www/group/group_app_create_step_2.html", context)

            context["service_list"] = published_service_list
            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
            context["success"] = True
            context["shared_group_id"] = groupId
            context["group_id"] = group_id
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/group/group_app_create_step_2.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, groupId, *args, **kwargs):
        data = {}
        tenant_id = self.tenant.tenant_id
        try:
            service_group_id = request.POST.get("service_group_id", None)
            services_json = request.POST.get("services")
            services = json.loads(services_json)
            success = tenant_svc.init_for_region(self.response_region, self.tenantName, self.tenant.tenant_id,
                                                          self.user)
            if not success:
                data["status"] = "failure"
                return JsonResponse(data, status=200)
            need_create_service, is_pass, result = self.preprocess(services)
            logger.debug("need_create_service: {}".format(need_create_service))
            if not is_pass:
                return JsonResponse(result, status=200)
            is_success = True

            GroupCreateTemp.objects.filter(share_group_id=groupId).delete()
            for ncs in need_create_service:
                service_id = make_uuid(tenant_id)
                service_cname = ncs.service_cname
                try:
                    temp_data = {}
                    temp_data["tenant_id"] = tenant_id
                    temp_data["service_id"] = service_id
                    temp_data["service_key"] = ncs.service_key
                    temp_data["service_cname"] = service_cname
                    temp_data["share_group_id"] = groupId
                    temp_data["service_group_id"] = service_group_id
                    GroupCreateTemp.objects.create(**temp_data)
                except Exception as ex:
                    logger.exception(ex)
                    GroupCreateTemp.objects.filter(share_group_id=groupId).delete()
                    is_success = False
            if is_success:
                next_url = "/apps/{0}/group-deploy/{1}/step3/?group_id={2}".format(self.tenantName, groupId,
                                                                                   service_group_id)
                data.update({"success": True, "status": "success", "next_url": next_url})
            else:
                data.update({"success": False, "status": "failure"})

        except Exception as e:
            data.update({"success": False, "code": 500})
            logger.exception(e)

        return JsonResponse(data, status=200)


class GroupServiceDeployStep3(LeftSideBarMixin, AuthedView):
    """组应用创建第三步,应用相关设置"""

    def get_media(self):
        media = super(AuthedView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css', 'www/css/owl.carousel.css',
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js')
        return media

    def sort_service(self, publish_service_list):
        service_map = {s.service_key: s for s in publish_service_list}
        result = []
        key_app_map = {}
        for app in publish_service_list:
            dep_services = AppServiceRelation.objects.filter(service_key=app.service_key, app_version=app.version)
            if dep_services:
                key_app_map[app.service_key] = [ds.dep_service_key for ds in dep_services]
            else:
                key_app_map[app.service_key] = []
        logger.debug(" service_map:{} ".format(service_map))
        service_keys = self.topological_sort(key_app_map)

        for key in service_keys:
            result.append(service_map.get(key))
        return result

    def topological_sort(self, graph):
        is_visit = dict((node, False) for node in graph)
        li = []

        def dfs(graph, start_node):

            for end_node in graph[start_node]:
                if not is_visit[end_node]:
                    is_visit[end_node] = True
                    dfs(graph, end_node)
            li.append(start_node)

        for start_node in graph:
            if not is_visit[start_node]:
                is_visit[start_node] = True
                dfs(graph, start_node)
        return li

    def create_dep_service(self, service_info, service, service_group_id):
        app_relations = AppServiceRelation.objects.filter(service_key=service_info.service_key,
                                                          app_version=service_info.version)
        dep_service_ids = []
        if app_relations:
            for dep_app in app_relations:
                temp = GroupCreateTemp.objects.get(service_key=dep_app.dep_service_key, tenant_id=self.tenant.tenant_id,
                                                   service_group_id=service_group_id)
                dep_service_ids.append(temp.service_id)

        for dep_id in dep_service_ids:
            baseService.create_service_dependency(self.tenant, service, dep_id, self.response_region)
        logger.info("create service info for service_id{0} ".format(service.service_id))

    def get_published_service_info(self, groupId):
        result = []
        pgsr_list = PublishedGroupServiceRelation.objects.filter(group_pk=groupId)
        for pgsr in pgsr_list:
            apps = ServiceInfo.objects.filter(service_key=pgsr.service_key, version=pgsr.version).order_by("-ID")
            if apps:
                result.append(apps[0])
            else:
                code, base_info, dep_map, error_msg = baseService.download_service_info(pgsr.service_key, pgsr.version)
                if code == 500:
                    logger.error(error_msg)
                    return []
                else:
                    apps = ServiceInfo.objects.filter(service_key=pgsr.service_key, version=pgsr.version).order_by(
                        "-ID")
                    if apps:
                        result.append(apps[0])
                    else:
                        apps = ServiceInfo.objects.filter(service_key=pgsr.service_key).order_by("-ID")
                        if apps:
                            result.append(apps[0])
        return result

    def create_service_event(self, service, tenant, action):
        event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                             tenant_id=tenant.tenant_id, type="{0}".format(action),
                             deploy_version=service.deploy_version,
                             old_deploy_version=service.deploy_version,
                             user_name=self.user.nick_name, start_time=datetime.datetime.now())
        event.save()
        return event

    def copy_volumes(self, source_service, tenant_service):
        volumes = AppServiceVolume.objects.filter(service_key=source_service.service_key,
                                                  app_version=source_service.version)
        for volume in volumes:
            baseService.add_volume_with_type(tenant_service, volume.volume_path, TenantServiceVolume.SHARE,
                                             make_uuid()[:7])

        if tenant_service.volume_mount_path:
            if not volumes.filter(volume_path=tenant_service.volume_mount_path).exists():
                baseService.add_volume_with_type(tenant_service, tenant_service.volume_mount_path,
                                                 TenantServiceVolume.SHARE, make_uuid()[:7])
