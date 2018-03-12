# -*- coding: utf8 -*-
import datetime
import json
import logging
import re

from django.conf import settings
from django.db import transaction
from django.forms import model_to_dict
from django.http import JsonResponse

from goodrain_web.decorator import method_perf_time
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.forms.services import EnvCheckForm
from www.models import (ServiceInfo, AppService, TenantServiceInfo,
                        TenantRegionInfo, PermRelService, TenantServiceRelation,
                        TenantServiceInfoDelete, Users, TenantServiceEnv,
                        TenantServiceAuth, ServiceDomain, TenantServiceEnvVar,
                        TenantServicesPort, TenantServiceMountRelation, TenantServiceVolume, ServiceEvent,
                        ServiceProbe, TenantServiceGroup)
from www.models.main import ServiceGroupRelation, ServiceAttachInfo, ServiceCreateStep, ServiceFeeBill, ServiceConsume, \
    ServiceDomainCertificate, ServicePaymentNotify, TenantServiceStatics
from www.monitorservice.monitorhook import MonitorHook
from www.service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, \
    CodeRepositoriesService, ServiceAttachInfoManage, ServicePluginResource
from www.utils.crypt import make_uuid
from www.utils.giturlparse import parse as git_url_parse
from www.utils.status_translate import get_status_info_map
from www.views import AuthedView
from django.db.models import Q
logger = logging.getLogger('default')

regionClient = RegionServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
codeRepositoriesService = CodeRepositoriesService()
region_api = RegionInvokeApi()
attach_manager = ServiceAttachInfoManage()
servicePluginResource = ServicePluginResource()

class AppDeploy(AuthedView):
    def update_event(self, event, message, status):
        event.status = status
        event.final_status = "complete"
        event.message = message
        event.end_time = datetime.datetime.now()
        if event.status == "failure" and event.type == "callback":
            event.deploy_version = event.old_deploy_version
        event.save()

    @method_perf_time
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        event = None
        data = {}
        try:
            if 'event_id' not in request.POST:
                data["status"] = "failure"
                data["message"] = "event is not exist."
                return JsonResponse(data, status=412)
            event_id = request.POST["event_id"]
            event = ServiceEvent.objects.get(event_id=event_id)

            if not event:
                data["status"] = "failure"
                data["message"] = "event is not exist."
                return JsonResponse(data, status=412)

            if tenantAccountService.isOwnedMoney(self.tenant, self.service.service_region):
                data["status"] = "owed"
                self.update_event(event, "余额不足请及时充值", "failure")
                return JsonResponse(data, status=200)

            if tenantAccountService.isExpired(self.tenant, self.service):
                data["status"] = "expired"
                self.update_event(event, "试用已到期", "failure")
                return JsonResponse(data, status=200)

            # if self.service.language is None or self.service.language == "":
            #     data["status"] = "language"
            #     self.update_event(event, "构建语言未知", "failure")
            #     return JsonResponse(data, status=200)

            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id

            # calculate resource
            rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, 0, True)
            if not flag:
                if rt_type == "memory":
                    data["status"] = "over_memory"
                else:
                    data["status"] = "over_money"
                self.update_event(event, "可用资源不足", "failure")
                return JsonResponse(data, status=200)

            gitUrl = request.POST.get('git_url', None)
            if gitUrl is None:
                gitUrl = self.service.git_url
            body = {}
            if self.service.deploy_version == "" or self.service.deploy_version is None:
                body["action"] = "deploy"
            else:
                body["action"] = "upgrade"

            self.service.deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            self.service.save()

            # 保存最新 deploy_version
            event.deploy_version = self.service.deploy_version
            event.save()

            clone_url = self.service.git_url
            if self.service.code_from == "github":
                code_user = clone_url.split("/")[3]
                code_project_name = clone_url.split("/")[4].split(".")[0]
                createUser = Users.objects.get(user_id=self.service.creater)
                clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"

            body["deploy_version"] = self.service.deploy_version
            body["operator"] = str(self.user.nick_name)
            body["event_id"] = event_id
            body["service_id"] = service_id
            envs = {}
            buildEnvs = TenantServiceEnvVar.objects.filter(service_id=service_id, attr_name__in=(
                "COMPILE_ENV", "NO_CACHE", "DEBUG", "PROXY", "SBT_EXTRAS_OPTS"))
            for benv in buildEnvs:
                envs[benv.attr_name] = benv.attr_value
            body["envs"] = envs
            kind = baseService.get_service_kind(self.service)
            body["kind"] = kind
            if kind == "source":
                body["repo_url"] = "--branch " + self.service.code_version + " --depth 1 " + clone_url
            body["service_alias"] = self.service.service_alias
            body["tenant_name"] = self.tenant.tenant_name
            body["enterprise_id"] = self.tenant.enterprise_id
            # 新版api构建完成后没有进行启动操作
            region_api.build_service(self.service.service_region, self.tenantName, self.serviceAlias, body)
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_deploy', True)

            data["status"] = "success"
            return JsonResponse(data, status=200)
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
            if event:
                self.update_event(event, "部署操作失败，请重试！", "failure")
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_deploy', False)
        return JsonResponse(data, status=500)


