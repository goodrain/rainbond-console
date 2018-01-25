# -*- coding: utf8 -*-
import datetime
import json
import logging

from django.db.models import Sum, F
from django.http import JsonResponse

from www.apiclient.regionapi import RegionInvokeApi
from www.app_http import AppServiceApi
from www.decorator import perm_required
from www.models.main import ServiceGroup, ServiceGroupRelation, TenantServiceInfo, TenantServiceEnvVar, Users, \
    ServiceEvent
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource
from www.utils.crypt import make_uuid
from www.views import AuthedView
from www.views.mixin import LeftSideBarMixin

logger = logging.getLogger('default')

monitorhook = MonitorHook()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
region_api = RegionInvokeApi()
appClient = AppServiceApi()


class AddGroupView(LeftSideBarMixin, AuthedView):
    """添加组"""

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        group_name = request.POST.get("group_name", "")
        try:
            if group_name.strip() == "":
                return JsonResponse({"ok": False, "info": "组名不能为空"})
            if ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                           group_name=group_name).exists():
                return JsonResponse({"ok": False, "info": "组名已存在"})
            group_info = ServiceGroup.objects.create(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                                     group_name=group_name)
            return JsonResponse(
                {'ok': True, "info": "修改成功", "group_id": group_info.ID, "group_name": group_info.group_name})
        except Exception as e:
            logger.exception(e)


class UpdateGroupView(LeftSideBarMixin, AuthedView):
    """修改组"""

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        new_group_name = request.POST.get("new_group_name", "")
        group_id = request.POST.get("group_id")
        try:
            if new_group_name.strip() == "" or group_id.strip() == "":
                return JsonResponse({"ok": False, "info": "参数错误"})
            ServiceGroup.objects.filter(ID=group_id).update(group_name=new_group_name)
            return JsonResponse({"ok": True, "info": "修改成功"})
        except Exception as e:
            logger.exception(e)


class DeleteGroupView(LeftSideBarMixin, AuthedView):
    """删除组"""

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        group_id = request.POST.get("group_id")
        try:
            ServiceGroup.objects.filter(ID=group_id).delete()
            ServiceGroupRelation.objects.filter(group_id=group_id).delete()
            return JsonResponse({"ok": True, "info": "删除成功"})
        except Exception as e:
            logger.exception(e)


class UpdateServiceGroupView(LeftSideBarMixin, AuthedView):
    """修改服务所在的组"""

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        group_id = request.POST.get("group_id", "")
        service_id = request.POST.get("service_id", "")
        try:
            if group_id.strip() == "" or service_id.strip() == "":
                return JsonResponse({"ok": False, "info": "参数错误"})
            if group_id == "-1":
                ServiceGroupRelation.objects.filter(service_id=service_id).delete()
            elif ServiceGroupRelation.objects.filter(service_id=service_id).count() > 0:
                ServiceGroupRelation.objects.filter(service_id=service_id).update(group_id=group_id)
            else:
                ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                                                    tenant_id=self.tenant.tenant_id, region_name=self.response_region)
            return JsonResponse({"ok": True, "info": "修改成功"})
        except Exception as e:
            logger.exception(e)


