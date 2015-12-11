# -*- coding: utf8 -*-
import datetime
import json

from django.db.models import Sum
from django.db.models import Max
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required

from www.models import ServiceInfo, AppServiceInfo, TenantServiceInfo, TenantRegionInfo, TenantServiceLog, PermRelService, TenantServiceRelation, TenantServiceStatics, TenantServiceInfoDelete, Users, TenantServiceEnv, TenantServiceAuth, ServiceDomain, TenantServiceEnvVar
from www.service_http import RegionServiceApi
from www.gitlab_http import GitlabApi
from www.github_http import GitHubApi
from django.conf import settings
from www.db import BaseConnection
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource
from goodrain_web.decorator import method_perf_time
from www.monitorservice.monitorhook import MonitorHook
from www.utils.giturlparse import parse as git_url_parse

import logging
from django.template.defaultfilters import length
logger = logging.getLogger('default')

gitClient = GitlabApi()
githubClient = GitHubApi()

regionClient = RegionServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()


class AppDeploy(AuthedView):

    @method_perf_time
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        data = {}
        self.tenant_region = TenantRegionInfo.objects.get(
            tenant_id=self.service.tenant_id, region_name=self.service.service_region)
        if self.tenant_region.service_status == 2 and self.tenant.pay_type == "payed":
            data["status"] = "owed"
            return JsonResponse(data, status=200)

        if self.service.ID > 598 and (self.service.language is None or self.service.language == ""):
            data["status"] = "language"
            return JsonResponse(data, status=200)

        tenant_id = self.tenant.tenant_id
        service_id = self.service.service_id
        oldVerion = self.service.deploy_version
        if oldVerion is not None and oldVerion != "":
            if not baseService.is_user_click(self.service.service_region, service_id):
                data["status"] = "often"
                return JsonResponse(data, status=200)

        # temp record service status
        temData = {}
        temData["service_id"] = service_id
        temData["status"] = 2
        old_status = regionClient.updateTenantServiceStatus(self.service.service_region, service_id, json.dumps(temData))
        # calculate resource
        flag = tenantUsedResource.predict_next_memory(self.tenant, 0)
        if not flag:
            if self.tenant.pay_type == "free":
                data["status"] = "over_memory"
            else:
                data["status"] = "over_money"
            temData["service_id"] = service_id
            temData["status"] = old_status
            regionClient.updateTenantServiceStatus(self.service.service_region, service_id, json.dumps(temData))
            return JsonResponse(data, status=200)
        try:
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

            clone_url = self.service.git_url
            if self.service.code_from == "github":
                code_user = clone_url.split("/")[3]
                code_project_name = clone_url.split("/")[4].split(".")[0]
                createUser = Users.objects.get(user_id=self.service.creater)
                clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
            body["deploy_version"] = self.service.deploy_version
            body["gitUrl"] = "--branch " + self.service.code_version + " --depth 1 " + clone_url
            body["operator"] = str(self.user.nick_name)

            regionClient.build_service(self.service.service_region, service_id, json.dumps(body))
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_deploy', True)

            data["status"] = "success"
            return JsonResponse(data, status=200)
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_deploy', False)
        return JsonResponse(data, status=500)