class ServiceManage(AuthedView):
    @perm_required('manage_service')
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        result = {}

        if 'event_id' not in request.POST:
            result["status"] = "failure"
            result["message"] = "event is not exist."
            return JsonResponse(result, status=412)
        event_id = request.POST["event_id"]
        event = ServiceEvent.objects.get(event_id=event_id)
        if not event:
            result["status"] = "failure"
            result["message"] = "event is not exist."
            return JsonResponse(result, status=412)
        event.deploy_version = self.service.deploy_version

        action = request.POST["action"]
        user_actions = ("rollback", "restart", "reboot")
        if action in user_actions:
            if tenantAccountService.isOwnedMoney(self.tenant, self.service.service_region):
                result["status"] = "owed"
                self.update_event(event, "余额不足请及时充值", "failure")
                return JsonResponse(result, status=200)

            if tenantAccountService.isExpired(self.tenant, self.service):
                result["status"] = "expired"
                self.update_event(event, "试用已到期", "failure")
                return JsonResponse(result, status=200)

        if action == "stop":
            try:
                body = {}
                body["operator"] = str(self.user.nick_name)
                body["event_id"] = event_id
                body["enterprise_id"] = self.tenant.enterprise_id
                region_api.stop_service(self.service.service_region,
                                        self.tenantName,
                                        self.service.service_alias,
                                        body)
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_stop', True)
                result["status"] = "success"
            except Exception, e:
                if event:
                    event.message = u"停止应用失败,{}".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_stop', False)
        elif action == "restart":
            try:
                # calculate resource
                diff_memory = self.service.min_node * self.service.min_memory
                rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, diff_memory, False)
                if not flag:
                    if rt_type == "memory":
                        result["status"] = "over_memory"
                        self.update_event(event, "资源已达上限，不能升级", "failure")
                    else:
                        result["status"] = "over_money"
                        self.update_event(event, "余额不足，不能升级", "failure")
                    return JsonResponse(result, status=200)
                body = {}
                body["deploy_version"] = self.service.deploy_version
                body["operator"] = str(self.user.nick_name)
                body["event_id"] = event_id
                body["enterprise_id"] = self.tenant.enterprise_id
                region_api.start_service(self.service.service_region, self.tenantName, self.service.service_alias,
                                         body)
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_start', True)
                result["status"] = "success"
            except Exception, e:
                if event:
                    event.message = u"启动应用失败" + e.message
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_start', False)
        elif action == "reboot":
            try:
                diff_memory = self.service.min_node * self.service.min_memory
                rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, diff_memory, False)
                if not flag:
                    if rt_type == "memory":
                        result["status"] = "over_memory"
                        self.update_event(event, "资源不足，不能升级", "failure")
                    else:
                        result["status"] = "over_money"
                        self.update_event(event, "余额不足，不能升级", "failure")
                    return JsonResponse(result, status=200)
                body = {}
                body["operator"] = str(self.user.nick_name)
                body["event_id"] = event_id
                body["enterprise_id"] = self.tenant.enterprise_id
                region_api.restart_service(self.service.service_region,
                                           self.tenantName,
                                           self.service.service_alias,
                                           body)

                result["status"] = "success"
            except Exception, e:
                if event:
                    event.message = u"重启应用失败" + e.message
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_reboot', False)
        elif action == "delete":
            try:
                sid = transaction.savepoint()
                now = datetime.datetime.now()
                service_attach_info = ServiceAttachInfo.objects.get(service_id=self.service.service_id,
                                                                    tenant_id=self.tenant.tenant_id)
                has_prepaid_items = False
                if service_attach_info.memory_pay_method == "prepaid" or service_attach_info.disk_pay_method == "prepaid":
                    has_prepaid_items = True
                unpayed_bills = ServiceFeeBill.objects.filter(service_id=self.service.service_id,
                                                              tenant_id=self.tenant.tenant_id, pay_status="unpayed")
                if has_prepaid_items:
                    if now < service_attach_info.buy_end_time:
                        #  开始计费之前,如果已经付款
                        if not unpayed_bills:
                            result["status"] = "payed"
                            result["info"] = u"已付款应用无法删除"
                            self.update_event(event, "已付款应用无法删除", "failure")
                            return JsonResponse(result)
                # 判断状态
                try:
                    status_info = region_api.check_service_status(self.service.service_region, self.tenant.tenant_name,
                                                                  self.service.service_alias, self.tenant.enterprise_id)
                    status = status_info["bean"]["cur_status"]
                    if status in ("running", "starting", "stopping", "failure", "unKnow"):
                        result["status"] = "service running"
                        result["info"] = u"应用可能处于运行状态,请先关闭应用"
                        self.update_event(event, "应用可能处于运行状态,请先关闭应用", "failure")
                        return JsonResponse(result)
                except Exception as e:
                    pass

                # published = AppService.objects.filter(service_id=self.service.service_id).count()
                # if published:
                #     result["status"] = "published"
                #     self.update_event(event, "关联了已发布服务, 不可删除", "failure")
                #     result["info"] = u"关联了已发布服务, 不可删除"
                #     return JsonResponse(result)

                dependSids = TenantServiceRelation.objects.filter(dep_service_id=self.service.service_id).values(
                    "service_id")
                if len(dependSids) > 0:
                    sids = []
                    for ds in dependSids:
                        sids.append(ds["service_id"])
                    if len(sids) > 0:
                        aliasList = TenantServiceInfo.objects.filter(service_id__in=sids).values('service_cname')
                        depalias = ""
                        for alias in aliasList:
                            if depalias != "":
                                depalias = depalias + ","
                            depalias = depalias + alias["service_cname"]
                        result["dep_service"] = depalias
                        result["status"] = "evn_dependency"
                        self.update_event(event, "被依赖, 不可删除", "failure")
                        return JsonResponse(result)

                dependSids = TenantServiceMountRelation.objects.filter(dep_service_id=self.service.service_id).values(
                    "service_id")
                if len(dependSids) > 0:
                    sids = []
                    for ds in dependSids:
                        sids.append(ds["service_id"])
                    if len(sids) > 0:
                        aliasList = TenantServiceInfo.objects.filter(service_id__in=sids).values('service_alias')
                        depalias = ""
                        for alias in aliasList:
                            if depalias != "":
                                depalias = depalias + ","
                            depalias = depalias + alias["service_alias"]
                        result["dep_service"] = depalias
                        result["status"] = "mnt_dependency"
                        self.update_event(event, "被依赖, 不可删除", "failure")
                        return JsonResponse(result)

                # 集群删除
                try:
                    region_api.delete_service(self.service.service_region, self.tenantName, self.service.service_alias,
                                              self.tenant.enterprise_id)
                except region_api.CallApiError as e:
                    if e.status != 404:
                        logger.exception(e)
                        result["status"] = "failure"
                        result["message"] = "删除应用失败 {0}".format(e.message)
                        return JsonResponse(result)

                data = self.service.toJSON()
                newTenantServiceDelete = TenantServiceInfoDelete(**data)
                newTenantServiceDelete.save()

                if self.service.code_from == 'gitlab_new' and self.service.git_project_id > 0:
                    # 排除goodrain的租户
                    if self.tenant.tenant_id not in ("b7584c080ad24fafaa812a7739174b50",):
                        codeRepositoriesService.deleteProject(self.service)

                TenantServiceEnv.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceAuth.objects.filter(service_id=self.service.service_id).delete()
                ServiceDomain.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceRelation.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceMountRelation.objects.filter(service_id=self.service.service_id).delete()
                TenantServicesPort.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceVolume.objects.filter(service_id=self.service.service_id).delete()
                ServiceGroupRelation.objects.filter(service_id=self.service.service_id,
                                                    tenant_id=self.tenant.tenant_id).delete()
                ServiceAttachInfo.objects.filter(service_id=self.service.service_id).delete()
                ServiceCreateStep.objects.filter(service_id=self.service.service_id).delete()
                # 删除event相关数据
                # events = ServiceEvent.objects.filter(service_id=self.service.service_id)

                ServiceEvent.objects.filter(service_id=self.service.service_id).delete()
                # 删除应用检测数据
                ServiceProbe.objects.filter(service_id=self.service.service_id).delete()
                ServicePaymentNotify.objects.filter(service_id=self.service.service_id).delete()

                # 如果这个应用属于应用组, 则删除应用组最后一个应用后同时删除应用组
                if self.service.tenant_service_group_id > 0:
                    count = TenantServiceInfo.objects.filter(
                        tenant_service_group_id=self.service.tenant_service_group_id).count()
                    if count <= 1:
                        TenantServiceGroup.objects.filter(ID=self.service.tenant_service_group_id).delete()

                TenantServiceInfo.objects.get(service_id=self.service.service_id).delete()

                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_delete', True)
                result["status"] = "success"
                transaction.savepoint_commit(sid)
            except Exception, e:
                transaction.savepoint_rollback(sid)
                if event:
                    event.message = "删除应用失败 {0}".format(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                logger.exception(e)
                result["status"] = "failure"
                result["message"] = "删除应用失败 {0}".format(e.message)
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_delete', False)
        elif action == "rollback":
            try:
                deploy_version = request.POST["deploy_version"]
                if deploy_version == self.service.deploy_version:
                    result["status"] = "failure"
                    result["message"] = "当前版本与所需回滚版本一致，无需回滚"
                    return JsonResponse(result)
                if event_id != "":
                    # calculate resource
                    rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, 0, True)
                    if not flag:
                        if rt_type == "memory":
                            result["status"] = "over_memory"
                            self.update_event(event, "资源不足，不能升级", "failure")
                        else:
                            result["status"] = "over_money"
                            self.update_event(event, "余额不足，不能升级", "failure")
                        return JsonResponse(result, status=200)
                    body = {}
                    body["event_id"] = event_id
                    body["operator"] = str(self.user.nick_name)
                    body["deploy_version"] = deploy_version
                    body["enterprise_id"] = self.tenant.enterprise_id
                    region_api.rollback(self.service.service_region, self.tenantName, self.service.service_alias,
                                        body)
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_rollback', True)
                result["status"] = "success"
                event.deploy_version = deploy_version
                event.save()
            except Exception, e:
                if event:
                    event.message = u"回滚应用失败" + str(e.message)
                    event.final_status = "complete"
                    event.status = "failure"
                    event.save()
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_rollback', False)
        return JsonResponse(result)

    def update_event(self, event, message, status):
        event.status = status
        event.final_status = "complete"
        event.message = message
        event.end_time = datetime.datetime.now()
        if event.status == "failure" and event.type == "callback":
            event.deploy_version = event.old_deploy_version
        event.save()


class ServiceUpgrade(AuthedView):

    def update_event(self, event, message, status):
        event.status = status
        event.final_status = "complete"
        event.message = message
        event.end_time = datetime.datetime.now()
        if event.status == "failure" and event.type == "callback":
            event.deploy_version = event.old_deploy_version
        event.save()

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        if 'event_id' not in request.POST:
            result["status"] = "failure"
            result["message"] = "event is not exist."
            return JsonResponse(result, status=412)
        event_id = request.POST["event_id"]
        event = ServiceEvent.objects.get(event_id=event_id)
        if not event:
            result["status"] = "failure"
            result["message"] = "event is not exist."
            return JsonResponse(result, status=412)

        if tenantAccountService.isOwnedMoney(self.tenant, self.service.service_region):
            result["status"] = "owed"
            result["msg"] = u"您已欠费，升级失败"
            self.update_event(event, "您已欠费，升级失败", "failure")
            return JsonResponse(result, status=200)

        if tenantAccountService.isExpired(self.tenant, self.service):
            result["status"] = "expired"
            result["msg"] = "超出免费使用期，升级失败"
            self.update_event(event, "超出免费使用期，升级失败", "failure")
            return JsonResponse(result, status=200)

        action = request.POST["action"]
        try:
            if action == "vertical":
                container_memory = request.POST["memory"]
                container_cpu = request.POST["cpu"]
                old_container_cpu = self.service.min_cpu
                old_container_memory = self.service.min_memory
                if int(container_memory) != old_container_memory or int(container_cpu) != old_container_cpu:
                    upgrade_container_memory = int(container_memory)
                    left = upgrade_container_memory % 128
                    if upgrade_container_memory > 0 and upgrade_container_memory <= 65536 and left == 0:
                        # calculate resource
                        diff_memory = upgrade_container_memory - int(old_container_memory)
                        rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, diff_memory,
                                                                               True)
                        if not flag:
                            if rt_type == "memory":
                                result["status"] = "over_memory"
                                self.update_event(event, "资源不足，升级失败","failure")
                            else:
                                result["status"] = "over_money"
                                self.update_event(event, "余额不足，升级失败", "failure")
                            return JsonResponse(result, status=200)

                        upgrade_container_cpu = baseService.calculate_service_cpu(self.service.service_region,
                                                                                  upgrade_container_memory)
                        body = {}
                        body["container_memory"] = upgrade_container_memory
                        body["deploy_version"] = self.service.deploy_version
                        body["container_cpu"] = upgrade_container_cpu
                        body["operator"] = str(self.user.nick_name)
                        body["event_id"] = event_id
                        body["enterprise_id"] = self.tenant.enterprise_id
                        region_api.vertical_upgrade(self.service.service_region,
                                                    self.tenantName,
                                                    self.service.service_alias,
                                                    body)

                        self.service.min_cpu = upgrade_container_cpu
                        self.service.min_memory = upgrade_container_memory
                        self.service.save()

                        monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_vertical', True)
                    else:
                        if event:
                            event.delete()
                else:
                    if event:
                        event.delete()
                result["status"] = "success"
            elif action == "horizontal":
                node_num = request.POST["node_num"]
                new_node_num = int(node_num)
                old_min_node = self.service.min_node
                if new_node_num >= 0 and new_node_num != old_min_node:
                    # calculate resource
                    diff_memory = (new_node_num - old_min_node) * self.service.min_memory
                    rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, diff_memory, True)
                    if not flag:
                        if rt_type == "memory":
                            result["status"] = "over_memory"
                            self.update_event(event, "资源不足，升级失败", "failure")
                        else:
                            result["status"] = "over_money"
                            self.update_event(event, "余额不足，升级失败", "failure")
                        return JsonResponse(result, status=200)

                    body = {}
                    body["node_num"] = new_node_num
                    body["deploy_version"] = self.service.deploy_version
                    body["operator"] = str(self.user.nick_name)
                    body["event_id"] = event_id
                    body["enterprise_id"] = self.tenant.enterprise_id
                    region_api.horizontal_upgrade(self.service.service_region, self.tenantName,
                                                  self.service.service_alias, body)

                    self.service.min_node = new_node_num
                    self.service.save()
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_horizontal', True)
                else:
                    if event:
                        event.delete()
                result["status"] = "success"
            elif action == "imageUpgrade":
                baseservice = ServiceInfo.objects.get(service_key=self.service.service_key,
                                                      version=self.service.version)
                if baseservice.update_version != self.service.update_version:
                    region_api.update_service(self.service.service_region,
                                              self.tenantName,
                                              self.service.service_alias,
                                              {"image_name": baseservice.image,
                                               "enterprise_id": self.tenant.enterprise_id})
                    self.service.image = baseservice.image
                    self.service.update_version = baseservice.update_version
                    self.service.save()
                result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            if action == "vertical":
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_vertical', False)
            elif action == "horizontal":
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_horizontal', False)
            result["status"] = "failure"
        return JsonResponse(result)


