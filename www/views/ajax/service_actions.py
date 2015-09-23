# -*- coding: utf8 -*-
import datetime
import json

from django.db.models import Sum
from django.db.models import Max
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required

from www.models import TenantServiceInfo, TenantServiceLog, PermRelService, TenantServiceRelation, TenantServiceStatics, TenantServiceInfoDelete, Users, TenantServiceEnv, TenantServiceAuth, ServiceDomain 
from www.service_http import RegionServiceApi
from www.gitlab_http import GitlabApi
from django.conf import settings
from www.db import BaseConnection
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource

import logging
from django.template.defaultfilters import length
logger = logging.getLogger('default')

gitClient = GitlabApi()

regionClient = RegionServiceApi()

class AppDeploy(AuthedView):
    @perm_required('code_deploy')
    def post(self, request, *args, **kwargs):
        data = {}
        if self.tenant.service_status == 2 and self.tenant.pay_type == "payed":
            data["status"] = "owed"
            return JsonResponse(data, status=200)
        
        if self.service.ID > 598 and (self.service.language is None or self.service.language == ""):
            data["status"] = "language"
            return JsonResponse(data, status=200)
        
        tenant_id = self.tenant.tenant_id
        service_id = self.service.service_id
        oldVerion = self.service.deploy_version
        if oldVerion is not None and oldVerion != "":      
            curVersion = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            diffsec = int(curVersion) - int(oldVerion)
            if diffsec <= 90:
                data["status"] = "often"
                return JsonResponse(data, status=200)
        
        # temp record service status
        temData = {}
        temData["service_id"] = service_id
        temData["status"] = 2
        old_status = regionClient.updateTenantServiceStatus(self.tenant.region, service_id, json.dumps(temData))
        # calculate resource 
        tenantUsedResource = TenantUsedResource()
        flag = tenantUsedResource.predict_next_memory(self.tenant, 0) 
        if not flag:
            if self.tenant.pay_type == "free":
                data["status"] = "over_memory"
            else:
                data["status"] = "over_money"
            temData["service_id"] = service_id
            temData["status"] = old_status
            regionClient.updateTenantServiceStatus(self.tenant.region, service_id, json.dumps(temData))
            return JsonResponse(data, status=200)
        
        try:
            data = {}
            data["log_msg"] = "开始部署......"
            data["service_id"] = service_id
            data["tenant_id"] = tenant_id
            task = {}
            task["service_id"] = service_id
            task["data"] = data
            task["tube"] = "app_log"
            regionClient.writeToRegionBeanstalk(self.tenant.region, service_id, json.dumps(task))
        except Exception as e:
            logger.exception(e)
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
            para = json.dumps(body)
            
            regionClient.build_service(self.tenant.region, service_id, para)

            log = {
                "user_id": self.user.pk, "user_name": self.user.nick_name,
                "service_id": service_id, "tenant_id": tenant_id,
                "action": "deploy",
            }
            TenantServiceLog.objects.create(**log)
            data["status"] = "success"
            return JsonResponse(data, status=200)
        except Exception as e:
            logger.debug(e)
            data["status"] = "failure"
        return JsonResponse(data, status=500)