class ServiceManage(AuthedView):

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        self.tenant_region = TenantRegionInfo.objects.get(
            tenant_id=self.service.tenant_id, region_name=self.service.service_region)
        if self.tenant_region.service_status == 2 and self.tenant.pay_type == "payed":
            result["status"] = "owed"
            return JsonResponse(result, status=200)

        oldVerion = self.service.deploy_version
        if oldVerion is not None and oldVerion != "":
            if not baseService.is_user_click(self.service.service_region, self.service.service_id):
                result["status"] = "often"
                return JsonResponse(result, status=200)

        action = request.POST["action"]
        if action == "stop":
            try:
                body = {}
                body["operator"] = str(self.user.nick_name)
                regionClient.stop(self.service.service_region, self.service.service_id, json.dumps(body))
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_stop', True)
                result["status"] = "success"
            except Exception, e:
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_stop', False)
        elif action == "restart":
            try:
                # temp record service status
                temData = {}
                temData["service_id"] = self.service.service_id
                temData["status"] = 2
                old_status = regionClient.updateTenantServiceStatus(
                    self.service.service_region, self.service.service_id, json.dumps(temData))
                # calculate resource
                flag = tenantUsedResource.predict_next_memory(self.tenant, 0)
                if not flag:
                    if self.tenant.pay_type == "free":
                        result["status"] = "over_memory"
                    else:
                        result["status"] = "over_money"
                    temData["service_id"] = self.service.service_id
                    temData["status"] = old_status
                    regionClient.updateTenantServiceStatus(self.service.service_region,
                                                           self.service.service_id, json.dumps(temData))
                    return JsonResponse(result, status=200)

                self.service.deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                self.service.save()
                body = {}
                body["deploy_version"] = self.service.deploy_version
                body["operator"] = str(self.user.nick_name)
                regionClient.restart(self.service.service_region, self.service.service_id, json.dumps(body))
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_start', True)
                result["status"] = "success"
            except Exception, e:
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_start', False)
        elif action == "delete":
            try:
                dependSids = TenantServiceRelation.objects.filter(dep_service_id=self.service.service_id).values("service_id")
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
                    result["status"] = "dependency"
                    return JsonResponse(result)
                data = self.service.toJSON()
                newTenantServiceDelete = TenantServiceInfoDelete(**data)
                newTenantServiceDelete.save()
                try:
                    regionClient.delete(self.service.service_region, self.service.service_id)
                except Exception as e:
                    logger.exception(e)
                if self.service.code_from == 'gitlab_new' and self.service.git_project_id > 0:
                    same_repo_services = TenantServiceInfo.objects.only('ID').filter(
                        tenant_id=self.service.tenant_id, git_url=self.service.git_url).exclude(service_id=self.service.service_id)
                    if not same_repo_services:
                        gitClient.deleteProject(self.service.git_project_id)
                    gitClient.deleteProject(self.service.git_project_id)
                if self.service.category == 'app_publish':
                    self.update_app_service(self.service)

                TenantServiceInfo.objects.get(service_id=self.service.service_id).delete()
                # env/auth/domain/relationship/envVar delete
                TenantServiceEnv.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceAuth.objects.filter(service_id=self.service.service_id).delete()
                ServiceDomain.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceRelation.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).delete()
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_delete', True)
                result["status"] = "success"
            except Exception, e:
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_delete', False)
        elif action == "protocol":
            par_opt_type = request.POST["opt_type"]
            if par_opt_type == "outer":
                try:
                    protocol = request.POST["protocol"]
                    par_outer_service = request.POST["outer_service"]
                    if par_outer_service == "change":
                        logger.debug("old protocol=" + self.service.protocol + ";new protocol=" + protocol)
                        if protocol == self.service.protocol:
                            result["status"] = "success"
                            return JsonResponse(result)
                    outer_service = False
                    if par_outer_service == "start" or par_outer_service == "change":
                        outer_service = True
                    data = {}
                    data["protocol"] = protocol
                    data["outer_service"] = outer_service
                    data["inner_service"] = self.service.is_service
                    data["inner_service_port"] = self.service.service_port
                    data["service_type"] = par_opt_type
                    regionClient.modifyServiceProtocol(self.service.service_region, self.service.service_id, json.dumps(data))
                    self.service.protocol = protocol
                    self.service.is_web_service = outer_service
                    self.service.save()
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_outer', True)
                    result["status"] = "success"
                except Exception, e:
                    logger.exception(e)
                    result["status"] = "failure"
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_outer', False)
            elif par_opt_type == "inner":
                try:
                    par_inner_service = request.POST["inner_service"]
                    inner_service = False
                    if par_inner_service == "start" or par_inner_service == "change":
                        inner_service = True
                    service_port = self.service.service_port
                    if inner_service:
                        number = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).count()
                        if number < 1:
                            # open inner service add new env variable
                            temp_key = self.service.service_key.upper()
                            if self.service.category == 'application':
                                temp_key = self.service.service_alias.upper()
                            baseService.saveServiceEnvVar(
                                self.tenant.tenant_id, self.service.service_id, u"连接地址", temp_key + "_HOST", "127.0.0.1", False)
                            baseService.saveServiceEnvVar(
                                self.tenant.tenant_id, self.service.service_id, u"端口", temp_key + "_PORT", service_port, False)
                        baseService.create_service_env(
                            self.service.tenant_id, self.service.service_id, self.service.service_region)
                    else:
                        depNumber = TenantServiceRelation.objects.filter(dep_service_id=self.service.service_id).count()
                        if depNumber > 0:
                            result["status"] = "inject_dependency"
                            return JsonResponse(result)

                        # close inner service need to clear env
                        baseService.cancel_service_env(
                            self.service.tenant_id, self.service.service_id, self.service.service_region)

                    data = {}
                    data["protocol"] = self.service.protocol
                    data["outer_service"] = self.service.is_web_service
                    data["inner_service"] = inner_service
                    data["inner_service_port"] = service_port
                    data["service_type"] = par_opt_type
                    regionClient.modifyServiceProtocol(self.service.service_region, self.service.service_id, json.dumps(data))
                    self.service.service_port = service_port
                    self.service.is_service = inner_service
                    self.service.save()
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_inner', True)
                    result["status"] = "success"
                except Exception, e:
                    logger.exception(e)
                    result["status"] = "failure"
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_inner', False)
        elif action == "rollback":
            try:
                event_id = request.POST["event_id"]
                deploy_version = request.POST["deploy_version"]
                if event_id != "":
                    temData = {}
                    temData["service_id"] = self.service.service_id
                    temData["status"] = 2
                    old_status = regionClient.updateTenantServiceStatus(
                        self.service.service_region, self.service.service_id, json.dumps(temData))
                    # calculate resource
                    flag = tenantUsedResource.predict_next_memory(self.tenant, 0)
                    if not flag:
                        if self.tenant.pay_type == "free":
                            result["status"] = "over_memory"
                        else:
                            result["status"] = "over_money"
                        temData["service_id"] = self.service.service_id
                        temData["status"] = old_status
                        regionClient.updateTenantServiceStatus(self.service.service_region, self.service.service_id, json.dumps(temData))
                        return JsonResponse(result, status=200)
                    body = {}
                    body["event_id"] = event_id
                    body["operator"] = str(self.user.nick_name)
                    body["deploy_version"] = deploy_version
                    regionClient.rollback(self.service.service_region, self.service.service_id, json.dumps(body))
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_rollback', True)
                result["status"] = "success"
            except Exception, e:
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_rollback', False)
        return JsonResponse(result)

    def update_app_service(self, tservice):
        try:
            appversion = AppServiceInfo.objects.only('deploy_num').get(service_key=tservice.service_key, app_version=tservice.version)
            appversion.deploy_num -= 1
            appversion.save()
        except AppServiceInfo.DoesNotExist:
            pass


