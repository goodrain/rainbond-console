# -*- coding: utf8 -*-
import datetime
import json
import re

from django.db.models import Sum
from django.db.models import Max
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required

from www.models import (ServiceInfo, AppServiceInfo, TenantServiceInfo, TenantRegionInfo, TenantServiceLog, PermRelService, TenantServiceRelation,
                        TenantServiceStatics, TenantServiceInfoDelete, Users, TenantServiceEnv, TenantServiceAuth, ServiceDomain,
                        TenantServiceEnvVar, TenantServicesPort, TenantServiceMountRelation)
from www.service_http import RegionServiceApi
from django.conf import settings
from www.db import BaseConnection
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, CodeRepositoriesService
from goodrain_web.decorator import method_perf_time
from www.monitorservice.monitorhook import MonitorHook
from www.utils.giturlparse import parse as git_url_parse
from www.forms.services import EnvCheckForm

import logging
from django.template.defaultfilters import length
logger = logging.getLogger('default')

regionClient = RegionServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
codeRepositoriesService = CodeRepositoriesService()


class AppDeploy(AuthedView):

    @method_perf_time
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        data = {}

        if tenantAccountService.isOwnedMoney(self.tenant, self.service.service_region):
            data["status"] = "owed"
            return JsonResponse(data, status=200)

        if self.service.language is None or self.service.language == "":
            data["status"] = "language"
            return JsonResponse(data, status=200)

        tenant_id = self.tenant.tenant_id
        service_id = self.service.service_id
        oldVerion = self.service.deploy_version
        if oldVerion is not None and oldVerion != "":
            if not baseService.is_user_click(self.service.service_region, service_id):
                data["status"] = "often"
                return JsonResponse(data, status=200)

        # calculate resource
        rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, 0, True)
        if not flag:
            if rt_type == "memory":
                data["status"] = "over_memory"
            else:
                data["status"] = "over_money"
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
        
        if tenantAccountService.isOwnedMoney(self.tenant, self.service.service_region):
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
                # calculate resource
                diff_memory = self.service.min_node * self.service.min_memory
                rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, diff_memory, False)
                if not flag:
                    if rt_type == "memory":
                        result["status"] = "over_memory"
                    else:
                        result["status"] = "over_money"
                    return JsonResponse(result, status=200)
                
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
                published = AppServiceInfo.objects.filter(service_id=self.service.service_id).count()
                if published:
                    result["status"] = "failure"
                    result["info"] = u"关联了已发布服务, 不可删除"
                    return JsonResponse(result)
                
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
                        result["status"] = "evn_dependency"
                        return JsonResponse(result)
                    
                dependSids = TenantServiceMountRelation.objects.filter(dep_service_id=self.service.service_id).values("service_id")
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
                        return JsonResponse(result)
                
                data = self.service.toJSON()
                newTenantServiceDelete = TenantServiceInfoDelete(**data)
                newTenantServiceDelete.save()
                try:
                    regionClient.delete(self.service.service_region, self.service.service_id)
                except Exception as e:
                    logger.exception(e)
                if self.service.code_from == 'gitlab_new' and self.service.git_project_id > 0:
                    codeRepositoriesService.deleteProject(self.service)
                if self.service.category == 'app_publish':
                    self.update_app_service(self.service)

                TenantServiceInfo.objects.get(service_id=self.service.service_id).delete()
                # env/auth/domain/relationship/envVar delete
                TenantServiceEnv.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceAuth.objects.filter(service_id=self.service.service_id).delete()
                ServiceDomain.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceRelation.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceMountRelation.objects.filter(service_id=self.service.service_id).delete()
                TenantServicesPort.objects.filter(service_id=self.service.service_id).delete()
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_delete', True)
                result["status"] = "success"
            except Exception, e:
                logger.exception(e)
                result["status"] = "failure"
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_delete', False)
        elif action == "rollback":
            try:
                event_id = request.POST["event_id"]
                deploy_version = request.POST["deploy_version"]
                if event_id != "":
                    # calculate resource
                    rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, 0, True)
                    if not flag:
                        if rt_type == "memory":
                            result["status"] = "over_memory"
                        else:
                            result["status"] = "over_money"
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
            appversion = AppServiceInfo.objects.only('deploy_num').get(service_key=tservice.service_key, app_version=tservice.version, update_version=tservice.update_version)
            appversion.deploy_num -= 1
            appversion.save()
        except AppServiceInfo.DoesNotExist:
            pass