class ServiceRelation(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        action = request.POST["action"]
        dep_service_alias = request.POST["dep_service_alias"]
        try:
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            dep_service = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_alias=dep_service_alias)
            if action == "add":
                is_env_duplicate = self.is_env_duplicate(self.service, dep_service)
                if is_env_duplicate:
                    result["status"] = "failure"
                    result["msg"] = "要关联的应用的变量与已关联的应用变量重复，请修改后再试"
                    return JsonResponse(result)
                baseService.create_service_dependency(self.tenant, self.service, dep_service.service_id,
                                                      self.service.service_region)
            elif action == "cancel":
                baseService.cancel_service_dependency(self.tenant, self.service, dep_service.service_id,
                                                      self.service.service_region)

                relation_num = TenantServiceRelation.objects.filter(service_id=service_id, tenant_id=tenant_id).count()
                if relation_num == 0:
                    self.cancelAdapterEnv(self.service)
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)

    def cancelAdapterEnv(self, service):
        TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="GD_ADAPTER").delete()
        region_api.delete_service_env(service.service_region, self.tenantName, self.service.service_alias,
                                      {"env_name": "GD_ADAPTER", "enterprise_id": self.tenant.enterprise_id})

    def is_env_duplicate(self, service, dep_service):
        """ 判断要关联的应用和已有的依赖的别名是否重复"""
        dep_services_ids = TenantServiceRelation.objects.filter(tenant_id=self.tenant.tenant_id,
                                                                service_id=service.service_id).values_list(
            "dep_service_id", flat=True)
        dep_service_env = TenantServiceEnvVar.objects.filter(tenant_id=dep_service.tenant_id,
                                                             service_id=dep_service.service_id,
                                                             ).exclude(container_port__lt=0).values_list("attr_name",
                                                                                                         flat=True)
        dep_services_envs = TenantServiceEnvVar.objects.filter(tenant_id=self.tenant.tenant_id,
                                                               service_id__in=list(dep_services_ids),
                                                               attr_name__in=list(dep_service_env))
        if len(dep_services_envs) > 0:
            return True
        return False



class NoneParmsError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class UseMidRain(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        action = request.POST.get("action", None)
        try:
            if not action:
                raise NoneParmsError("UseMidRain need action.")
            if action == "add":
                self.addSevenLevelEnv(self.service)
                self.addIsHttpEnv(self.service)
            elif action == "del":
                self.delSevenLevelEnv(self.service)
            elif action == "check":
                if self.checkSevenLevelEnv(self.service):
                    result["is_mid"] = "no"
                else:
                    result["is_mid"] = "yes"

            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)

    def checkSevenLevelEnv(self, service):
        num = TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="SEVEN_LEVEL").count()
        if num < 1:
            return 1
        else:
            return 0

    def addSevenLevelEnv(self, service):
        num = TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="SEVEN_LEVEL").count()
        if num < 1:
            attr = {"tenant_id": service.tenant_id, "service_id": service.service_id, "name": "SEVEN_LEVEL",
                    "attr_name": "SEVEN_LEVEL", "attr_value": "true", "is_change": 0, "scope": "inner",
                    "container_port": -1}
            TenantServiceEnvVar.objects.create(**attr)
            attr.update({"env_name": "SEVEN_LEVEL", "env_value": "true", "enterprise_id": self.tenant.enterprise_id})
            region_api.add_service_env(service.service_region, self.tenantName, self.service.service_alias,
                                       attr)

    def addIsHttpEnv(self, service):
        # add domposer-compose
        is_compose = TenantServiceInfo.objects.filter(service_id=self.service.service_id,
                                                      language="docker-compose").count()
        if is_compose > 0:
            logger.debug("is_composer %s, IS_HTTP" % service.service_id)
            num = TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="IS_HTTP").count()
            logger.debug("start to inster Http env")
            if num < 1:
                logger.debug("inster HTTP env")
                attr = {"tenant_id": service.tenant_id, "service_id": service.service_id, "name": "IS_HTTP",
                        "attr_name": "IS_HTTP", "attr_value": "true", "is_change": 0, "scope": "inner",
                        "container_port": -1}
                TenantServiceEnvVar.objects.create(**attr)
                attr.update({"env_name": "IS_HTTP", "env_value": "true", "enterprise_id": self.tenant.enterprise_id})
                region_api.add_service_env(service.service_region, self.tenantName, self.service.service_alias,
                                           attr)
        else:
            pass

    def delSevenLevelEnv(self, service):
        num = TenantServiceEnvVar.objects.filter(service_id=service.service_id, attr_name="SEVEN_LEVEL").count()
        if num > 0:
            TenantServiceEnvVar.objects.get(service_id=service.service_id, attr_name="SEVEN_LEVEL").delete()
            region_api.delete_service_env(service.service_region, self.tenantName, self.service.service_alias,
                                          {"env_name": "SEVEN_LEVEL", "enterprise_id": self.tenant.enterprise_id})


class AllServiceInfo(AuthedView):
    def init_request(self, *args, **kwargs):
        self.cookie_region = self.request.COOKIES.get('region')
        self.tenant_region = TenantRegionInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                          region_name=self.cookie_region)

    @method_perf_time
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        result = {}
        service_ids = []
        try:
            tmp = TenantServiceInfo()
            if hasattr(tmp, 'service_origin'):
                service_list = TenantServiceInfo.objects.filter(
                    tenant_id=self.tenant.tenant_id,
                    service_region=self.cookie_region).values('ID', 'service_id', 'deploy_version')
            else:
                service_list = TenantServiceInfo.objects.filter(
                    tenant_id=self.tenant.tenant_id,
                    service_region=self.cookie_region).values('ID', 'service_id', 'deploy_version')
            if self.has_perm('tenant.list_all_services'):
                for s in service_list:
                    if s['deploy_version'] is None or s['deploy_version'] == "":
                        child1 = {}
                        child1["status"] = "uncreate"
                        child1["status_cn"] = "未部署"
                        result[s['service_id']] = child1
                    else:
                        service_ids.append(s['service_id'])
            else:
                service_pk_list = PermRelService.objects.filter(user_id=self.user.pk).values_list('service_id',
                                                                                                  flat=True)
                for s in service_list:
                    if s['ID'] in service_pk_list:
                        if s['deploy_version'] is None or s['deploy_version'] == "":
                            child1 = {}
                            child1["status"] = "uncreate"
                            child1["status_cn"] = "未部署"
                            result[s.service_id] = child1
                        else:
                            service_ids.append(s['service_id'])
            if len(service_ids) > 0:
                if self.tenant_region.service_status == 2 and self.tenant.pay_type == "payed":
                    for sid in service_ids:
                        child = {}
                        child["status"] = "owed"
                        result[sid] = child
                else:
                    service_status_list = region_api.service_status(self.cookie_region, self.tenantName,
                                                                    {"service_ids": service_ids,
                                                                     "enterprise_id": self.tenant.enterprise_id})
                    service_status_list = service_status_list["list"]
                    rt_service_ids = [rt["service_id"] for rt in service_status_list]
                    difference = list(set(service_ids).difference(set(rt_service_ids)))
                    for item in service_status_list:
                        child = {}
                        child["status"] = item["status"]
                        status_info_map = get_status_info_map(item['status'])
                        child.update(status_info_map)
                        status_cn = item.get("status_cn", None)
                        if status_cn:
                            child["status_cn"] = status_cn
                        result[item["service_id"]] = child
                    if difference:
                        for d in difference:
                            result[d] = {"status": "uncreate", "status_cn": "未部署"}


        except Exception as e:
            tempIds = ','.join(service_ids)
            logger.exception(e)
            logger.debug(self.tenant.region + "-" + tempIds + " check_service_status is error")
            for sid in service_ids:
                child = {}
                child["status"] = "failure"
                child.update(get_status_info_map('failure'))
                result[sid] = child
        return JsonResponse(result, status=200)