class ServiceUpgrade(AuthedView):

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        self.tenant_region = TenantRegionInfo.objects.get(
            tenant_id=self.service.tenant_id, region_name=self.service.service_region)
        if self.tenant_region.service_status == 2 and self.tenant.pay_type == "payed":
            result["status"] = "owed"
            return JsonResponse(result, status=200)
        oldVerion = self.service.deploy_version
        if oldVerion is not None and oldVerion != "":
            if not baseService.is_user_click(self.service.service_region, self.service.service_id):
                result["status"] = "often"
                return JsonResponse(result, status=200)

        action = request.POST["action"]
        if action == "vertical":
            try:
                container_memory = request.POST["memory"]
                container_cpu = request.POST["cpu"]
                old_container_cpu = self.service.min_cpu
                old_container_memory = self.service.min_memory
                old_deploy_version = self.service.deploy_version
                upgrade_container_memory = int(container_memory)
                left = upgrade_container_memory % 128
                if upgrade_container_memory > 0 and upgrade_container_memory <= 65536 and left == 0:
                    upgrade_container_cpu = upgrade_container_memory / 128 * 20
                    # temp record service status
                    temData = {}
                    temData["service_id"] = self.service.service_id
                    temData["status"] = 2
                    old_status = regionClient.updateTenantServiceStatus(
                        self.service.service_region, self.service.service_id, json.dumps(temData))
                    # calculate resource
                    diff_memory = upgrade_container_memory - int(old_container_memory)
                    flag = tenantUsedResource.predict_next_memory(self.tenant, diff_memory)
                    if not flag:
                        if self.tenant.pay_type == "free":
                            result["status"] = "over_memory"
                        else:
                            result["status"] = "over_money"
                        temData["service_id"] = self.service.service_id
                        temData["status"] = old_status
                        regionClient.updateTenantServiceStatus(self.service.service_region,
                                                               self.service.service_id, json.dumps(temData))
                        return JsonResponse(result, status=200)

                    deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                    self.service.min_cpu = upgrade_container_cpu
                    self.service.min_memory = upgrade_container_memory
                    self.service.deploy_version = deploy_version
                    self.service.save()

                    body = {}
                    body["container_memory"] = upgrade_container_memory
                    body["deploy_version"] = deploy_version
                    body["container_cpu"] = upgrade_container_cpu
                    body["operator"] = str(self.user.nick_name)
                    regionClient.verticalUpgrade(self.service.service_region, self.service.service_id, json.dumps(body))
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_vertical', True)
                result["status"] = "success"
            except Exception, e:
                self.service.min_cpu = old_container_cpu
                self.service.min_memory = old_container_memory
                self.service.deploy_version = old_deploy_version
                self.service.save()
                logger.exception(e)
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_vertical', False)
                result["status"] = "failure"
        elif action == "horizontal":
            node_num = request.POST["node_num"]
            old_min_node = self.service.min_node
            old_deploy_version = self.service.deploy_version
            try:
                new_node_num = int(node_num)
                if new_node_num >= 0 and new_node_num != old_min_node:
                    # temp record service status
                    temData = {}
                    temData["service_id"] = self.service.service_id
                    temData["status"] = 2
                    old_status = regionClient.updateTenantServiceStatus(
                        self.service.service_region, self.service.service_id, json.dumps(temData))
                    # calculate resource
                    diff_memory = (new_node_num - old_min_node) * self.service.min_memory
                    flag = tenantUsedResource.predict_next_memory(self.tenant, diff_memory)
                    if not flag:
                        if self.tenant.pay_type == "free":
                            result["status"] = "over_memory"
                        else:
                            result["status"] = "over_money"
                        temData["service_id"] = self.service.service_id
                        temData["status"] = old_status
                        regionClient.updateTenantServiceStatus(self.service.service_region,
                                                               self.service.service_id, json.dumps(temData))
                        return JsonResponse(result, status=200)

                    deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

                    isResetStatus = False
                    try:
                        body = {}
                        body["node_num"] = node_num
                        body["deploy_version"] = deploy_version
                        body["operator"] = str(self.user.nick_name)
                        regionClient.horizontalUpgrade(self.service.service_region, self.service.service_id, json.dumps(body))
                    except Exception, e:
                        logger.exception(e)
                        isResetStatus = True

                    if not isResetStatus:
                        self.service.min_node = node_num
                        self.service.deploy_version = deploy_version
                        self.service.save()

                    if isResetStatus or new_node_num < old_min_node:
                        temData["service_id"] = self.service.service_id
                        temData["status"] = old_status
                        regionClient.updateTenantServiceStatus(self.service.service_region,
                                                               self.service.service_id, json.dumps(temData))
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_horizontal', True)
                result["status"] = "success"
            except Exception, e:
                self.service.min_node = old_min_node
                self.service.deploy_version = old_deploy_version
                self.service.save()
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_horizontal', False)
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
            tenantS = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_alias=dep_service_alias)
            if action == "add":
                baseService.create_service_dependency(tenant_id, service_id, tenantS.service_id, self.service.service_region)
            elif action == "cancel":
                baseService.cancel_service_dependency(tenant_id, service_id, tenantS.service_id, self.service.service_region)
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)


