# -*- coding: utf8 -*-
import datetime
import json
import re

from django.http import JsonResponse

from www.monitorservice.monitorhook import MonitorHook
from www.views import AuthedView
from www.decorator import perm_required

from www.service_http import RegionServiceApi
from django.conf import settings
from goodrain_web.decorator import method_perf_time
from www.models.main import ServiceGroup, ServiceGroupRelation, TenantServiceInfo, TenantServiceEnvVar, Users
import logging

from www.views.mixin import LeftSideBarMixin

logger = logging.getLogger('default')

regionClient = RegionServiceApi()
monitorhook = MonitorHook()


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
            ServiceGroup.objects.create(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                        group_name=group_name)
            return JsonResponse({'ok': True, "info": "修改成功"})
        except Exception as e:
            print e
            logger.exception(e)


class UpdateGroupView(LeftSideBarMixin, AuthedView):
    """修改组"""

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        new_group_name = request.POST.get("new_group_name", "")
        group_id = request.POST.get("group_id")
        try:
            if new_group_name.strip == "" or group_id.strip == "":
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

    def post(self, request, *args, **kwargs):
        group_id = request.POST.get("group_id", "")
        service_id = request.POST.get("service_id", "")
        try:
            if group_id.strip == "" or service_id.strip == "":
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
                for service_id in service_ids:
                    current_service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                    service_id=service_id)
                    body = {}
                    body["deploy_version"] = current_service.deploy_version
                    body["operator"] = str(self.user.nick_name)
                    regionClient.restart(current_service.service_region, service_id, json.dumps(body))

                    monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_start', True)
                result = {"ok": True, "info": "启动成功"}
            except Exception, e:
                logger.exception(e)
                result = {"ok": False, "info": "启动失败"}
                monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_start', False)

        elif action == "deploy":
            try:
                for service_id in service_ids:
                    current_service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                    service_id=service_id)
                    gitUrl = current_service.git_url
                    if current_service.category == "application" and gitUrl is not None and gitUrl != "":
                        body = {}
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
                        body["gitUrl"] = "--branch " + current_service.code_version + " --depth 1 " + clone_url
                        body["operator"] = str(self.user.nick_name)
    
                        envs = {}
                        buildEnvs = TenantServiceEnvVar.objects.filter(service_id=service_id, attr_name__in=("COMPILE_ENV", "NO_CACHE", "DEBUG", "PROXY"))
                        for benv in buildEnvs:
                            envs[benv.attr_name] = benv.attr_value
                        body["envs"] = json.dumps(envs)
    
                        regionClient.build_service(current_service.service_region, service_id, json.dumps(body))
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
                    body = {}
                    body["operator"] = str(self.user.nick_name)
                    regionClient.stop(current_service.service_region, service_id, json.dumps(body))
                    current_service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                    service_id=service_id)
                    monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_stop', True)
                result = {"ok": True, "info": "停止成功"}
            except Exception, e:
                logger.exception(e)
                result = {"ok": False, "info": "停止失败"}
                monitorhook.serviceMonitor(self.user.nick_name, current_service, 'app_stop', False)
        return JsonResponse(result, status=200)

    def _saveAdapterEnv(self, service):
        num = TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="GD_ADAPTER").count()
        if num < 1:
            attr = {"tenant_id": service.tenant_id, "service_id": service.service_id, "name": "GD_ADAPTER",
                    "attr_name": "GD_ADAPTER", "attr_value": "true", "is_change": 0, "scope": "inner", "container_port":-1}
            TenantServiceEnvVar.objects.create(**attr)
            data = {"action": "add", "attrs": attr}
            regionClient.createServiceEnv(service.service_region, service.service_id, json.dumps(data))