class AllTenantsUsedResource(AuthedView):
    def init_request(self, *args, **kwargs):
        self.cookie_region = self.request.COOKIES.get('region')
        self.tenant_region = TenantRegionInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                          region_name=self.cookie_region)

    @method_perf_time
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            service_ids = []
            serviceIds = ""
            service_list = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id,
                                                            service_region=self.cookie_region).values(
                'ID', 'service_id', 'min_node', 'min_memory')
            ids = [s["service_id"] for s in service_list]
            source_map = servicePluginResource.get_services_plugin_resource_map(ids)

            if self.has_perm('tenant.list_all_services'):
                for s in service_list:
                    service_ids.append(s['service_id'])
                    if len(serviceIds) > 0:
                        serviceIds = serviceIds + ","
                    serviceIds = serviceIds + "'" + s["service_id"] + "'"
                    plugin_memory = source_map.get(s["service_id"],0)
                    result[s['service_id'] + "_running_memory"] = s["min_node"] * (s["min_memory"]+plugin_memory)
            else:
                service_pk_list = PermRelService.objects.filter(user_id=self.user.pk).values_list('service_id',
                                                                                                  flat=True)
                for s in service_list:
                    if s['ID'] in service_pk_list:
                        service_ids.append(s['service_id'])
                        if len(serviceIds) > 0:
                            serviceIds = serviceIds + ","
                        serviceIds = serviceIds + "'" + s["service_id"] + "'"
                        plugin_memory = source_map.get(s["service_id"], 0)
                        result[s['service_id'] + "_running_memory"] = s["min_node"] * (s["min_memory"]+plugin_memory)
                        result[s['service_id'] + "_storage_memory"] = 0
            result["service_ids"] = service_ids
        except Exception as e:
            logger.exception(e)
        return JsonResponse(result)