class ServiceManage(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        if self.tenant.service_status == 2 and self.tenant.pay_type == "payed":
            result["status"] = "owed"
            return JsonResponse(result, status=200)
        
        oldVerion = self.service.deploy_version
        if oldVerion is not None and oldVerion != "":      
            curVersion = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            diffsec = int(curVersion) - int(oldVerion)
            if diffsec <= 60:
                result["status"] = "often"
                return JsonResponse(result, status=200)

        try:
            action = request.POST["action"]
            if action == "stop":
                regionClient.stop(self.tenant.region, self.service.service_id)
            elif action == "restart":
                # temp record service status
                temData = {}
                temData["service_id"] = self.service.service_id
                temData["status"] = 2
                old_status = regionClient.updateTenantServiceStatus(self.tenant.region, self.service.service_id, json.dumps(temData))
                # calculate resource 
                tenantUsedResource = TenantUsedResource()
                flag = tenantUsedResource.predict_next_memory(self.tenant, 0) 
                if not flag:
                    if self.tenant.pay_type == "free":
                        result["status"] = "over_memory"
                    else:
                        result["status"] = "over_money"
                    temData["service_id"] = self.service.service_id
                    temData["status"] = old_status
                    regionClient.updateTenantServiceStatus(self.tenant.region, self.service.service_id, json.dumps(temData))
                    return JsonResponse(result, status=200)
                
                self.service.deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                self.service.save()
                body = {}
                body["deploy_version"] = self.service.deploy_version                    
                regionClient.restart(self.tenant.region, self.service.service_id, json.dumps(body))                
            elif action == "delete":
                depNumber = TenantServiceRelation.objects.filter(dep_service_id=self.service.service_id).count()
                if depNumber > 0:
                    result["status"] = "dependency"
                    return JsonResponse(result)
                data = self.service.toJSON()
                newTenantServiceDelete = TenantServiceInfoDelete(**data)
                newTenantServiceDelete.save()
                try:
                   regionClient.delete(self.tenant.region, self.service.service_id)
                except Exception as e:
                   logger.exception(e)
                if self.service.code_from == 'gitlab_new' and self.service.git_project_id > 0:
                    gitClient.deleteProject(self.service.git_project_id)
                TenantServiceInfo.objects.get(service_id=self.service.service_id).delete()
                # env/auth/relationship delete                
                TenantServiceEnv.objects.filter(service_id=self.service.service_id).delete()
                TenantServiceAuth.objects.filter(service_id=self.service.service_id).delete()
                ServiceDomain.objects.filter(service_id=self.service.service_id).delete()
                               
                tdrNumber = TenantServiceRelation.objects.filter(service_id=self.service.service_id).count()
                if tdrNumber > 0:
                    TenantServiceRelation.objects.filter(service_id=self.service.service_id).delete()
                    try:
                        data = {}
                        data["tenant_id"] = self.service.tenant_id
                        data["service_id"] = self.service.service_id
                        regionClient.deleteEtcdService(self.tenant.region, self.service.service_id, json.dumps(data))
                    except Exception as e:
                        logger.exception(e)
            elif action == "protocol":
                par_opt_type = request.POST["opt_type"]
                if par_opt_type == "outer":
                    protocol = request.POST["protocol"]
                    par_outer_service = request.POST["outer_service"]
                    par_outer_ip = request.POST["outer_ip"]
                    if protocol != "":
                        outer_service = False
                        if par_outer_service == "start" or par_outer_service == "change":
                            outer_service = True                                
                        if outer_service != self.service.is_web_service or protocol != self.service.protocol:
                            data = {}
                            data["protocol"] = protocol
                            data["outer_service"] = outer_service
                            data["inner_service"] = self.service.is_service
                            data["inner_service_port"] = self.service.service_port
                            if par_outer_ip != "":
                                data["outer_ip"] = par_outer_ip
                            logger.debug(data)
                            if protocol == "stream" :
                                if par_outer_ip != "":
                                    regionClient.modifyServiceProtocol(self.tenant.region, self.service.service_id, json.dumps(data))
                            elif protocol == "http" :
                                regionClient.modifyServiceProtocol(self.tenant.region, self.service.service_id, json.dumps(data))                                
                            self.service.protocol = protocol
                            self.service.is_web_service = outer_service
                            self.service.save()                            
                elif par_opt_type == "inner":
                    par_inner_service = request.POST["inner_service"]
                    inner_service = False
                    if par_inner_service == "start" or par_inner_service == "change":
                        inner_service = True
                    if inner_service != self.service.is_service:
                        baseService = BaseTenantService()
                        service_port = self.service.service_port
                        if inner_service:
                            deployPort = baseService.getMaxPort(self.tenant.tenant_id, self.service.service_key, self.service.service_alias) + 1
                            if deployPort > 0: 
                                service_port = deployPort + 1
                        data = {}
                        data["protocol"] = self.service.protocol
                        data["outer_service"] = self.service.is_web_service
                        data["inner_service"] = inner_service
                        data["inner_service_port"] = service_port
                        logger.debug(data)
                        regionClient.modifyServiceProtocol(self.tenant.region, self.service.service_id, json.dumps(data))
                        self.service.service_port = service_port
                        self.service.is_service = inner_service
                        self.service.save()
            result["status"] = "success"
        except Exception, e:
            logger.debug(e)
            result["status"] = "failure"
        return JsonResponse(result)


class ServiceUpgrade(AuthedView):
    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        result = {}
        if self.tenant.service_status == 2 and self.tenant.pay_type == "payed":
            result["status"] = "owed"
            return JsonResponse(result, status=200)
        oldVerion = self.service.deploy_version
        if oldVerion is not None and oldVerion != "":      
            curVersion = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            diffsec = int(curVersion) - int(oldVerion)
            if diffsec <= 90:
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
                if  upgrade_container_memory > 0 and upgrade_container_memory <= 4096 and left == 0:
                    upgrade_container_cpu = upgrade_container_memory / 128 * 20
                    # temp record service status
                    temData = {}
                    temData["service_id"] = self.service.service_id
                    temData["status"] = 2
                    old_status = regionClient.updateTenantServiceStatus(self.tenant.region, self.service.service_id, json.dumps(temData)) 
                    # calculate resource
                    diff_memory = upgrade_container_memory - int(old_container_memory)
                    tenantUsedResource = TenantUsedResource()
                    flag = tenantUsedResource.predict_next_memory(self.tenant, diff_memory) 
                    if not flag:
                        if self.tenant.pay_type == "free":
                            result["status"] = "over_memory"
                        else:
                            result["status"] = "over_money"
                        temData["service_id"] = self.service.service_id
                        temData["status"] = old_status
                        regionClient.updateTenantServiceStatus(self.tenant.region, self.service.service_id, json.dumps(temData))
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
                    regionClient.verticalUpgrade(self.tenant.region, self.service.service_id, json.dumps(body)) 
                result["status"] = "success"                       
            except Exception, e:
                self.service.min_cpu = old_container_cpu          
                self.service.min_memory = old_container_memory
                self.service.deploy_version = old_deploy_version
                self.service.save() 
                logger.exception(e)
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
                    old_status = regionClient.updateTenantServiceStatus(self.tenant.region, self.service.service_id, json.dumps(temData))
                    # calculate resource
                    diff_memory = (new_node_num - old_min_node) * self.service.min_memory                        
                    tenantUsedResource = TenantUsedResource()
                    flag = tenantUsedResource.predict_next_memory(self.tenant, diff_memory) 
                    if not flag:
                        if self.tenant.pay_type == "free":
                            result["status"] = "over_memory"
                        else:
                            result["status"] = "over_money"
                        temData["service_id"] = self.service.service_id
                        temData["status"] = old_status
                        regionClient.updateTenantServiceStatus(self.tenant.region, self.service.service_id, json.dumps(temData))
                        return JsonResponse(result, status=200)
                           
                    deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                                          
                    isResetStatus = False    
                    try:
                        body = {}
                        body["node_num"] = node_num   
                        body["deploy_version"] = deploy_version
                        regionClient.horizontalUpgrade(self.tenant.region, self.service.service_id, json.dumps(body))
                    except Exception, e:
                        logger.exception(e)
                        isResetStatus = True
                        
                    if not isResetStatus:
                        self.service.min_node = node_num
                        self.service.deploy_version = deploy_version
                        self.service.save()
                                                
                    if isResetStatus or new_node_num < old_min_node :
                        temData["service_id"] = self.service.service_id
                        temData["status"] = old_status
                        regionClient.updateTenantServiceStatus(self.tenant.region, self.service.service_id, json.dumps(temData))
                                        
                result["status"] = "success"
            except Exception, e:
                self.service.min_node = old_min_node
                self.service.deploy_version = old_deploy_version
                self.service.save()
                logger.exception(e)
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
            tenantS = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_alias=dep_service_alias)            
            if action == "add":
                baseService = BaseTenantService()
                baseService.create_service_dependency(tenant_id, service_id, tenantS.service_id, self.tenant.region)
            elif action == "cancel":
                try:
                    data = {}
                    data["tenant_id"] = tenant_id
                    data["dps_service_id"] = tenantS.service_id
                    data["service_id"] = service_id
                    regionClient.cancelServiceDependency(self.tenant.region, service_id, json.dumps(data))
                except Exception as e:
                    logger.exception(e)                
                TenantServiceRelation.objects.get(tenant_id=tenant_id, service_id=service_id, dep_service_id=tenantS.service_id).delete()
            result["status"] = "success"    
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)