class BatchActionView(LeftSideBarMixin, AuthedView):
    """批量操作(批量启动,批量停止,批量部署)"""

    def generate_event(self, service, action):
        old_deploy_version = ""
        events = ServiceEvent.objects.filter(service_id=service.service_id).order_by("-start_time")
        if events:
            last_event = events[0]
            if last_event.final_status == "":
                if not baseService.checkEventTimeOut(last_event):
                    return "often", None
            old_deploy_version = last_event.deploy_version
        event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                             tenant_id=self.tenant.tenant_id, type=action,
                             deploy_version=service.deploy_version, old_deploy_version=old_deploy_version,
                             user_name=self.user.nick_name, start_time=datetime.datetime.now())
        event.save()
        if action == "deploy":
            last_all_deploy_event = ServiceEvent.objects.filter(service_id=service.service_id,
                                                                type="deploy").order_by("-start_time")
            if last_all_deploy_event:
                last_deploy_event = last_all_deploy_event[0]
                old_code_version = last_deploy_event.code_version
                event.old_code_version = old_code_version
                event.save()
        return "success", event

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", None)
        service_ids = request.POST.get("service_ids", None)
        result = {}
        if service_ids is not None:
            service_ids = json.loads(service_ids)
        if action is None:
            result = {"ok": True, "info": "参数异常"}
        if action == 'start':
            try:
                # 已用内存
                tm = tenantUsedResource.calculate_real_used_resource(self.tenant, self.response_region)
                res = TenantServiceInfo.objects.filter(service_id__in=service_ids).aggregate(
                    memory=Sum(F('min_node') * F('min_memory')))
                memory = res["memory"]

                if self.tenant.pay_type == "free":
                    total = memory + tm
                    # if total > self.tenant.limit_memory:
                    if total > tenantUsedResource.get_limit_memory(self.tenant, self.response_region):
                        result = {"ok": False, "info": "资源超限,无法批量启动"}
                        return JsonResponse(result, status=200)

                for service_id in service_ids:
                    current_service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                    service_id=service_id)
                    status, event = self.generate_event(current_service, "restart")
                    if status == "often":
                        continue
                    body = {}
                    body["event_id"] = event.event_id
                    body["deploy_version"] = current_service.deploy_version
                    body["operator"] = str(self.user.nick_name)
                    body["enterprise_id"] = self.tenant.enterprise_id
                    # 启动
                    region_api.start_service(current_service.service_region, self.tenantName,
                                             current_service.service_alias, body)

                    monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_start', True)
                result = {"ok": True, "info": "启动成功"}
            except Exception, e:
                logger.exception(e)
                result = {"ok": False, "info": "启动失败"}
                monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_start', False)

        elif action == "deploy":
            try:
                # 已用内存
                tm = tenantUsedResource.calculate_real_used_resource(self.tenant, self.response_region)

                res = TenantServiceInfo.objects.filter(service_id__in=service_ids).aggregate(
                    memory=Sum(F('min_node') * F('min_memory')))
                memory = res["memory"]

                if self.tenant.pay_type == "free":
                    total = memory + tm
                    # if total > self.tenant.limit_memory:
                    if total > tenantUsedResource.get_limit_memory(self.tenant, self.response_region):
                        result = {"ok": False, "info": "资源超限,无法批量部署"}
                        return JsonResponse(result, status=200)

                for service_id in service_ids:
                    current_service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                    service_id=service_id)
                    status, event = self.generate_event(current_service, action)
                    if status == "often":
                        continue
                    gitUrl = current_service.git_url
                    if current_service.category == "application" and gitUrl is not None and gitUrl != "":
                        body = {}
                        body["event_id"] = event.event_id
                        if current_service.deploy_version == "" or current_service.deploy_version is None:
                            body["action"] = "deploy"
                        else:
                            body["action"] = "upgrade"
                        current_service.deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                        current_service.save()
                        clone_url = current_service.git_url
                        if current_service.code_from == "github":
                            code_user = clone_url.split("/")[3]
                            code_project_name = clone_url.split("/")[4].split(".")[0]
                            createUser = Users.objects.get(user_id=current_service.creater)
                            clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
                        body["deploy_version"] = current_service.deploy_version
                        body["repo_url"] = "--branch " + current_service.code_version + " --depth 1 " + clone_url
                        body["operator"] = str(self.user.nick_name)
                        kind = baseService.get_service_kind(self.service)
                        body["kind"] = kind
                        envs = {}
                        buildEnvs = TenantServiceEnvVar.objects.filter(service_id=service_id, attr_name__in=(
                            "COMPILE_ENV", "NO_CACHE", "DEBUG", "PROXY"))
                        for benv in buildEnvs:
                            envs[benv.attr_name] = benv.attr_value
                        body["envs"] = envs
                        body["service_alias"] = self.service.service_alias
                        body["enterprise_id"] = self.tenant.enterprise_id

                        region_api.build_service(current_service.service_region, self.tenantName,
                                                 current_service.service_alias, body)
                        monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_deploy', True)
                result = {"ok": True, "info": "部署成功"}
            except Exception, e:
                logger.exception(e)
                monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_deploy', False)
                result = {"ok": False, "info": "部署失败"}
        elif action == "stop":
            try:
                for service_id in service_ids:
                    current_service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                    service_id=service_id)
                    status, event = self.generate_event(current_service, action)
                    if status == "often":
                        continue
                    body = {}
                    body["event_id"] = event.event_id
                    body["operator"] = str(self.user.nick_name)
                    body["enterprise_id"] = self.tenant.enterprise_id
                    region_api.stop_service(current_service.service_region, self.tenantName,
                                            current_service.service_alias, body)
                    current_service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                    service_id=service_id)
                    monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_stop', True)
                result = {"ok": True, "info": "停止成功"}
            except Exception, e:
                logger.exception(e)
                result = {"ok": False, "info": "停止失败"}
                monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_stop', False)
        return JsonResponse(result, status=200)
