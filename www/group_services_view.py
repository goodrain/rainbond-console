# -*- coding: utf8 -*-
import json
from decimal import Decimal
from django.http import Http404,HttpResponse
from addict import Dict
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse

from share.manager.region_provier import RegionProviderManager
from www.models.main import ServiceAttachInfo, ServiceFeeBill, ServiceGroup, GroupCreateTemp
from www.views import AuthedView, LeftSideBarMixin, CopyPortAndEnvMixin
from www.decorator import perm_required
from www.models import (ServiceInfo, TenantServiceInfo, TenantServiceAuth, TenantServiceRelation,
                        AppServicePort, AppServiceEnv, AppServiceRelation, ServiceExtendMethod,
                        AppServiceVolume, AppService, ServiceGroupRelation, ServiceCreateStep, AppServiceGroup)
from service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, \
    TenantRegionService, \
    AppCreateService
from www.monitorservice.monitorhook import MonitorHook
from www.utils.crypt import make_uuid
from www.app_http import AppServiceApi
from www.region import RegionInfo
from django.db.models import Q, Count
from www.utils import sn

import logging
import datetime
from dateutil.relativedelta import relativedelta

logger = logging.getLogger('default')

regionClient = RegionServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
appClient = AppServiceApi()
tenantRegionService = TenantRegionService()
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
        share_group_pk = None
        try:
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
                    raise Http404
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
        group_name = request.POST.get("group_name", None)

        try:
            service_group = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region,group_name=group_name)
            if len(service_group) > 0:
                return JsonResponse({"success": False, "info": u"组名已存在,请更换组名"}, status=200)
            # 创建组
            group = ServiceGroup.objects.create(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                                group_name=group_name)
            next_url = "/apps/{0}/group-deploy/{1}/step2/?group_id={2}".format(self.tenantName, groupId, group.ID)
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

    def preprocess(self, services):
        need_create_service = []
        is_pass = True
        data = {}
        for s in services:
            service_key = s.get("service_key")
            service_version = s.get("service_version")
            service_name = s.get("service_name")
            if not service_name:
                data["status"] = "failure"
                is_pass = False
                return need_create_service,is_pass,data
            service_model_list = ServiceInfo.objects.filter(service_key=service_key, version=service_version)
            if not service_model_list:
                data["status"] = "notexist"
                is_pass = False
                return need_create_service,is_pass,data
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
                return need_create_service,is_pass,data

            ccpu = int(service.min_memory / 128) * 20
            service.min_cpu = ccpu
            service.service_cname = service_name
            need_create_service.append(service)
            data["status"] = "success"
        return need_create_service, is_pass, data

    @never_cache
    @perm_required('code_deploy')
    def get(self, request, groupId, *args, **kwargs):
        context = self.get_context()
        try:
            # 新创建的组ID
            group_id = request.GET.get("group_id")
            service_group = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region, pk=group_id)
            if not service_group:
                raise Http404
            context["group_id"] = group_id
            shared_group = AppServiceGroup.objects.get(ID=groupId)
            # 查询分享组中的服务ID
            service_ids = shared_group.service_ids
            service_id_list = json.loads(service_ids)
            app_service_list = AppService.objects.filter(service_id__in=service_id_list)
            published_service_list = []
            for app_service in app_service_list:
                services = ServiceInfo.objects.filter(service_key=app_service.service_key,version=app_service.app_version)
                services = list(services)
                # 没有服务模板,需要下载模板
                if len(services) == 0:
                    code, base_info, dep_map, error_msg = baseService.download_service_info(app_service.service_key, app_service.app_version)
                    if code == 500:
                        logger.error(error_msg)
                    else:
                        services.append(base_info)
                if len(services) > 0:
                    published_service_list.append(services[0])
                else:
                    logger.error(
                        "service_key {0} version {1} is not found in table service or can be download from market".format(
                            app_service.service_key, app_service.app_version))
            # 发布的应用有不全的信息
            if len(published_service_list) != len(service_id_list):
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
            success = tenantRegionService.init_for_region(self.response_region, self.tenantName, self.tenant.tenant_id,
                                                          self.user)
            if not success:
                data["status"] = "failure"
                return JsonResponse(data, status=200)
            need_create_service, is_pass, result = self.preprocess(services)
            if not is_pass:
                return JsonResponse(result, status=200)
            is_success = True
            for ncs in need_create_service:
                service_id = make_uuid(tenant_id)
                service_cname = ncs.service_cname
                try:
                    GroupCreateTemp.objects.filter(share_group_id=groupId).delete()
                    temp_data = {}
                    temp_data["tenant_id"] = tenant_id
                    temp_data["service_id"] = service_id
                    temp_data["service_key"] = ncs.service_key
                    temp_data["service_cname"] = service_cname
                    temp_data["share_group_id"] = groupId
                    temp_data["service_group_id"] = service_group_id
                    GroupCreateTemp.objects.create(**temp_data)
                    # newTenantService = baseService.create_service(service_id, tenant_id, service_alias, service_cname,
                    #                                               ncs,
                    #                                               self.user.pk, region=self.response_region)
                    # if service_group_id:
                    #     group_id = int(service_group_id)
                    #     if group_id > 0:
                    #         ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                    #                                             tenant_id=self.tenant.tenant_id,
                    #                                             region_name=self.response_region)
                    # monitorhook.serviceMonitor(self.user.nick_name, newTenantService, 'create_service', True)
                except Exception as ex:
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

    @never_cache
    @perm_required('code_deploy')
    def get(self, request,groupId, *args, **kwargs):
        tenant_id = self.tenant.tenant_id
        context = self.get_context()
        try:
            group_id = request.GET.get("group_id")
            if not ServiceGroup.objects.filter(ID=group_id).exists():
                raise Http404

            context["createApp"] = "active"
            context["tenantName"] = self.tenantName
            temp_list = GroupCreateTemp.objects.filter(share_group_id=groupId, tenant_id=tenant_id)
            if len(temp_list) == 0:
                return self.redirect_to("/apps/{0}/group-deploy/{1}/step1/".format(self.tenantName, groupId))
            service_cname_map = {tmp.service_key:tmp.service_cname for tmp in temp_list}
            context["service_cname_map"] = service_cname_map

            shared_group = AppServiceGroup.objects.get(ID=groupId)
            # 查询分享组中的服务ID
            service_ids = shared_group.service_ids
            service_id_list = json.loads(service_ids)
            app_service_list = AppService.objects.filter(service_id__in=service_id_list)
            app_port_map = {}
            app_relation_map = {}
            app_env_map = {}
            app_volumn_map = {}
            for app in app_service_list:
                # 端口
                port_list = AppServicePort.objects.filter(service_key=app.service_key, app_version=app.app_version)
                app_port_map[app.service_key] = list(port_list)
                # 环境变量
                env_list = AppServiceEnv.objects.filter(service_key=app.service_key, app_version=app.app_version)
                app_env_map[app.service_key] = list(env_list)
                # 持久化路径
                volumn_list = AppServiceVolume.objects.filter(service_key=app.service_key, app_version=app.app_version)
                app_volumn_map[app.service_key] = list(volumn_list)
                # 依赖关系
                dep_list = AppServiceRelation.objects.filter(service_key=app.service_key, app_servion=app.app_version)
                app_relation_map[app.service_key] = list(dep_list)
            context["app_port_map"] = app_port_map
            context["app_relation_map"] = app_relation_map
            context["app_env_map"] = app_env_map
            context["app_volumn_map"] = app_volumn_map
            context["service_list"] = service_id_list

        except Http404 as e_404:
            logger.exception(e_404)
            return HttpResponse("<html><body>Group Not Found !</body></html>")
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/group/group_app_create_step_3.html", context)

    @never_cache
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            pass
        except Exception as e:
            logger.exception(e)
        data.update({"success": True, "code": 200})
        return JsonResponse(data, status=200)