class ServiceDetail(AuthedView):
    @method_perf_time
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                service_id=self.service.service_id)
            is_prepaid = attach_manager.is_during_monthly_payment(service_attach_info)
            if tenantAccountService.isOwnedMoney(self.tenant, self.service.service_region) and not is_prepaid:
                result["totalMemory"] = 0
                result["status"] = "Owed"
                status_info_map = get_status_info_map(result["status"])
                result.update(status_info_map)
                result["service_pay_status"] = "no_money"
                result["tips"] = "请为账户充值,然后重启应用"
            else:
                if self.service.deploy_version is None or self.service.deploy_version == "":
                    result["totalMemory"] = 0
                    result["status"] = "undeploy"
                    status_info_map = get_status_info_map(result["status"])
                    result.update(status_info_map)
                    result["service_pay_status"] = "debugging"
                    result["tips"] = "应用尚未运行"
                else:
                    body = region_api.check_service_status(self.service.service_region, self.tenantName,
                                                           self.service.service_alias, self.tenant.enterprise_id)
                    bean = body["bean"]
                    status = bean["cur_status"]
                    service_pay_status, tips, cost_money, need_pay_money, start_time_str, total_cost = self.get_pay_status(
                        status)
                    result["service_pay_status"] = service_pay_status
                    result["tips"] = tips
                    result["cost_money"] = cost_money
                    result["need_pay_money"] = need_pay_money
                    result["start_time_str"] = start_time_str
                    result["total_cost"] = total_cost
                    if status == "running":
                        result["totalMemory"] = self.service.min_node * self.service.min_memory
                    else:
                        result["totalMemory"] = 0
                    status_cn = bean.get("status_cn", None)
                    status_info_map = get_status_info_map(status)
                    result.update(status_info_map)
                    if status_cn:
                        result["status_cn"] = status_cn
                    result["status"] = status
                    # 获取服务包月信息
                    result["service_attach_info"] = model_to_dict(self.get_service_attach_info())

                    result["last_hour_consume"] = self.get_consume_detail()

        except Exception, e:
            logger.debug(self.service.service_region + "-" + self.service.service_id + " check_service_status is error")
            logger.exception(e)
            result["totalMemory"] = 0
            result['status'] = "failure"
            result["status_cn"] = "未知"
            result["service_pay_status"] = "unknown"
            result["tips"] = "服务状态未知"
        return JsonResponse(result, status=200)

    def get_consume_detail(self):
        service_consume_list = ServiceConsume.objects.filter(
            tenant_id=self.tenant.tenant_id, service_id=self.service.service_id
        ).order_by("-ID")
        lhc = {}
        if service_consume_list:
            sc = service_consume_list[0]
            consume_time = sc.time
            now = datetime.datetime.now()
            seconds = (now - consume_time).total_seconds()
            eighty_minutes = 80 * 60
            lhc["memory"] = sc.memory
            lhc["node_num"] = sc.node_num
            lhc["disk"] = sc.disk
            lhc["net"] = sc.net
            if seconds < eighty_minutes:
                lhc["memory_money"] = sc.memory_money
                lhc["disk_money"] = sc.disk_money
                lhc["net_money"] = sc.net_money
            else:
                lhc["memory_money"] = 0
                lhc["disk_money"] = 0
                lhc["net_money"] = 0

        else:

            tss = TenantServiceStatics.objects.filter(service_id=self.service.service_id,
                                                      tenant_id=self.tenant.tenant_id).order_by("-ID")[:1]
            if tss:
                ts = tss[0]
                lhc["memory"] = ts.node_memory
                lhc["node_num"] = ts.node_num
                lhc["disk"] = ts.storage_disk
                lhc["net"] = ts.flow
                lhc["memory_money"] = 0.0
                lhc["disk_money"] = 0.0
                lhc["net_money"] = 0.0
            else:
                lhc["memory"] = self.service.min_memory
                lhc["node_num"] = self.service.min_node
                lhc["disk"] = 0
                lhc["net"] = 0
                lhc["memory_money"] = 0.0
                lhc["disk_money"] = 0.0
                lhc["net_money"] = 0.0
        return lhc

    def get_pay_status(self, service_current_status):

        rt_status = "unknown"
        rt_tips = "应用状态未知"
        rt_money = 0.0
        need_pay_money = 0.0
        start_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status = service_current_status
        now = datetime.datetime.now()
        service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                            service_id=self.service.service_id)
        buy_start_time = service_attach_info.buy_start_time
        buy_end_time = service_attach_info.buy_end_time
        memory_pay_method = service_attach_info.memory_pay_method
        disk_pay_method = service_attach_info.disk_pay_method

        service_consume_list = ServiceConsume.objects.filter(tenant_id=self.tenant.tenant_id,
                                                             service_id=self.service.service_id).order_by("-ID")
        last_hour_cost = None
        total_cost = 0
        if service_consume_list:
            last_hour_cost = service_consume_list[0]
            diff = (now - last_hour_cost.time).total_seconds()
            if diff < 80 * 60:
                rt_money = last_hour_cost.pay_money
            total_cost = sum([consume.pay_money for consume in service_consume_list])

        service_unpay_bill_list = ServiceFeeBill.objects.filter(service_id=self.service.service_id,
                                                                tenant_id=self.tenant.tenant_id, pay_status="unpayed")
        buy_start_time_str = buy_start_time.strftime("%Y-%m-%d %H:%M:%S")
        diff_minutes = int((buy_start_time - now).total_seconds() / 60)
        if status == "running":
            if diff_minutes > 0:
                if memory_pay_method == "prepaid" or disk_pay_method == "prepaid":
                    if service_unpay_bill_list:
                        rt_status = "wait_for_pay"
                        rt_tips = "请于{0}前支付{1}元".format(buy_start_time_str, service_unpay_bill_list[0].prepaid_money)
                        need_pay_money = service_unpay_bill_list[0].prepaid_money
                        start_time_str = buy_start_time_str
                    else:
                        rt_status = "soon"
                        rt_tips = "将于{0}开始计费".format(buy_start_time_str)
                else:
                    rt_status = "soon"
                    rt_tips = "将于{0}开始计费".format(buy_start_time_str)
            else:
                if memory_pay_method == "prepaid" or disk_pay_method == "prepaid":
                    if now < buy_end_time:
                        rt_status = "show_money"
                        rt_tips = "包月包年项目于{0}到期".format(buy_end_time.strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        rt_status = "show_money"
                        rt_tips = "包月包年项目已于{0}到期,应用所有项目均按需结算".format(buy_end_time.strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    rt_status = "show_money"
                    rt_tips = "当前应用所有项目均按小时结算"
        else:
            if diff_minutes > 0:
                rt_status = "debugging"
                rt_tips = "应用尚未运行"
            else:
                rt_status = "show_money"
                rt_tips = "应用尚未运行"

        return rt_status, rt_tips, rt_money, need_pay_money, start_time_str, total_cost

    def get_service_attach_info(self):
        try:
            return ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id)
        except ServiceAttachInfo.DoesNotExist:
            return self.generate_service_attach_info()

    def generate_service_attach_info(self):
        service_attach_info = ServiceAttachInfo()
        service_attach_info.tenant_id = self.tenant.tenant_id
        service_attach_info.service_id = self.service.service_id
        service_attach_info.memory_pay_method = "postpaid"
        service_attach_info.disk_pay_method = "postpaid"
        service_attach_info.min_memory = self.service.min_memory
        service_attach_info.min_node = self.service.min_node
        service_attach_info.disk = 0
        service_attach_info.pre_paid_period = 0
        service_attach_info.pre_paid_money = 0
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        service_attach_info.buy_start_time = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        service_attach_info.buy_end_time = datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        service_attach_info.create_time = datetime.datetime.now()
        service_attach_info.region = self.service.service_region
        service_attach_info.save()
        return service_attach_info


class ServiceNetAndDisk(AuthedView):
    @method_perf_time
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            result["memory"] = self.service.min_node * self.service.min_memory
            result["disk"] = 0
            result["bytesin"] = 0
            result["bytesout"] = 0
            result["disk_memory"] = 0
        except Exception, e:
            logger.exception(e)
        return JsonResponse(result)


class ServiceLog(AuthedView):
    @method_perf_time
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        try:
            if self.service.deploy_version is None or self.service.deploy_version == "":
                return JsonResponse({})
            else:
                action = request.GET.get("action", "")
                service_id = self.service.service_id
                tenant_id = self.service.tenant_id
                if action == "operate":
                    events = ServiceEvent.objects.filter(service_id=service_id).order_by("-start_time")
                    reEvents = []
                    for event in list(events):
                        eventRe = {}
                        eventRe["start_time"] = event.start_time
                        eventRe["end_time"] = event.end_time
                        eventRe["user_name"] = event.user_name
                        eventRe["message"] = event.message
                        eventRe["type"] = event.type
                        eventRe["status"] = event.status
                        reEvents.append(eventRe)
                    result = {}
                    result["log"] = reEvents
                    result["num"] = len(reEvents)
                    return JsonResponse(result)
                elif action == "service":
                    data = {}
                    data["tenant_id"] = tenant_id
                    data['lines'] = 50
                    data["enterprise_id"] = self.tenant.enterprise_id
                    body = region_api.get_service_logs(self.service.service_region, self.tenantName,
                                                       self.service.service_alias, data)
                    return JsonResponse(body)
                elif action == "compile":
                    event_id = request.GET.get("event_id", "")
                    body = {}
                    if event_id != "":
                        body["tenant_id"] = tenant_id
                        body["event_id"] = event_id
                        # TODO v2 api修改
                        body = regionClient.get_compile_log(self.service.service_region, service_id, json.dumps(body))
                    return JsonResponse(body)
        except Exception as e:
            logger.info("%s" % e)
        return JsonResponse({})


class ServiceCheck(AuthedView):
    @method_perf_time
    @perm_required('manage_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            requestNumber = request.GET.get("requestNumber", "0")
            reqNum = int(requestNumber)
            if reqNum > 0 and reqNum % 30 == 0:
                # 发送请求
                codeRepositoriesService.codeCheck(self.service)

            body = region_api.get_service_language(self.service.service_region, self.service.service_id,
                                                   self.tenantName)
            bean = body["bean"]
            if bean:
                check_type = bean["CheckType"]
                if check_type == 'first_check':
                    dependency = bean["Condition"]
                    dps = json.loads(dependency)
                    language = dps["language"]
                    if language and language != "no":
                        try:
                            tse = TenantServiceEnv.objects.get(service_id=self.service.service_id)
                            tse.language = language
                            tse.check_dependency = dependency
                            tse.save()
                        except TenantServiceEnv.DoesNotExist:
                            tse = TenantServiceEnv(service_id=self.service.service_id, language=language,
                                                   check_dependency=dependency)
                            tse.save()
                        if language != "false":
                            if language.find("Java") > -1 and self.service.min_memory < 512:
                                self.service.min_memory = 512
                            self.service.language = language
                            self.service.save()

            if not self.service.language:
                tse = TenantServiceEnv.objects.get(service_id=self.service.service_id)
                dps = json.loads(tse.check_dependency)
                if dps["language"] == "false":
                    result["status"] = "check_error"
                else:
                    result["status"] = "checking"
            else:
                result["status"] = "checked"
                result["language"] = self.service.language
        except Exception as e:
            logger.exception(e)
            result["status"] = "checking"
            logger.debug(self.service.service_id + " not upload code")
        return JsonResponse(result)


class ServiceDomainManager(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            tenantService = self.service
            domain_name = request.POST["domain_name"]
            action = request.POST["action"]
            zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
            match = zhPattern.search(domain_name.decode('utf-8'))
            container_port = request.POST.get("multi_port_bind", '0')
            if match:
                result["status"] = "failure"
                return JsonResponse(result)

            if action == "start":
                domainNum = ServiceDomain.objects.filter(domain_name=domain_name).count()
                if domainNum > 0:
                    result["status"] = "exist"
                    return JsonResponse(result)

                protocol = request.POST.get("protocol", "http")

                certificate_info = None
                if protocol != 'http':
                    certificate_id = request.POST.get("certificate_id", None)
                    if certificate_id:
                        certificate_id = int(certificate_id)
                        certificate_info = ServiceDomainCertificate.objects.get(ID=certificate_id)
                    else:
                        return JsonResponse({"status": "failure", "msg": "证书不能为空"})

                data = {}
                data["uuid"] = make_uuid(domain_name)
                data["domain_name"] = domain_name
                data["service_alias"] = self.serviceAlias
                data["tenant_id"] = self.tenant.tenant_id
                data["tenant_name"] = self.tenantName
                data["service_port"] = int(container_port)
                data["protocol"] = protocol
                data["add_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data["add_user"] = self.user.nick_name
                data["enterprise_id"] = self.tenant.enterprise_id
                if certificate_info:
                    data["certificate"] = certificate_info.certificate
                    data["private_key"] = certificate_info.private_key
                    data["certificate_name"] = certificate_info.alias
                else:
                    data["certificate"] = ""
                    data["private_key"] = ""
                    data["certificate_name"] = ""

                region_api.bindDomain(self.service.service_region, self.tenantName, self.serviceAlias, data)

                domain = {}
                domain["service_id"] = self.service.service_id
                domain["service_name"] = tenantService.service_alias
                domain["domain_name"] = domain_name
                domain["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                domain["container_port"] = int(container_port)
                domain["protocol"] = protocol
                domain["certificate_id"] = certificate_info.ID if certificate_info else 0
                domaininfo = ServiceDomain(**domain)
                domaininfo.save()

                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'domain_add', True)
            elif action == "close":
                servicerDomain = ServiceDomain.objects.get(service_id=self.service.service_id,
                                                           container_port=container_port, domain_name=domain_name)
                data = {}
                data["service_id"] = servicerDomain.service_id
                data["domain"] = servicerDomain.domain_name
                data["pool_name"] = self.tenantName + "@" + self.serviceAlias + ".Pool"
                data["container_port"] = int(container_port)
                data["enterprise_id"] = self.tenant.enterprise_id
                try:
                    region_api.unbindDomain(self.service.service_region, self.tenantName, self.serviceAlias, data)
                except region_api.CallApiError as e:
                    if e.status != 404:
                        raise e
                ServiceDomain.objects.filter(service_id=self.service.service_id, container_port=container_port,
                                             domain_name=domain_name).delete()
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'domain_delete', True)
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'domain_manage', False)
        return JsonResponse(result)


class DomainCertificationManager(AuthedView):
    @perm_required('manage_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            certifactes = ServiceDomainCertificate.objects.filter(tenant_id=self.tenant.tenant_id)
            data = []
            for sdc in certifactes:
                certifacte = {}
                certifacte["certificate"] = sdc.certificate
                certifacte["alias"] = sdc.alias
                certifacte["private_key"] = sdc.private_key
                certifacte["id"] = sdc.ID
                data.append(certifacte)
            result["data"] = data

        except Exception as e:
            logger.exception(e)
        return JsonResponse(result, status=200)

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        certificate = request.POST.get("certificate", "")
        private_key = request.POST.get("private_key", "")
        alias = request.POST.get("alias", "")
        try:
            if certificate and private_key and alias:
                r = re.compile("^[A-Za-z0-9]+$")
                if not r.match(alias):
                    return JsonResponse({"status": "failure", "msg": "证书别名只能是数字和字母的组合"})
                certificate_list = ServiceDomainCertificate.objects.filter(alias=alias)
                if len(list(certificate_list)) > 0:
                    return JsonResponse({"status": "failure", "msg": "证书别名已存在"})
                service_domain_certificate = {}
                service_domain_certificate["tenant_id"] = self.tenant.tenant_id
                service_domain_certificate["certificate"] = certificate
                service_domain_certificate["private_key"] = private_key
                service_domain_certificate["alias"] = alias
                service_domain_certificate["create_time"] = datetime.datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S')
                certificate_info = ServiceDomainCertificate(**service_domain_certificate)
                certificate_info.save()
                result['status'] = "success"
                result['msg'] = "证书添加成功"
            else:
                result["status"] = "failure"
                result["msg"] = "参数不能为空"
                return JsonResponse
        except Exception as e:
            result["status"] = "failure"
            result["msg"] = "系统异常"
            logger.exception(e)

        return JsonResponse(result, status=200)


class ServiceEnvVarManager(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            id = request.POST["id"]
            nochange_name = request.POST["nochange_name"]
            name = request.POST["name"]
            attr_name = request.POST["attr_name"]
            attr_value = request.POST["attr_value"]
            attr_id = request.POST["attr_id"]
            name_arr = name.split(",")
            attr_name_arr = attr_name.split(",")
            attr_value_arr = attr_value.split(",")
            attr_id_arr = attr_id.split(",")
            logger.debug(attr_id)

            isNeedToRsync = True
            total_ids = []
            if id != "" and nochange_name != "":
                id_arr = id.split(',')
                nochange_name_arr = nochange_name.split(',')
                if len(id_arr) == len(nochange_name_arr):
                    for index, curid in enumerate(id_arr):
                        total_ids.append(curid)
                        stsev = TenantServiceEnvVar.objects.get(ID=curid)
                        stsev.attr_name = nochange_name_arr[index]
                        stsev.save()
            if name != "" and attr_name != "" and attr_value != "":
                if len(name_arr) == len(attr_name_arr) and len(attr_value_arr) == len(attr_name_arr):
                    # first delete old item
                    for item in attr_id_arr:
                        total_ids.append(item)
                    if len(total_ids) > 0:
                        TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).exclude(
                            ID__in=total_ids).delete()

                    # update and save env
                    for index, cname in enumerate(name_arr):
                        tmpId = attr_id_arr[index]
                        attr_name = attr_name_arr[index]
                        attr_value = attr_value_arr[index]
                        if int(tmpId) > 0:
                            tsev = TenantServiceEnvVar.objects.get(ID=int(tmpId))
                            tsev.attr_name = attr_name.lstrip().rstrip()
                            tsev.attr_value = attr_value.lstrip().rstrip()
                            tsev.save()
                        else:
                            tenantServiceEnvVar = {}
                            tenantServiceEnvVar["tenant_id"] = self.service.tenant_id
                            tenantServiceEnvVar["service_id"] = self.service.service_id
                            tenantServiceEnvVar["name"] = cname
                            tenantServiceEnvVar["attr_name"] = attr_name.lstrip().rstrip()
                            tenantServiceEnvVar["attr_value"] = attr_value.lstrip().rstrip()
                            tenantServiceEnvVar["is_change"] = True
                            TenantServiceEnvVar(**tenantServiceEnvVar).save()
            else:
                if len(total_ids) > 0:
                    TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).exclude(
                        ID__in=total_ids).delete()

            # sync data to region
            if isNeedToRsync:
                baseService.create_service_env(self.tenant, self.service.service_id,
                                               self.service.service_region)
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)


class ServiceBranch(AuthedView):
    def get_gitlab_branchs(self, parsed_git_url):
        project_id = self.service.git_project_id
        if project_id > 0:
            branchlist = codeRepositoriesService.getProjectBranches(project_id)
            branchs = [e['name'] for e in branchlist]
            return branchs
        else:
            return [self.service.code_version]

    def get_github_branchs(self, parsed_git_url):
        user = Users.objects.only('github_token').get(pk=self.service.creater)
        token = user.github_token
        owner = parsed_git_url.owner
        repo = parsed_git_url.repo
        branchs = []
        try:
            repos = codeRepositoriesService.gitHub_ReposRefs(owner, repo, token)
            reposList = json.loads(repos)
            for reposJson in reposList:
                ref = reposJson["ref"]
                branchs.append(ref.split("/")[2])
        except Exception, e:
            logger.error('client_error', e)
        return branchs

    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        parsed_git_url = git_url_parse(self.service.git_url)
        host = parsed_git_url.host
        if host is not None:
            if parsed_git_url.host == 'code.goodrain.com':
                branchs = self.get_gitlab_branchs(parsed_git_url)
            elif parsed_git_url.host.endswith('github.com'):
                branchs = self.get_github_branchs(parsed_git_url)
            else:
                branchs = [self.service.code_version]
            result = {"current": self.service.code_version, "branchs": branchs}
            return JsonResponse(result, status=200)
        else:
            return JsonResponse({}, status=200)

    @perm_required('deploy_service')
    def post(self, request, *args, **kwargs):
        branch = request.POST.get('branch')
        self.service.code_version = branch
        self.service.save(update_fields=['code_version'])
        return JsonResponse({"ok": True}, status=200)


class ServicePort(AuthedView):
    def check_port_alias(self, port_alias):
        if not re.match(r'^[A-Z][A-Z0-9_]*$', port_alias):
            return False, u"格式不符合要求^[A-Z][A-Z0-9_]"

        if TenantServicesPort.objects.filter(service_id=self.service.service_id, port_alias=port_alias).exists():
            return False, u"别名冲突"

        return True, port_alias

    def check_port(self, port):
        # if not re.match(r'^\d{2,5}$', str(port)):
        #     return False, u"格式不符合要求^\d{2,5}"

        if self.service.language and "docker" not in self.service.language:
            if port > 65535 or port < 1025:
                return False, u"端口号必须在1025~65535之间！"
        else:
            if port > 65535 or port < 1:
                return False, u"端口号必须在1~65535之间！"

        if TenantServicesPort.objects.filter(service_id=self.service.service_id, container_port=port).exists():
            return False, u"端口冲突"

        return True, port

    def switch_service_port(self, action, deal_port):
        """打开关闭端口"""
        # 标识操作是否成功
        is_success = True
        data = {"success": True, "info": u"更改成功", "code": 200}
        if action == "open_outer":
            if deal_port.protocol != "http":
                stream_outer_num = TenantServicesPort.objects.filter(service_id=self.service.service_id,
                                                                    is_outer_service=True).exclude(protocol="http").count()
                if stream_outer_num > 0:
                    is_success = False
                    data = {"success": False, "code": 410, "info": u"stream协议族外部访问只能开启一个"}
                    return is_success, data
            deal_port.is_outer_service = True
            body = region_api.manage_outer_port(self.service.service_region, self.tenantName,
                                                self.service.service_alias,
                                                deal_port.container_port,
                                                {"operation": "open", "enterprise_id": self.tenant.enterprise_id})
            logger.debug("open outer port body {}".format(body))
            lb_mapping_port = body["bean"]["port"]

            deal_port.lb_mapping_port = lb_mapping_port
        elif action == "close_outer":
            deal_port.is_outer_service = False
            region_api.manage_outer_port(self.service.service_region, self.tenantName, self.service.service_alias,
                                         deal_port.container_port,
                                         {"operation": "close", "enterprise_id": self.tenant.enterprise_id})
        elif action == "close_inner":
            deal_port.is_inner_service = False
            region_api.manage_inner_port(self.service.service_region, self.tenantName, self.service.service_alias,
                                         deal_port.container_port,
                                         {"operation": "close", "enterprise_id": self.tenant.enterprise_id})
        elif action == "open_inner":
            if not deal_port.port_alias:
                is_success = False
                data = {"success": False, "code": 409, "info": u"请先为端口设置别名"}
                return is_success, data
            deal_port.is_inner_service = True
            baseService = BaseTenantService()

            # mapping_port = baseService.prepare_mapping_port(self.service, deal_port.container_port)
            # logger.debug("generate new mapping port {0}".format(mapping_port))
            mapping_port = deal_port.container_port
            deal_port.mapping_port = mapping_port
            deal_port.save(update_fields=['mapping_port'])
            # 删除跟此端口有关的环境变量
            TenantServiceEnvVar.objects.filter(service_id=deal_port.service_id,
                                               container_port=deal_port.container_port).delete()
            baseService.saveServiceEnvVar(self.service.tenant_id, self.service.service_id, deal_port.container_port,
                                          u"连接地址",
                                          deal_port.port_alias + "_HOST", "127.0.0.1", False, scope="outer")
            baseService.saveServiceEnvVar(self.service.tenant_id, self.service.service_id, deal_port.container_port,
                                          u"端口",
                                          deal_port.port_alias + "_PORT", mapping_port, False, scope="outer")

            port_envs = TenantServiceEnvVar.objects.filter(service_id=deal_port.service_id,
                                                           container_port=deal_port.container_port)
            # 原有reigon_api是先删除原有的端口相关的env,然后添加
            for env in port_envs:
                region_api.delete_service_env(self.service.service_region,
                                              self.tenantName,
                                              self.service.service_alias,
                                              {"env_name": env.attr_name,
                                               "enterprise_id": self.tenant.enterprise_id})
                add_attr = {"container_port": env.container_port, "env_name": env.attr_name,
                            "env_value": env.attr_value, "is_change": env.is_change, "name": env.name,
                            "scope": env.scope, "enterprise_id": self.tenant.enterprise_id}
                region_api.add_service_env(self.service.service_region,
                                           self.tenantName,
                                           self.service.service_alias,
                                           add_attr)
            res = region_api.manage_inner_port(self.service.service_region, self.tenantName, self.service.service_alias,
                                         deal_port.container_port,
                                         {"operation": "open", "enterprise_id": self.tenant.enterprise_id})

        if action == 'close_outer' or action == 'open_outer':
            if self.service.port_type == "one_outer":
                # 检查服务已经存在对外端口
                outer_port_num = TenantServicesPort.objects.filter(service_id=self.service.service_id,
                                                                   is_outer_service=True).count()
                if outer_port_num > 1:
                    cur_port_type = "multi_outer"
                    self.service.port_type = cur_port_type
                    self.service.save()
        # 保存本地服务信息
        deal_port.save()
        return is_success, data

    def change_port_info(self, action, deal_port, request):
        """修改端口信息"""
        is_success = True
        data = {"success": True, "info": u"更改成功", "code": 200}
        body = {"container_port": deal_port.container_port, "is_inner_service": deal_port.is_inner_service,
                "is_outer_service": deal_port.is_outer_service, "mapping_port": deal_port.mapping_port,
                "port_alias": deal_port.port_alias, "protocol": deal_port.protocol,
                "tenant_id": self.tenant.tenant_id, "service_id": self.service.service_id}
        if action == "change_protocol":
            protocol = request.POST.get("value")
            deal_port.protocol = protocol
            if protocol != "http":
                if TenantServicesPort.objects.filter(service_id=self.service.service_id,
                                                     container_port=deal_port.container_port,
                                                     is_outer_service=True).count() > 0:
                    return False, {"success": False, "code": 400, "info": u"请关闭外部访问"}

                stream_outer_num = TenantServicesPort.objects.filter(
                        service_id=self.service.service_id,is_outer_service=True).exclude(protocol="http").count()
                if stream_outer_num > 0 and deal_port.is_outer_service:
                    is_success = False
                    data = {"success": False, "code": 410, "info": u"stream协议族外部访问只能开启一个"}
                    return is_success, data
            body["protocol"] = protocol
            region_api.update_service_port(self.service.service_region, self.tenantName, self.service.service_alias,
                                           {"port": [body], "enterprise_id": self.tenant.enterprise_id})
            deal_port.save()
        elif action == "change_port_alias":
            new_port_alias = request.POST.get("value")
            success, reason = self.check_port_alias(new_port_alias)
            tenant_alias_num = TenantServicesPort.objects.filter(tenant_id=self.service.tenant_id,
                                                                 port_alias=new_port_alias).count()
            if not success:
                return False, {"success": False, "info": reason, "code": 400}
            else:
                old_port_alias = deal_port.port_alias
                deal_port.port_alias = new_port_alias
                envs = TenantServiceEnvVar.objects.filter(service_id=deal_port.service_id,
                                                          container_port=deal_port.container_port)
                for env in envs:
                    old_env_attr_name = env.attr_name
                    new_attr_name = new_port_alias + env.attr_name.replace(old_port_alias, '')
                    env.attr_name = new_attr_name
                    # 更新region环境变量
                    # step 1 先删除原有的
                    region_api.delete_service_env(self.service.service_region,
                                                  self.tenantName,
                                                  self.service.service_alias,
                                                  {"env_name": old_env_attr_name,
                                                   "enterprise_id": self.tenant.enterprise_id})
                    # step 2 添加新的
                    add_env = {"container_port": env.container_port, "env_name": env.attr_name,
                               "env_value": env.attr_value, "is_change": env.is_change, "name": env.name,
                               "scope": env.scope, "enterprise_id": self.tenant.enterprise_id}
                    region_api.add_service_env(self.service.service_region,
                                               self.tenantName,
                                               self.service.service_alias,
                                               add_env)
                    env.save()
                # 更新region的端口信息
                body["port_alias"] = new_port_alias
                region_api.update_service_port(self.service.service_region, self.tenantName, self.service.service_alias,
                                               {"port": [body], "enterprise_id": self.tenant.enterprise_id})
                deal_port.save()
        elif action == "change_port":
            new_port = int(request.POST.get("value"))
            success, reason = self.check_port(new_port)
            if not success:
                return False, {"success": False, "info": reason, "code": 400}
            else:
                if TenantServicesPort.objects.filter(service_id=self.service.service_id,
                                                     container_port=deal_port.container_port,
                                                     is_outer_service=True).count() > 0:
                    return False, {"success": False, "code": 400, "info": u"请关闭外部访问"}

                if TenantServicesPort.objects.filter(service_id=self.service.service_id,
                                                     container_port=deal_port.container_port,
                                                     is_inner_service=True).count() > 0:
                    return False, {"success": False, "code": 400, "info": u"请关闭对外服务"}

            old_port = deal_port.container_port
            deal_port.container_port = new_port
            envs = TenantServiceEnvVar.objects.filter(service_id=deal_port.service_id, container_port=old_port)
            for env in envs:
                # 更新region 环境变量
                # step 1 先删除原有的
                env.container_port = new_port
                region_api.delete_service_env(self.service.service_region,
                                              self.tenantName,
                                              self.service.service_alias,
                                              {"env_name": deal_port.port_alias,
                                               "enterprise_id": self.tenant.enterprise_id})
                # step 2 添加新的
                add_env = {"container_port": env.container_port, "env_name": env.attr_name,
                           "env_value": env.attr_value, "is_change": env.is_change, "name": env.name,
                           "scope": env.scope, "enterprise_id": self.tenant.enterprise_id}
                region_api.add_service_env(self.service.service_region,
                                           self.tenantName,
                                           self.service.service_alias,
                                           add_env)
                env.save()
            # 更新region端口信息
            body["container_port"] = new_port
            region_api.update_service_port(self.service.service_region, self.tenantName, self.service.service_alias,
                                           {"port": [body], "enterprise_id": self.tenant.enterprise_id})
            deal_port.save()

        return is_success, data

    @perm_required("manage_service")
    def post(self, request, port, *args, **kwargs):

        try:
            action = request.POST.get("action")
            deal_port = TenantServicesPort.objects.get(service_id=self.service.service_id, container_port=int(port))

            port_switch_action = ("open_outer", "close_outer", "close_inner", "open_inner")
            change_port_actions = ("change_protocol", "change_port_alias", "change_port")
            result = {"success": False, "code": 500, "info": u"系统异常"}
            if action in port_switch_action:
                is_success, result = self.switch_service_port(action, deal_port)
            if action in change_port_actions:
                is_success, result = self.change_port_info(action, deal_port, request)
            if action not in port_switch_action and action not in change_port_actions:
                result = {"success": False, "code": 405, "info": u"操作不允许"}

            return JsonResponse(result, status=200)
        except Exception as e:
            logger.exception(e)
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_outer', False)
            return JsonResponse({"success": False, "info": u"更改失败", "code": 500}, status=200)

    def get(self, request, port, *args, **kwargs):
        deal_port = TenantServicesPort.objects.get(service_id=self.service.service_id, container_port=int(port))
        data = {"environment": []}

        if deal_port.is_inner_service:
            for port_env in TenantServiceEnvVar.objects.filter(service_id=self.service.service_id,
                                                               container_port=deal_port.container_port):
                data["environment"].append({
                    "desc": port_env.name, "name": port_env.attr_name, "value": port_env.attr_value
                })
        if deal_port.is_outer_service:
            service_region = self.service.service_region
            if deal_port.protocol != 'http':
                cur_region = service_region.replace("-1", "")
                domain = "{0}.{1}.{2}-s1.goodrain.net".format(self.service.service_alias, self.tenant.tenant_name,
                                                              cur_region)
                if settings.STREAM_DOMAIN_URL[service_region] != "":
                    domain = settings.STREAM_DOMAIN_URL[service_region]

                data["outer_service"] = {
                    "domain": domain,
                    "port": deal_port.mapping_port,
                }
                if deal_port.lb_mapping_port != 0:
                    data["outer_service"]["port"] = deal_port.lb_mapping_port
            elif deal_port.protocol == 'http':
                data["outer_service"] = {
                    "domain": "{0}.{1}{2}".format(self.service.service_alias, self.tenant.tenant_name,
                                                  settings.WILD_DOMAINS[service_region]),
                    "port": settings.WILD_PORTS[self.service.service_region]
                }

        return JsonResponse(data, status=200)


class ServiceEnv(AuthedView):
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'add_attr':
            name = request.POST.get('name', '')
            attr_name = request.POST.get('attr_name')
            attr_value = request.POST.get('attr_value')
            scope = request.POST.get('scope', 'inner')
            attr_name = attr_name.lstrip().rstrip()
            attr_value = attr_value.lstrip().rstrip()

            form = EnvCheckForm(request.POST)
            if not form.is_valid():
                return JsonResponse({"success": False, "code": 400, "info": u"变量名不合法"})

            if TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, attr_name=attr_name).exists():
                return JsonResponse({"success": False, "code": 409, "info": u"变量名冲突"})
            else:
                attr = {
                    "tenant_id": self.service.tenant_id, "service_id": self.service.service_id, "name": name,
                    "attr_name": attr_name, "attr_value": attr_value, "is_change": True, "scope": scope
                }
                env = TenantServiceEnvVar.objects.create(**attr)
                attr.update(
                    {"env_name": attr_name, "env_value": attr_value, "enterprise_id": self.tenant.enterprise_id})
                region_api.add_service_env(self.service.service_region, self.tenant.tenant_name,
                                           self.service.service_alias, attr)
                return JsonResponse(
                    {"success": True, "info": u"创建成功", "pk": env.pk, "attr_name": attr_name, "attr_value": attr_value,
                     "name": name})
        elif action == 'del_attr':
            attr_name = request.POST.get("attr_name")
            TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, attr_name=attr_name).delete()

            region_api.delete_service_env(self.service.service_region, self.tenant.tenant_name,
                                          self.service.service_alias, {"env_name": attr_name,
                                                                       "enterprise_id": self.tenant.enterprise_id})
            return JsonResponse({"success": True, "info": u"删除成功"})


