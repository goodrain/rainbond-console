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
from www.models import (ServiceInfo, TenantServiceInfo, TenantServiceAuth, TenantServiceRelation,
                        AppServicePort, AppServiceEnv, AppServiceRelation, AppServiceVolume, ServiceGroupRelation,
                        AppServiceGroup,
                        PublishedGroupServiceRelation, TenantServiceInfoDelete)
from www.models.main import ServiceGroup, GroupCreateTemp, TenantServiceEnvVar, \
    TenantServicesPort, TenantServiceVolume, ServiceDomain, ServiceEvent
from www.monitorservice.monitorhook import MonitorHook
from www.region import RegionInfo
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

    def set_direct_copy_options(self, envs, service_id, service_key, version):
        outer_ports = AppServicePort.objects.filter(service_key=service_key,
                                                    app_version=version,
                                                    is_outer_service=True,
                                                    protocol='http')
        service_alias = "gr" + service_id[-6:]
        for env in envs:
            if env.attr_name == 'SITE_URL' or env.attr_name == 'TRUSTED_DOMAIN':
                if self.cookie_region in RegionInfo.valid_regions():
                    env.options = 'direct_copy'
                    if len(outer_ports) > 0:
                        port = RegionInfo.region_port(self.response_region)
                        domain = RegionInfo.region_domain(self.response_region)
                        if env.attr_name == 'SITE_URL':
                            env.attr_value = 'http://{}.{}.{}{}:{}'.format(outer_ports[0].container_port, service_alias,
                                                                           self.tenantName, domain, port)
                        else:
                            env.attr_value = '{}.{}.{}{}:{}'.format(outer_ports[0].container_port, service_alias,
                                                                    self.tenantName, domain, port)

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, groupId, *args, **kwargs):
        tenant_id = self.tenant.tenant_id
        context = self.get_context()
        try:
            group_id = request.GET.get("group_id")
            if not ServiceGroup.objects.filter(ID=group_id).exists():
                raise Http404

            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
            temp_list = GroupCreateTemp.objects.filter(share_group_id=groupId, tenant_id=tenant_id,
                                                       service_group_id=group_id)
            if len(temp_list) == 0:
                return self.redirect_to("/apps/{0}/group-deploy/{1}/step1/".format(self.tenantName, groupId))
            service_cname_map = {tmp.service_key: tmp.service_cname for tmp in temp_list}
            logger.debug("service_cname_map:{}".format(service_cname_map))
            context["service_cname_map"] = service_cname_map

            shared_group = AppServiceGroup.objects.get(ID=groupId)
            # 查询分享组中的服务ID
            app_service_list = self.get_published_service_info(groupId)
            app_port_map = {}
            app_relation_map = {}
            app_env_map = {}
            app_volumn_map = {}
            app_min_memory_map = {}
            for app in app_service_list:
                # 端口
                port_list = AppServicePort.objects.filter(service_key=app.service_key, app_version=app.version)
                app_port_map[app.service_key] = list(port_list)
                # 环境变量
                env_list = AppServiceEnv.objects.filter(service_key=app.service_key, app_version=app.version,
                                                        container_port=0, is_change=True)
                gct_list = GroupCreateTemp.objects.filter(service_key=app.service_key, tenant_id=self.tenant.tenant_id,
                                                          service_group_id=group_id)
                if gct_list:
                    service_id = gct_list[0].service_id
                else:
                    service_id = None
                self.set_direct_copy_options(env_list, service_id, app.service_key, app.version)
                app_env_map[app.service_key] = list(env_list)
                # 持久化路径
                volumn_list = AppServiceVolume.objects.filter(service_key=app.service_key, app_version=app.version)
                app_volumn_map[app.service_key] = list(volumn_list)
                # 依赖关系
                dep_list = AppServiceRelation.objects.filter(service_key=app.service_key, app_version=app.version)
                app_relation_map[app.service_key] = list(dep_list)
                app_min_memory_map[app.service_key] = app.min_memory
            context["app_port_map"] = app_port_map
            context["app_relation_map"] = app_relation_map
            context["app_env_map"] = app_env_map
            context["app_volumn_map"] = app_volumn_map
            context["service_list"] = app_service_list
            context["group_id"] = group_id
            context["shared_group_id"] = groupId
            context["tenantName"] = self.tenantName
            context["app_min_memory_map"] = app_min_memory_map

        except Http404 as e_404:
            logger.exception(e_404)
            return HttpResponse("<html><body>Group Not Found !</body></html>")
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/group/group_app_create_step_3.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, groupId, *args, **kwargs):
        tenant_id = self.tenant.tenant_id
        context = self.get_context()
        data = {}
        current_service_ids = []
        sorted_service = None
        try:

            service_group_id = request.POST.get("group_id", None)
            envs = request.POST.get("envs", "")
            env_map = json.loads(envs)

            status_label = request.POST.get("methodval","")
            label_map = json.loads(status_label)

            services_min_memory = request.POST.get("service_min_memory","")
            memory_map = json.loads(services_min_memory)

            if not service_group_id:
                data.update({"success": False, "status": "failure", "info": u"服务异常"})
                return JsonResponse(data, status=500)

            shared_group = AppServiceGroup.objects.get(ID=groupId)
            # 查询分享组中的服务ID
            app_service_list = self.get_published_service_info(groupId)
            published_services = []
            for app in app_service_list:
                # 第二步已经做过相应的判断,此处可以不用重复判断版本是否正确
                service_list = ServiceInfo.objects.filter(service_key=app.service_key, version=app.version)
                if service_list:
                    published_services.append(service_list[0])

            # 根据依赖关系将服务进行排序
            sorted_service = self.sort_service(published_services)
            expired_time = datetime.datetime.now() + datetime.timedelta(days=7) + datetime.timedelta(hours=1)
            for service_info in sorted_service:
                logger.debug("service_info.service_key: {}".format(service_info.service_key))
                gct = GroupCreateTemp.objects.get(service_key=service_info.service_key, tenant_id=self.tenant.tenant_id,
                                                  service_group_id=service_group_id)
                service_id = gct.service_id
                logger.debug("gct.service_id: {}".format(gct.service_id))
                current_service_ids.append(service_id)
                service_alias = "gr" + service_id[-6:]
                # console层创建服务和组关系
                newTenantService = baseService.create_service(service_id, self.tenant.tenant_id, service_alias,
                                                              gct.service_cname,
                                                              service_info,
                                                              self.user.pk, region=self.response_region)

                memory = int(memory_map.get(service_info.service_key, service_info.min_memory))
                if memory < 128:
                    memory *= 1024
                cpu = baseService.calculate_service_cpu(self.response_region,memory)
                newTenantService.min_memory = memory
                newTenantService.min_cpu = cpu
                newTenantService.save()

                if self.tenant.pay_type == 'free':
                    newTenantService.expired_time = expired_time
                    # newTenantService.expired_time = self.tenant.expired_time
                    newTenantService.save()
                if service_group_id:
                    group_id = int(service_group_id)
                    if group_id > 0:
                        ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                                                            tenant_id=self.tenant.tenant_id,
                                                            region_name=self.response_region)
                monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)

                # 环境变量
                logger.debug("create service env!")
                env_list = env_map.get(service_info.service_key)
                self.copy_envs(service_info, newTenantService, env_list)
                # 端口信息
                logger.debug("create service port!")
                self.copy_ports(service_info, newTenantService)
                # 持久化目录
                logger.debug("create service volumn!")
                self.copy_volumes(service_info, newTenantService)

                dep_sids = []
                tsrs = TenantServiceRelation.objects.filter(service_id=newTenantService.service_id)
                for tsr in tsrs:
                    dep_sids.append(tsr.dep_service_id)

                baseService.create_region_service(newTenantService, self.tenantName, self.response_region,
                                                  self.user.nick_name, dep_sids=json.dumps(dep_sids))
                
                service_status = "stateless" if newTenantService.extend_method == "stateless" else "state"
                label_data = {}
                label_data["label_values"] = "无状态的应用" if service_status == "stateless" else "有状态的应用"
                label_data["enterprise_id"] = self.tenant.enterprise_id
                region_api.update_service_state_label(self.response_region, self.tenantName, newTenantService.service_alias, label_data)
                newTenantService.save()

                # 创建服务依赖
                logger.debug("create service dependency!")
                self.create_dep_service(service_info, newTenantService, service_group_id)
                # 构建服务
                body = {}
                event = self.create_service_event(newTenantService, self.tenant, "deploy")
                kind = baseService.get_service_kind(newTenantService)
                body["event_id"] = event.event_id
                body["deploy_version"] = newTenantService.deploy_version
                body["operator"] = self.user.nick_name
                body["action"] = "upgrade"
                body["kind"] = kind
                body["enterprise_id"] = self.tenant.enterprise_id

                envs = {}
                buildEnvs = TenantServiceEnvVar.objects.filter(service_id=service_id, attr_name__in=(
                    "COMPILE_ENV", "NO_CACHE", "DEBUG", "PROXY", "SBT_EXTRAS_OPTS"))
                for benv in buildEnvs:
                    envs[benv.attr_name] = benv.attr_value
                body["envs"] = envs

                region_api.build_service(newTenantService.service_region, self.tenantName,
                                         newTenantService.service_alias, body)

                monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'init_region_service', True)
            # 创建成功,删除临时数据
            GroupCreateTemp.objects.filter(share_group_id=groupId).delete()
            next_url = "/apps/{0}/myservice/?gid={1}".format(self.tenantName, service_group_id)
            data.update({"success": True, "code": 200, "next_url": next_url})

        except Exception as e:
            logger.exception(e)
            try:
                if sorted_service:
                    for service in sorted_service:
                        region_api.delete_service(self.response_region, self.tenantName, service.service_alias,self.tenant.enterprise_id)
                        data = service.toJSON()
                        newTenantServiceDelete = TenantServiceInfoDelete(**data)
                        newTenantServiceDelete.save()

                TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id,
                                                 service_id__in=current_service_ids).delete()
                TenantServiceAuth.objects.filter(service_id__in=current_service_ids).delete()
                ServiceDomain.objects.filter(service_id__in=current_service_ids).delete()
                TenantServiceRelation.objects.filter(tenant_id=self.tenant.tenant_id,
                                                     service_id__in=current_service_ids).delete()
                TenantServiceEnvVar.objects.filter(tenant_id=self.tenant.tenant_id,
                                                   service_id__in=current_service_ids).delete()
                TenantServicesPort.objects.filter(tenant_id=self.tenant.tenant_id,
                                                  service_id__in=current_service_ids).delete()
                TenantServiceVolume.objects.filter(service_id__in=current_service_ids).delete()

                data.update({"success": False, "code": 500})
            except Exception as e:
                logger.exception(e)

        return JsonResponse(data, status=200)

    def create_service_event(self, service, tenant, action):
        event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                             tenant_id=tenant.tenant_id, type="{0}".format(action),
                             deploy_version=service.deploy_version,
                             old_deploy_version=service.deploy_version,
                             user_name=self.user.nick_name, start_time=datetime.datetime.now())
        event.save()
        return event

    def copy_ports(self, source_service, current_service):
        AppPorts = AppServicePort.objects.filter(service_key=current_service.service_key,
                                                 app_version=current_service.version)
        baseService = BaseTenantService()
        for port in AppPorts:
            baseService.addServicePort(current_service, source_service.is_init_accout,
                                       container_port=port.container_port, protocol=port.protocol,
                                       port_alias=port.port_alias,
                                       is_inner_service=port.is_inner_service, is_outer_service=port.is_outer_service)

    def copy_envs(self, service_info, current_service, env_list):
        s = current_service
        baseService = BaseTenantService()
        has_env = []
        for e in env_list:
            source_env = AppServiceEnv.objects.get(service_key=s.service_key, app_version=s.version,
                                                   attr_name=e["attr_name"])
            baseService.saveServiceEnvVar(s.tenant_id, s.service_id, source_env.container_port, source_env.name,
                                          e["attr_name"], e["attr_value"], source_env.is_change, source_env.scope)
            has_env.append(source_env.attr_name)
        envs = AppServiceEnv.objects.filter(service_key=service_info.service_key, app_version=service_info.version)
        for env in envs:
            if env.attr_name not in has_env:
                baseService.saveServiceEnvVar(s.tenant_id, s.service_id, env.container_port, env.name,
                                              env.attr_name, env.attr_value, env.is_change, env.scope)

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