class AllServiceInfo(AuthedView):
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        result = {}
        service_ids = []
        try:
            service_list = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id).values('ID', 'service_id', 'deploy_version')
            if self.has_perm('tenant.list_all_services'):
                for s in service_list:
                    if s['deploy_version'] is None or s['deploy_version'] == "":
                        child1 = {}
                        child1["status"] = "Undeployed"
                        result[s['service_id']] = child1
                    else:
                        service_ids.append(s['service_id'])                            
            else:
                service_pk_list = PermRelService.objects.filter(user_id=self.user.pk).values_list('service_id', flat=True)
                for s in service_list:
                    if s['ID'] in service_pk_list:
                            if s['deploy_version'] is None or s['deploy_version'] == "":
                                child1 = {}
                                child1["status"] = "Undeployed"
                                result[s.service_id] = child1
                            else:
                                service_ids.append(s['service_id'])        
            if len(service_ids) > 0:
                if self.tenant.service_status == 2 and self.tenant.pay_type == "payed":
                    for sid in service_ids:
                        child = {}
                        child["status"] = "Owed"
                        result[sid] = child
                else:
                    id_string = ','.join(service_ids)
                    bodys = regionClient.check_status(self.tenant.region, json.dumps({"service_ids": id_string}))
                    for sid in service_ids:
                        service = TenantServiceInfo.objects.get(service_id=sid)
                        body = bodys[sid]
                        nodeNum = 0
                        runningNum = 0
                        isDeploy = 0
                        child = {}
                        for item in body:
                            nodeNum += 1
                            status = body[item]['status']
                            if status == "Undeployed":
                                isDeploy = -1
                                break                      
                            elif status == 'Running':
                                runningNum += 1
                                isDeploy += 1
                            else:
                                isDeploy += 1
                        if isDeploy > 0:
                            if nodeNum == runningNum:
                                if runningNum > 0:
                                    child["status"] = "Running"
                                else:
                                    child["status"] = "Waiting"
                            else:
                                child["status"] = "Waiting"
                        elif isDeploy == -1 :
                            child["status"] = "Undeployed"
                        else:
                            child["status"] = "Closing"
                        result[sid] = child
        except Exception, e:
            tempIds = ','.join(service_ids)
            logger.debug(self.tenant.region + "-" + tempIds + " check_service_status is error")
            for sid in service_ids:
                child = {}
                child["status"] = "failure"
                result[sid] = child
        return JsonResponse(result)