class ServiceMnt(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        action = request.POST.get('action')
        try:
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            if action == 'add':
                dep_vol_ids = json.loads(request.POST.get('dep_vol_ids', '[]'))
                logger.debug('dep_vols {0}'.format(dep_vol_ids))

                ret, vol_names, message = baseService.batch_add_dep_volume_v2(
                    self.tenant, self.service, dep_vol_ids)
                if not ret and not vol_names:
                    return JsonResponse(data={'status': 'failure', 'msg': message})
                if not ret and vol_names:
                    return JsonResponse(data={
                        'status': 'failure', 'msg': '挂载目录{0}与当前应用已存在关联'.format(vol_names)})
                return JsonResponse(data={'status': 'success'})
            elif action == 'cancel':
                dep_vol_id = request.POST.get("dep_vol_id")
                ret = baseService.delete_dep_volume_v2(self.tenant, self.service, dep_vol_id)
                if not ret:
                    return JsonResponse(data={'status': 'failure'})
                return JsonResponse(data={'status': 'success'})
        except Exception, e:
            logger.exception(e)
            return JsonResponse(data={'status': 'failure', 'msg': e.message})


class ServiceNewPort(AuthedView):
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'add_port':
            port_port = request.POST.get('port_port', "5000")
            port_protocol = request.POST.get('port_protocol', "http")
            port_alias = request.POST.get('port_alias', "")
            port_inner = request.POST.get('port_inner', "0")
            port_outter = request.POST.get('port_outter', "0")

            if not re.match(r'^[0-9]*$', port_port):
                return JsonResponse({"success": False, "code": 400, "info": u"端口不合法"})

            port_port = int(port_port)
            port_inner = int(port_inner)
            port_outter = int(port_outter)

            if port_port <= 0:
                return JsonResponse({"success": False, "code": 400, "info": u"端口需大于零"})
            if port_inner != 0:
                if not re.match(r'^[A-Z][A-Z0-9_]*$', port_alias):
                    return JsonResponse({"success": False, "code": 400, "info": u"别名不合法"})
            # todo 判断端口别名是否重复
            tenant_alias_num = TenantServicesPort.objects.filter(tenant_id=self.service.tenant_id,
                                                                 port_alias=port_alias).count()
            if TenantServicesPort.objects.filter(service_id=self.service.service_id, container_port=port_port).exists():
                return JsonResponse({"success": False, "code": 409, "info": u"容器端口冲突"})
            mapping_port = 0
            if port_inner == 1 and port_protocol != "http":
                mapping_port = baseService.prepare_mapping_port(self.service, port_port)
            port = {
                "tenant_id": self.service.tenant_id, "service_id": self.service.service_id,
                "container_port": port_port, "mapping_port": mapping_port, "protocol": port_protocol,
                "port_alias": port_alias,
                "is_inner_service": bool(port_inner), "is_outer_service": bool(port_outter)
            }
            TenantServicesPort.objects.create(**port)
            region_api.add_service_port(self.service.service_region, self.tenant.tenant_name,
                                        self.service.service_alias,
                                        {"port": [port], "enterprise_id": self.tenant.enterprise_id})
            return JsonResponse({"success": True, "info": u"创建成功"})
        elif action == 'del_port':

            port_port = request.POST.get("port_port")
            num = ServiceDomain.objects.filter(service_id=self.service.service_id, container_port=port_port).count()
            if num > 0:
                return JsonResponse({"success": False, "code": 409, "info": u"请先解绑该端口绑定的域名"})

            if TenantServicesPort.objects.filter(service_id=self.service.service_id, container_port=port_port,
                                                 is_outer_service=True).count() > 0:
                return JsonResponse({"success": False, "code": 409, "info": u"请关闭外部访问"})

            if TenantServicesPort.objects.filter(service_id=self.service.service_id, container_port=port_port,
                                                 is_inner_service=True).count() > 0:
                return JsonResponse({"success": False, "code": 409, "info": u"请关闭对外服务"})

            TenantServicesPort.objects.filter(service_id=self.service.service_id, container_port=port_port).delete()
            TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, container_port=port_port).delete()
            ServiceDomain.objects.filter(service_id=self.service.service_id, container_port=port_port).delete()
            region_api.delete_service_port(self.service.service_region, self.tenantName, self.service.service_alias,
                                           port_port, self.tenant.enterprise_id)
            return JsonResponse({"success": True, "info": u"删除成功"})