class AllServiceInfo(AuthedView):

    def init_request(self, *args, **kwargs):
        self.cookie_region = self.request.COOKIES.get('region')
        self.tenant_region = TenantRegionInfo.objects.get(tenant_id=self.tenant.tenant_id, region_name=self.cookie_region)

    @method_perf_time
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        result = {}
        service_ids = []
        try:
            service_list = TenantServiceInfo.objects.filter(
                tenant_id=self.tenant.tenant_id, service_region=self.cookie_region).values('ID', 'service_id', 'deploy_version')
            if self.has_perm('tenant.list_all_services'):
                for s in service_list:
                    if s['deploy_version'] is None or s['deploy_version'] == "":
                        child1 = {}
                        child1["status"] = "undeploy"
                        result[s['service_id']] = child1
                    else:
                        service_ids.append(s['service_id'])
            else:
                service_pk_list = PermRelService.objects.filter(user_id=self.user.pk).values_list('service_id', flat=True)
                for s in service_list:
                    if s['ID'] in service_pk_list:
                        if s['deploy_version'] is None or s['deploy_version'] == "":
                            child1 = {}
                            child1["status"] = "undeploy"
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
                    id_string = ','.join(service_ids)
                    bodys = regionClient.check_status(self.cookie_region, json.dumps({"service_ids": id_string}))
                    logger.debug(bodys)
                    for key, value in bodys.items():
                        child = {}
                        child["status"] = value
                        result[key] = child
        except Exception:
            tempIds = ','.join(service_ids)
            logger.debug(self.tenant.region + "-" + tempIds + " check_service_status is error")
            for sid in service_ids:
                child = {}
                child["status"] = "failure"
                result[sid] = child
        return JsonResponse(result)