class AllTenantsUsedResource(AuthedView):
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            service_ids = []
            serviceIds = ""
            service_list = TenantServiceInfo.objects.filter(tenant_id=self.tenant.tenant_id).values('ID', 'service_id', 'min_node', 'min_memory')
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
            result["service_ids"] = service_ids
            if len(service_ids) > 0:
                dsn = BaseConnection()
                query_sql = "select service_id,storage_disk,node_num,net_in,net_out from tenant_service_statics where tenant_id ='" + self.tenant.tenant_id + "' and service_id in(" + serviceIds + ")  order by id desc limit " + str(len(service_ids))
                sqlobjs = dsn.query(query_sql)
                for sqlobj in sqlobjs:                    
                    service_id = sqlobj["service_id"]
                    storageDisk = int(sqlobj["storage_disk"])
                    node_num = int(sqlobj["node_num"])
                    net_in = int(sqlobj["net_in"])
                    net_out = int(sqlobj["net_out"])
                    max_net = net_out
                    if net_in > net_out:
                        max_net = net_in
                    result[service_id + "_storage_memory"] = int(storageDisk * 0.01) + max_net
        except Exception as e:
            logger.exception(e)
        return JsonResponse(result)
            
        

class ServiceDetail(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            if self.tenant.service_status == 2 and self.tenant.pay_type == "payed":
                result["totalMemory"] = 0
                result["status"] = "Owed"
            else:
                if self.service.deploy_version is None or self.service.deploy_version == "":
                    result["totalMemory"] = 0
                    result["status"] = "Undeployed"
                else:
                    body = regionClient.check_service_status(self.tenant.region, self.service.service_id)
                    nodeNum = 0
                    runningNum = 0
                    isDeploy = 0
                    for item in body:
                        nodeNum += 1
                        status = body[item]['status']
                        if status == "Undeployed":
                            isDeploy = -1
                            break
                        elif status == "Running":
                            runningNum += 1
                            isDeploy += 1
                        else:
                            isDeploy += 1                    
                    if isDeploy > 0:                
                        if nodeNum == runningNum :
                            if runningNum > 0:
                                result["totalMemory"] = runningNum * self.service.min_memory
                                result["status"] = "Running"
                            else:
                                result["totalMemory"] = 0
                                result["status"] = "Waiting"
                        else:
                            result["totalMemory"] = 0
                            result["status"] = "Waiting"
                    elif isDeploy == -1 :
                        result["totalMemory"] = 0
                        result["status"] = "Undeployed"
                    else:
                        result["totalMemory"] = 0
                        result["status"] = "Closing"
        except Exception, e:
            logger.debug(self.tenant.region + "-" + self.service.service_id + " check_service_status is error")
            result["totalMemory"] = 0
            result['status'] = "failure"
        return JsonResponse(result)

class ServiceNetAndDisk(AuthedView):
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
            
            tenantServiceStaticsList = TenantServiceStatics.objects.filter(tenant_id=tenant_id, service_id=service_id).order_by('-ID')[0:1]
            if tenantServiceStaticsList is not None and len(tenantServiceStaticsList) > 0 :
                tenantServiceStatics = tenantServiceStaticsList[0]
                storageDisk = tenantServiceStatics.storage_disk
                result["disk"] = storageDisk
                result["bytesin"] = tenantServiceStatics.net_in
                result["bytesout"] = tenantServiceStatics.net_out
                max_net = tenantServiceStatics.net_in
                if tenantServiceStatics.net_in < tenantServiceStatics.net_out:
                    max_net = tenantServiceStatics.net_out
                result["disk_memory"] = int(storageDisk * 0.01) + max_net
        except Exception, e:
            logger.exception(e)
        return JsonResponse(result)

class ServiceLog(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        try:
            if self.service.deploy_version is None or self.service.deploy_version == "":
                return JsonResponse({})
            else:
                action = request.GET.get("action", "")
                service_id = self.service.service_id
                tenant_id = self.service.tenant_id
                body = {}
                body["tenant_id"] = tenant_id                    
                if action == "operate":                   
                    body = regionClient.get_userlog(self.tenant.region, service_id, json.dumps(body))
                    return JsonResponse(body)
                elif action == "service":                    
                    body = regionClient.get_log(self.tenant.region, service_id, json.dumps(body))
                    return JsonResponse(body)
                return JsonResponse({})
        except Exception as e:
            logger.info("%s" % e)
        return JsonResponse({})
    
    
class ServiceCheck(AuthedView):
    
    def sendCodeCheckMsg(self):
        data = {}
        data["tenant_id"] = self.service.tenant_id
        data["service_id"] = self.service.service_id      
        if self.service.code_from != "github":
             gitUrl = "--branch " + self.service.code_version + " --depth 1 " + self.service.git_url
             data["git_url"] = gitUrl
        else:
            clone_url = self.service.git_url
            code_user = clone_url.split("/")[3]
            code_project_name = clone_url.split("/")[4].split(".")[0]
            createUser = Users.objects.get(user_id=self.service.creater)
            clone_url = "https://" + createUser.github_token + "@github.com/" + code_user + "/" + code_project_name + ".git"
            gitUrl = "--branch " + self.service.code_version + " --depth 1 " + clone_url
            data["git_url"] = gitUrl
        task = {}
        task["tube"] = "code_check"
        task["data"] = data
        task["service_id"] = self.service.service_id
        regionClient.writeToRegionBeanstalk(self.tenant.region, self.service.service_id, json.dumps(task))
    
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
        return JsonResponse(result)
    
class ServiceMappingPort(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            body = regionClient.findMappingPort(self.tenant.region, self.service.service_id)
            port = body["port"]
            ip = body["ip"]
            result["port"] = port
            result["ip"] = ip
        except Exception as e:
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
                
                num = ServiceDomain.objects.filter(service_name=tenantService.service_alias).count()
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
                regionClient.addUserDomain(self.tenant.region, json.dumps(data))
            elif action == "close":
                servicerDomain = ServiceDomain.objects.get(service_name=tenantService.service_alias)
                data = {}
                data["service_id"] = servicerDomain.service_id
                data["domain"] = servicerDomain.domain_name
                data["pool_name"] = self.tenantName + "@" + self.serviceAlias + ".Pool" 
                regionClient.deleteUserDomain(self.tenant.region, json.dumps(data))
                ServiceDomain.objects.filter(service_name=tenantService.service_alias).delete()
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result)