class ServiceDockerContainer(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            data = region_api.get_service_pods(self.service.service_region, self.tenantName, self.service.service_alias,
                                               self.tenant.enterprise_id)
            for d in data["list"]:
                result[d["PodName"]] = "manager"
            logger.info(result)
        except Exception, e:
            logger.exception(e)
        return JsonResponse(result)

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        response = JsonResponse({"success": True})
        try:
            c_id = request.POST.get("c_id", "")
            h_id = request.POST.get("h_id", "")
            logger.info("c_id=" + c_id)
            logger.info("h_id=" + h_id)
            if c_id != "" and h_id != "":
                if settings.DOCKER_WSS_URL.get("is_wide_domain", False):
                    response.set_cookie('docker_h_id', h_id)
                else:
                    response.set_cookie('docker_h_id', h_id)
                response.set_cookie('docker_c_id', c_id)
                response.set_cookie('docker_s_id', self.service.service_id)
            return response
        except Exception as e:
            logger.exception(e)
            response = JsonResponse({"success": False})
        return response


class ServiceVolumeView(AuthedView):
    """添加,删除持久化数据目录"""

    SYSDIRS = ["/", "/bin", "/boot", "/dev", "/etc", "/home",
               "/lib", "/lib64", "/opt", "/proc", "/root", "/sbin",
               "/srv", "/sys", "/tmp", "/usr", "/var",
               "/usr/local", "/usr/sbin", "/usr/bin",
               ]

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        action = request.POST.get('action')
        try:
            if action == 'add':
                volume_path = request.POST.get("volume_path")
                volume_type = request.POST.get('volume_type')
                volume_name = request.POST.get('volume_name')

                if baseService.check_volume_name_uniqueness(volume_name, self.service.service_id):
                    return JsonResponse(data={"code": "400", "status": "faliure", "msg": "持久化名称重复"})

                if baseService.check_volume_path_uniqueness(volume_path, self.service.service_id):
                    return JsonResponse(data={"code": "400", "status": "faliure", "msg": "持久化路径重复"})

                if self.service.image != "goodrain.me/runner":
                    if not volume_path.startswith("/"):
                        return JsonResponse(data={'status': 'failure', 'code': '303'})
                    if volume_path in self.SYSDIRS:
                        return JsonResponse(data={'status': 'failure', 'code': '304'})
                else:
                    if not volume_path.startswith("/"):
                        volume_path = "/" + volume_path

                all_volume_path = TenantServiceVolume.objects.filter(service_id=self.service.service_id).values(
                    "volume_path"
                )
                if len(all_volume_path):
                    for path in list(all_volume_path):
                        # volume_path不能重复
                        if path["volume_path"] == volume_path:
                            result["status"] = "failure"
                            result["code"] = "305"
                            return JsonResponse(result)
                        if path["volume_path"].startswith(volume_path + "/"):
                            result["status"] = "failure"
                            result["code"] = "307"
                            return JsonResponse(result)
                        if volume_path.startswith(path["volume_path"] + "/"):
                            result["status"] = "failure"
                            result["code"] = "306"
                            return JsonResponse(result)

                volume, body = baseService.add_volume_v2(
                    self.tenant, self.service, volume_name, volume_path, volume_type
                )
                if not volume:
                    return JsonResponse(data={"status": "failure", "code": "500", "msg": json.dumps(body)})
                result.update({
                    'volume': {
                        "ID": volume.ID,
                        "volume_name": volume_name,
                        "volume_path": volume_path,
                        "volume_type": volume_type
                    },
                    "code": "200",
                    "status": "success"
                })
                return JsonResponse(result, status=200)
            elif action == 'cancel':
                volume_id = request.POST["volume_id"]
                ret, msg = baseService.delete_volume_v2(self.tenant, self.service, int(volume_id))
                if ret:
                    return JsonResponse(data={"status": "success", "code": "200", "msg": msg}, status=200)
                return JsonResponse(data={"status": "failure", "code": "500", "msg": msg})
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
            result["code"] = "500"
        return JsonResponse(result)


class ServiceNameChangeView(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        new_service_cname = request.POST.get("new_service_cname", "")
        service_alias = request.POST.get("service_alias")
        result = {}
        try:
            if new_service_cname.strip() != "":
                TenantServiceInfo.objects.filter(service_alias=service_alias, tenant_id=self.tenant.tenant_id).update(
                    service_cname=new_service_cname)
                result["ok"] = True
                result["info"] = "修改成功"
                result["new_service_cname"] = new_service_cname
        except Exception as e:
            logger.exception(e)
            result["ok"] = False
            result["info"] = "修改失败"
        return JsonResponse(result)


class ServiceLogTypeView(AuthedView):
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            self.cookie_region = self.request.COOKIES.get('region')
            services = TenantServiceInfo.objects.filter(service_type__in=["elasticsearch", "mongodb", "influxdb"],
                                                        tenant_id=self.tenant.tenant_id,
                                                        service_region=self.cookie_region)
            i = 0
            for service in services:
                tmp = {}
                tmp["service_id"] = service.service_id
                tmp["service_cname"] = service.service_cname
                tmp["service_type"] = service.service_type
                tmp["service_alias"] = service.service_alias
                result[i] = tmp
                i += 1
        except Exception as e:
            logger.exception(e)
            result["ok"] = False
            result["info"] = "获取失败"
        return JsonResponse(result)


class DockerLogInstanceView(AuthedView):
    def make_event_ws_uri(self, default_uri):
        if default_uri != 'auto':
            return '{}/{}'.format(default_uri, 'docker_log')
        else:
            host = self.request.META.get('HTTP_HOST').split(':')[0]
            return 'ws://{}:6060/{}'.format(host, 'docker_log')

    def get(self, request, *args, **kwargs):
        result = {}
        ws_url = self.make_event_ws_uri(settings.EVENT_WEBSOCKET_URL[self.service.service_region])
        try:
            re = region_api.get_docker_log_instance(self.service.service_region, self.tenantName,
                                                    self.service.service_alias, self.tenant.enterprise_id)
            bean = re["bean"]

            result["ok"] = True
            result["host_id"] = bean["host_id"]
            result["ws_url"] = "{}?host_id={}".format(ws_url, bean["host_id"])
            return JsonResponse(result)
        except Exception as e:
            logger.exception(e)
            result["ok"] = False
            result["info"] = "获取失败.{0}".format(e.message)
        result["ws_url"] = ws_url
        return JsonResponse(result)