class AllTenantsUsedResource(AuthedView):

    def init_request(self, *args, **kwargs):
        self.cookie_region = self.request.COOKIES.get('region')
        self.tenant_region = TenantRegionInfo.objects.get(tenant_id=self.tenant.tenant_id, region_name=self.cookie_region)

    @method_perf_time
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            service_ids = []
            serviceIds = ""
            service_list = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id, service_region=self.cookie_region).values(
                'ID', 'service_id', 'min_node', 'min_memory')
            if self.has_perm('tenant.list_all_services'):
                for s in service_list:
                    service_ids.append(s['service_id'])
                    if len(serviceIds) > 0:
                        serviceIds = serviceIds + ","
                    serviceIds = serviceIds + "'" + s["service_id"] + "'"
                    result[s['service_id'] + "_running_memory"] = s["min_node"] * s["min_memory"]
            else:
                service_pk_list = PermRelService.objects.filter(user_id=self.user.pk).values_list('service_id', flat=True)
                for s in service_list:
                    if s['ID'] in service_pk_list:
                        service_ids.append(s['service_id'])
                        if len(serviceIds) > 0:
                            serviceIds = serviceIds + ","
                        serviceIds = serviceIds + "'" + s["service_id"] + "'"
                        result[s['service_id'] + "_running_memory"] = s["min_node"] * s["min_memory"]
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
            self.tenant_region = TenantRegionInfo.objects.get(
                tenant_id=self.service.tenant_id, region_name=self.service.service_region)
            if self.tenant_region.service_status == 2 and self.tenant.pay_type == "payed":
                result["totalMemory"] = 0
                result["status"] = "Owed"
            else:
                if self.service.deploy_version is None or self.service.deploy_version == "":
                    result["totalMemory"] = 0
                    result["status"] = "Undeployed"
                else:
                    body = regionClient.check_service_status(self.service.service_region, self.service.service_id)
                    status = body[self.service.service_id]
                    if status == "running":
                        result["totalMemory"] = self.service.min_node * self.service.min_memory
                    else:
                        result["totalMemory"] = 0
                    result["status"] = status
        except Exception, e:
            logger.debug(self.service.service_region + "-" + self.service.service_id + " check_service_status is error")
            result["totalMemory"] = 0
            result['status'] = "failure"
        return JsonResponse(result)


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
                    body = regionClient.get_userlog(self.service.service_region, service_id)
                    eventDataList = body.get("event_data")
                    result = {}
                    result["log"] = eventDataList
                    result["num"] = len(eventDataList)
                    return JsonResponse(result)
                elif action == "service":
                    body = {}
                    body["tenant_id"] = tenant_id
                    body = regionClient.get_log(self.service.service_region, service_id, json.dumps(body))
                    return JsonResponse(body)
                elif action == "compile":
                    event_id = request.GET.get("event_id", "")
                    body = {}
                    if event_id != "":
                        body["tenant_id"] = tenant_id
                        body["event_id"] = event_id
                        body = regionClient.get_compile_log(self.service.service_region, service_id, json.dumps(body))
                    return JsonResponse(body)
        except Exception as e:
            logger.info("%s" % e)
        return JsonResponse({})