class ServiceUpgrade(AuthedView):

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        
        if tenantAccountService.isOwnedMoney(self.tenant, self.service.service_region):
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
                if int(container_memory) != old_container_memory or int(container_cpu) != old_container_cpu:
                    upgrade_container_memory = int(container_memory)
                    left = upgrade_container_memory % 128
                    if upgrade_container_memory > 0 and upgrade_container_memory <= 65536 and left == 0:
                        # calculate resource
                        diff_memory = upgrade_container_memory - int(old_container_memory)
                        rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, diff_memory, True)
                        if not flag:
                            if rt_type == "memory":
                                result["status"] = "over_memory"
                            else:
                                result["status"] = "over_money"
                            return JsonResponse(result, status=200)
    
                        upgrade_container_cpu = upgrade_container_memory / 128 * 20
                        
                        body = {}
                        body["container_memory"] = upgrade_container_memory
                        body["deploy_version"] = self.service.deploy_version
                        body["container_cpu"] = upgrade_container_cpu
                        body["operator"] = str(self.user.nick_name)
                        regionClient.verticalUpgrade(self.service.service_region, self.service.service_id, json.dumps(body))
                        
                        self.service.min_cpu = upgrade_container_cpu
                        self.service.min_memory = upgrade_container_memory
                        self.service.save()
                        
                        monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_vertical', True)
                result["status"] = "success"
            except Exception, e:
                logger.exception(e)
                monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_vertical', False)
                result["status"] = "failure"
        elif action == "horizontal":
            node_num = request.POST["node_num"]
            try:
                new_node_num = int(node_num)
                old_min_node = self.service.min_node
                if new_node_num >= 0 and new_node_num != old_min_node:
                    # calculate resource
                    diff_memory = (new_node_num - old_min_node) * self.service.min_memory
                    rt_type, flag = tenantUsedResource.predict_next_memory(self.tenant, self.service, diff_memory, True)
                    if not flag:
                        if rt_type == "memory":
                            result["status"] = "over_memory"
                        else:
                            result["status"] = "over_money"
                        return JsonResponse(result, status=200)

                    body = {}
                    body["node_num"] = new_node_num
                    body["deploy_version"] = self.service.deploy_version
                    body["operator"] = str(self.user.nick_name)
                    regionClient.horizontalUpgrade(self.service.service_region, self.service.service_id, json.dumps(body))
                    
                    self.service.min_node = new_node_num
                    self.service.save()
                    monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_horizontal', True)
                result["status"] = "success"
            except Exception, e:
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
                    # logger.debug(bodys)
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
            if tenantAccountService.isOwnedMoney(self.tenant, self.service.service_region):
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

    @method_perf_time
    @perm_required('manage_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            requestNumber = request.GET.get("requestNumber", "0")
            reqNum = int(requestNumber)
            if reqNum > 0 and reqNum % 30 == 0:
                codeRepositoriesService.codeCheck(self.service)
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
        if parsed_git_url.host == 'code.goodrain.com':
            branchs = self.get_gitlab_branchs(parsed_git_url)
        elif parsed_git_url.host.endswith('github.com'):
            branchs = self.get_github_branchs(parsed_git_url)
        else:
            branchs = [self.service.code_version]
        # if len(branchs) > 0:
        #    branchs.sort(reverse=True)
        result = {"current": self.service.code_version, "branchs": branchs}
        return JsonResponse(result, status=200)

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
        if not re.match(r'^\d{2,5}$', str(port)):
            return False, u"格式不符合要求^\d{2,5}"

        if TenantServicesPort.objects.filter(service_id=self.service.service_id, container_port=port).exists():
            return False, u"端口冲突"

        return True, port

    @perm_required("manage_service")
    def post(self, request, port, *args, **kwargs):
        action = request.POST.get("action")
        deal_port = TenantServicesPort.objects.get(service_id=self.service.service_id, container_port=int(port))

        data = {"port": int(port)}
        if action == 'change_protocol':
            protocol = request.POST.get("value")
            deal_port.protocol = protocol
            data.update({"modified_field": "protocol", "current_value": protocol})
        elif action == 'open_outer':
            deal_port.is_outer_service = True
            data.update({"modified_field": "is_outer_service", "current_value": True})
            if deal_port.mapping_port == 0:
                deal_port.mapping_port = 1
                data.update({"mapping_port": 1})
        elif action == 'close_outer':
            deal_port.is_outer_service = False
            data.update({"modified_field": "is_outer_service", "current_value": False})
        elif action == 'close_inner':
            deal_port.is_inner_service = False
            data.update({"modified_field": "is_inner_service", "current_value": False})
        elif action == 'open_inner':
            if bool(deal_port.port_alias) is False:
                return JsonResponse({"success": False, "info": u"请先为端口设置别名", "code": 409})
            deal_port.is_inner_service = True
            data.update({"modified_field": "is_inner_service", "current_value": True})

            baseService = BaseTenantService()
            if deal_port.mapping_port <= 1:
                mapping_port = baseService.prepare_mapping_port(self.service, deal_port.container_port)
                deal_port.mapping_port = mapping_port
                deal_port.save(update_fields=['mapping_port'])
                TenantServiceEnvVar.objects.filter(service_id=deal_port.service_id, container_port=deal_port.container_port).delete()
                baseService.saveServiceEnvVar(self.service.tenant_id, self.service.service_id, deal_port.container_port, u"连接地址",
                                              deal_port.port_alias + "_HOST", "127.0.0.1", False, scope="outer")
                baseService.saveServiceEnvVar(self.service.tenant_id, self.service.service_id, deal_port.container_port, u"端口",
                                              deal_port.port_alias + "_PORT", mapping_port, False, scope="outer")
                data.update({"mapping_port": mapping_port})
            else:
                # 兼容旧的非对内服务, mapping_port有正常值
                unique = TenantServicesPort.objects.filter(tenant_id=deal_port.tenant_id, mapping_port=deal_port.mapping_port).count()
                logger.debug("debug", "unique count is {}".format(unique))
                if unique > 1:
                    new_mapping_port = baseService.prepare_mapping_port(self.service, deal_port.container_port)
                    logger.debug("debug", "new_mapping_port is {}".format(new_mapping_port))
                    deal_port.mapping_port = new_mapping_port
                    deal_port.save(update_fields=['mapping_port'])
                    data.update({"mapping_port": new_mapping_port})

            port_envs = TenantServiceEnvVar.objects.filter(service_id=deal_port.service_id, container_port=deal_port.container_port).values(
                'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
            data.update({"port_envs": list(port_envs)})
        elif action == 'change_port_alias':
            new_port_alias = request.POST.get("value")
            success, reason = self.check_port_alias(new_port_alias)
            if not success:
                return JsonResponse({"success": False, "info": reason, "code": 400}, status=400)
            else:
                old_port_alias = deal_port.port_alias
                deal_port.port_alias = new_port_alias
                envs = TenantServiceEnvVar.objects.only('attr_name').filter(service_id=deal_port.service_id, container_port=deal_port.container_port)
                for env in envs:
                    new_attr_name = new_port_alias + env.attr_name.lstrip(old_port_alias)
                    env.attr_name = new_attr_name
                    env.save()
                port_envs = TenantServiceEnvVar.objects.filter(service_id=deal_port.service_id, container_port=deal_port.container_port).values(
                    'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
                data.update({"modified_field": "port_alias", "current_value": new_port_alias, "port_envs": list(port_envs)})
        elif action == 'change_port':
            new_port = int(request.POST.get("value"))
            success, reason = self.check_port(new_port)
            if not success:
                return JsonResponse({"success": False, "info": reason, "code": 400}, status=400)
            else:
                old_port = deal_port.container_port
                deal_port.container_port = new_port
                TenantServiceEnvVar.objects.filter(service_id=deal_port.service_id, container_port=old_port).update(container_port=new_port)
                data.update({"modified_field": "port", "current_value": new_port})
        try:
            regionClient.manageServicePort(self.service.service_region, self.service.service_id, json.dumps(data))
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_outer', True)
            deal_port.save()
            return JsonResponse({"success": True, "info": u"更改成功"}, status=200)
        except Exception, e:
            logger.exception(e)
            monitorhook.serviceMonitor(self.user.nick_name, self.service, 'app_outer', False)
            return JsonResponse({"success": False, "info": u"更改失败", "code": 500}, status=200)

    def get(self, request, port, *args, **kwargs):
        deal_port = TenantServicesPort.objects.get(service_id=self.service.service_id, container_port=int(port))
        data = {"environment": []}

        if deal_port.is_inner_service:
            for port_env in TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, container_port=deal_port.container_port):
                data["environment"].append({
                    "desc": port_env.name, "name": port_env.attr_name, "value": port_env.attr_value
                })
        if deal_port.is_outer_service:
            service_region = self.service.service_region
            if deal_port.protocol == 'stream':
                body = regionClient.findMappingPort(self.service.service_region, self.service.service_id)
                cur_region = service_region.replace("-1", "")
                domain = "{0}.{1}.{2}-s1.goodrain.net".format(self.service.service_alias, self.tenant.tenant_name, cur_region)
                if settings.STREAM_DOMAIN:
                    domain = settings.STREAM_DOMAIN_URL
                    
                data["outer_service"] = {
                    "domain": domain,
                    "port": body["port"],
                }
            elif deal_port.protocol == 'http':
                data["outer_service"] = {
                    "domain": "{0}.{1}{2}".format(self.service.service_alias, self.tenant.tenant_name, settings.WILD_DOMAINS[service_region]),
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
                TenantServiceEnvVar.objects.create(**attr)
                data = {"action": "add", "attrs": attr}
                regionClient.createServiceEnv(self.service.service_region, self.service.service_id, json.dumps(data))
                return JsonResponse({"success": True, "info": u"创建成功"})
        elif action == 'del_attr':
            attr_name = request.POST.get("attr_name")
            TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, attr_name=attr_name).delete()

            data = {"action": "delete", "attr_names": [attr_name]}
            regionClient.createServiceEnv(self.service.service_region, self.service.service_id, json.dumps(data))
            return JsonResponse({"success": True, "info": u"删除成功"})


class ServiceMnt(AuthedView):

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        action = request.POST["action"]
        dep_service_alias = request.POST["dep_service_alias"]
        try:
            tenant_id = self.tenant.tenant_id
            service_id = self.service.service_id
            if action == "add":
                baseService.create_service_mnt(tenant_id, service_id, dep_service_alias, self.service.service_region)
            elif action == "cancel":
                baseService.cancel_service_mnt(tenant_id, service_id, dep_service_alias, self.service.service_region)
            result["status"] = "success"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)
    
    
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
            
            if not re.match(r'^[0-9_]*$', port_port):
                return JsonResponse({"success": False, "code": 400, "info": u"端口不合法"})
            
            port_port = int(port_port)
            port_inner = int(port_inner)
            port_outter = int(port_outter)
            
            if not re.match(r'^[A-Z][A-Z0-9_]*$', port_alias):
                return JsonResponse({"success": False, "code": 400, "info": u"别名不合法"})
            
            if port_outter == 1:
                 if TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=1).count() > 0:
                     return JsonResponse({"success": False, "code": 409, "info": u"只能开启一个对外端口"})
            
            if TenantServicesPort.objects.filter(service_id=self.service.service_id, container_port=port_port).exists():
                return JsonResponse({"success": False, "code": 409, "info": u"容器端口冲突"})
            
            mapping_port = 0
            if port_inner == 1 and port_protocol=="stream":
                 mapping_port = baseService.prepare_mapping_port(self.service, port_port)
            port = {
                "tenant_id": self.service.tenant_id, "service_id": self.service.service_id,
                "container_port": port_port, "mapping_port": mapping_port, "protocol": port_protocol, "port_alias": port_alias,
                "is_inner_service": port_inner, "is_outer_service": port_outter
            }
            TenantServicesPort.objects.create(**port)
            data = {"action": "add", "ports": port}
            regionClient.createServicePort(self.service.service_region, self.service.service_id, json.dumps(data))
            return JsonResponse({"success": True, "info": u"创建成功"})
        elif action == 'del_port':
            if TenantServicesPort.objects.filter(service_id=self.service.service_id).count()==1:
                return JsonResponse({"success": False, "code": 409, "info": u"服务至少保留一个端口"})
            
            port_port = request.POST.get("port_port")
            TenantServicesPort.objects.filter(service_id=self.service.service_id, container_port=port_port).delete()
            TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, container_port=port_port).delete()
            data = {"action": "delete", "port_ports": [port_port]}
            regionClient.createServicePort(self.service.service_region, self.service.service_id, json.dumps(data))
            return JsonResponse({"success": True, "info": u"删除成功"})