class ServiceCheck(AuthedView):

    def sendCodeCheckMsg(self):
        data = {}
        data["tenant_id"] = self.service.tenant_id
        data["service_id"] = self.service.service_id
        clone_url = self.service.git_url
        parsed_git_url = git_url_parse(clone_url)
        if parsed_git_url.host == "code.goodrain.com":
            gitUrl = "--branch " + self.service.code_version + " --depth 1 " + parsed_git_url.url2ssh
        elif parsed_git_url.host == 'github.com':
            createUser = Users.objects.get(user_id=self.service.creater)
            gitUrl = "--branch " + self.service.code_version + " --depth 1 " + parsed_git_url.url2https_token(createUser.token)
        else:
            gitUrl = "--branch " + self.service.code_version + " --depth 1 " + parsed_git_url.url2https

        data["git_url"] = gitUrl
        task = {}
        task["tube"] = "code_check"
        task["data"] = data
        task["service_id"] = self.service.service_id
        regionClient.writeToRegionBeanstalk(self.service.service_region, self.service.service_id, json.dumps(task))

    @method_perf_time
    @perm_required('manage_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            requestNumber = request.GET.get("requestNumber", "0")
            reqNum = int(requestNumber)
            if reqNum > 0 and reqNum % 20 == 0:
                self.sendCodeCheckMsg()
            if self.service.language is None or self.service.language == "":
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
            result["status"] = "checking"
            logger.debug(self.service.service_id + " not upload code")
        return JsonResponse(result)


class ServiceMappingPort(AuthedView):

    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            body = regionClient.findMappingPort(self.service.service_region, self.service.service_id)
            port = body["port"]
            ip = body["ip"]
            result["port"] = port
            result["ip"] = ip
        except Exception as e:
            logger.exception(e)
            result["port"] = 0
        return JsonResponse(result)


class ServiceDomainManager(AuthedView):

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            tenantService = self.service
            domain_name = request.POST["domain_name"]
            action = request.POST["action"]
            if action == "start":
                domainNum = ServiceDomain.objects.filter(domain_name=domain_name).count()
                if domainNum > 0:
                    result["status"] = "exist"
                    return JsonResponse(result)

                num = ServiceDomain.objects.filter(service_id=self.service.service_id).count()
                old_domain_name = "goodrain"
                if num == 0:
                    domain = {}
                    domain["service_id"] = self.service.service_id
                    domain["service_name"] = tenantService.service_alias
                    domain["domain_name"] = domain_name
                    domain["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    domaininfo = ServiceDomain(**domain)
                    domaininfo.save()
                else:
                    domain = ServiceDomain.objects.get(service_id=self.service.service_id)
                    old_domain_name = domain.domain_name
                    domain.domain_name = domain_name
                    domain.save()
                data = {}
                data["service_id"] = self.service.service_id
                data["new_domain"] = domain_name
                data["old_domain"] = old_domain_name
                data["pool_name"] = self.tenantName + "@" + self.serviceAlias + ".Pool"
                regionClient.addUserDomain(self.service.service_region, json.dumps(data))
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'domain_add', True)
            elif action == "close":
                servicerDomain = ServiceDomain.objects.get(service_id=self.service.service_id)
                data = {}
                data["service_id"] = servicerDomain.service_id
                data["domain"] = servicerDomain.domain_name
                data["pool_name"] = self.tenantName + "@" + self.serviceAlias + ".Pool"
                regionClient.deleteUserDomain(self.service.service_region, json.dumps(data))
                ServiceDomain.objects.filter(service_id=self.service.service_id).delete()
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'domain_delete', True)
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'domain_manage', False)
        return JsonResponse(result)


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
                        TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).exclude(ID__in=total_ids).delete()

                    # update and save env
                    for index, cname in enumerate(name_arr):
                        tmpId = attr_id_arr[index]
                        if int(tmpId) > 0:
                            tsev = TenantServiceEnvVar.objects.get(ID=int(tmpId))
                            tsev.attr_name = attr_name_arr[index]
                            tsev.attr_value = attr_value_arr[index]
                            tsev.save()
                        else:
                            tenantServiceEnvVar = {}
                            tenantServiceEnvVar["tenant_id"] = self.service.tenant_id
                            tenantServiceEnvVar["service_id"] = self.service.service_id
                            tenantServiceEnvVar["name"] = cname
                            tenantServiceEnvVar["attr_name"] = attr_name_arr[index]
                            tenantServiceEnvVar["attr_value"] = attr_value_arr[index]
                            tenantServiceEnvVar["is_change"] = True
                            TenantServiceEnvVar(**tenantServiceEnvVar).save()
            else:
                if len(total_ids) > 0:
                    TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).exclude(ID__in=total_ids).delete()

            # sync data to region
            if isNeedToRsync:
                baseService.create_service_env(self.service.tenant_id, self.service.service_id, self.service.service_region)
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)


class ServiceBranch(AuthedView):

    def get_gitlab_branchs(self, parsed_git_url):
        project_id = self.service.git_project_id
        if project_id > 0:
            branchlist = gitClient.getProjectBranches(project_id)
            branchs = [e['name'] for e in branchlist]
            return branchs
        else:
            return [self.service.code_version]

    def get_github_branchs(self, parsed_git_url):
        user = Users.objects.only('github_token').get(pk=self.service.creater)
        token = user.github_token
        owner = parsed_git_url.owner
        repo = parsed_git_url.repo
        try:
            branch_list = githubClient.get_branchs(owner, repo, token)
            branchs = [e['name'] for e in branch_list]
            return branchs
        except githubClient.CallApiError, e:
            logger.error('client_error', e)
            return []

    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        parsed_git_url = git_url_parse(self.service.git_url)
        if parsed_git_url.host == 'code.goodrain.com':
            branchs = self.get_gitlab_branchs(parsed_git_url)
        elif parsed_git_url.host.endswith('github.com'):
            branchs = self.get_github_branchs(parsed_git_url)
        else:
            branchs = [self.service.code_version]

        result = {"current": self.service.code_version, "branchs": branchs}
        return JsonResponse(result, status=200)

    @perm_required('deploy_service')
    def post(self, request, *args, **kwargs):
        branch = request.POST.get('branch')
        self.service.code_version = branch
        self.service.save(update_fields=['code_version'])
        return JsonResponse({"ok": True}, status=200)
