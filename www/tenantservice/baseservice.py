# -*- coding: utf8 -*-
import datetime
import json

from www.db import BaseConnection
from www.models import TenantServiceInfo, PermRelTenant, TenantServiceLog, TenantServiceRelation, TenantServiceStatics, TenantServiceAuth, TenantServiceEnvVar
from www.service_http import RegionServiceApi
from django.conf import settings

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()

class BaseTenantService(object):
    
    def get_service_list(self, tenant_pk, user_pk, tenant_id):
        my_tenant_identity = PermRelTenant.objects.get(tenant_id=tenant_pk, user_id=user_pk).identity
        if my_tenant_identity in ('admin', 'developer', 'viewer'):
            services = TenantServiceInfo.objects.filter(tenant_id=tenant_id)
        else:
            dsn = BaseConnection()
            query_sql = '''
                select s.* from tenant_service s, service_perms sp where s.tenant_id = "{tenant_id}"
                and sp.user_id = {user_id} and sp.service_id = s.ID;
                '''.format(tenant_id=tenant_id, user_id=user_pk)
            services = dsn.query(query_sql)
        return services
    
    def getMaxPort(self, tenant_id, service_key, service_alias):
        cur_service_port = 0
        dsn = BaseConnection()
        query_sql = '''select max(service_port) as service_port from tenant_service where tenant_id="{tenant_id}" and service_key="{service_key}" and service_alias !="{service_alias}";
            '''.format(tenant_id=tenant_id, service_key=service_key, service_alias=service_alias)
        data = dsn.query(query_sql)
        logger.debug(data)
        if data is not None:
           temp = data[0]["service_port"]
           if temp is not None:
              cur_service_port = int(temp) 
        return cur_service_port    

    def create_service(self, service_id, tenant_id, service_alias, service, creater):        
        service_port = service.inner_port
        if  service.is_service:
            deployPort = self.getMaxPort(tenant_id, service.service_key, service_alias)
            if deployPort > 0:
                service_port = deployPort + 1
            
        tenantServiceInfo = {}
        tenantServiceInfo["service_id"] = service_id
        tenantServiceInfo["tenant_id"] = tenant_id
        tenantServiceInfo["service_key"] = service.service_key
        tenantServiceInfo["service_alias"] = service_alias
        tenantServiceInfo["service_region"] = 'v1'
        tenantServiceInfo["desc"] = service.desc
        tenantServiceInfo["category"] = service.category
        tenantServiceInfo["service_port"] = service_port
        tenantServiceInfo["is_web_service"] = service.is_web_service
        tenantServiceInfo["image"] = service.image
        tenantServiceInfo["cmd"] = service.cmd
        tenantServiceInfo["setting"] = service.setting
        is_auth = False
        password = "admin"
        if service.is_init_accout:
            is_auth = True
            uk = service.service_key.upper() + "_USER=" + "admin"
            up = service.service_key.upper() + "_PASS=" + service_id[:8]
            envar = service.env + "," + uk + "," + up + ","
            password = service_id[:8]
            ta = TenantServiceAuth(service_id=service_id, user="admin", password=password)
            ta.save()
        else:
            envar = service.env + ","
        tenantServiceInfo["env"] = envar
        tenantServiceInfo["min_node"] = service.min_node
        tenantServiceInfo["min_cpu"] = service.min_cpu
        tenantServiceInfo["min_memory"] = service.min_memory
        tenantServiceInfo["inner_port"] = service.inner_port
        tenantServiceInfo["version"] = service.version
        volume_path = ""
        host_path = ""
        if service.volume_mount_path is not None and service.volume_mount_path != "":
            volume_path = service.volume_mount_path
            host_path = "/grdata/tenant/" + tenant_id + "/service/" + service_id
        tenantServiceInfo["volume_mount_path"] = volume_path
        tenantServiceInfo["host_path"] = host_path
        if service.service_key == 'application':            
            tenantServiceInfo["deploy_version"] = ""
        else:
            tenantServiceInfo["deploy_version"] = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        tenantServiceInfo["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenantServiceInfo["git_project_id"] = 0
        tenantServiceInfo["service_type"] = service.service_type
        tenantServiceInfo["creater"] = creater
        tenantServiceInfo["total_memory"] = service.min_node * service.min_memory
        if service.is_web_service:
            tenantServiceInfo["protocol"] = 'http'
        else:
            tenantServiceInfo["protocol"] = 'stream'
        tenantServiceInfo["is_service"] = service.is_service                        
        newTenantService = TenantServiceInfo(**tenantServiceInfo)
        newTenantService.save()
        
        # if service is inner service need to save env var
        if service.is_service:
            self.saveServiceEnvVar(tenant_id, service_id, u"连接地址", service.service_key.upper() + "_HOST", "127.0.0.1", False)
            self.saveServiceEnvVar(tenant_id, service_id, u"端口", service.service_key.upper() + "_PORT", service_port, False)
            if service.is_init_accout:
                self.saveServiceEnvVar(tenant_id, service_id, u"用户名", service.service_key.upper() + "_USER", "admin", True)
                self.saveServiceEnvVar(tenant_id, service_id, u"密码", service.service_key.upper() + "_PASSWORD", password, True)
        return newTenantService
        
    def create_region_service(self, newTenantService, service, domain, region):
        data = {}
        data["tenant_id"] = newTenantService.tenant_id
        data["service_id"] = newTenantService.service_id
        data["service_key"] = newTenantService.service_key
        data["comment"] = newTenantService.desc
        data["image_name"] = newTenantService.image
        data["container_cpu"] = newTenantService.min_cpu
        data["container_memory"] = newTenantService.min_memory
        data["volume_path"] = "vol" + newTenantService.service_id[0:10]
        data["volume_mount_path"] = newTenantService.volume_mount_path
        data["host_path"] = newTenantService.host_path
        data["extend_method"] = service.extend_method
        data["status"] = 0
        data["replicas"] = newTenantService. min_node
        data["service_alias"] = newTenantService.service_alias
        data["service_port"] = newTenantService.service_port
        data["service_version"] = newTenantService.version
        data["container_env"] = newTenantService.env
        data["container_port"] = newTenantService.inner_port
        data["container_cmd"] = newTenantService.cmd
        data["node_label"] = ""
        data["is_create_service"] = newTenantService.is_service
        data["is_binding_port"] = newTenantService.is_web_service
        data["deploy_version"] = newTenantService.deploy_version
        data["domain"] = domain
        data["category"] = newTenantService.category
        data["protocol"] = newTenantService.protocol        
        logger.debug(newTenantService.tenant_id + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        regionClient.create_service(region, newTenantService.tenant_id, json.dumps(data))
        logger.debug(newTenantService.tenant_id + " end create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        
    def record_service_log(self, user_pk, user_nike_name, service_id, tenant_id):
        log = {}
        log["user_id"] = user_pk
        log["user_name"] = user_nike_name
        log["service_id"] = service_id
        log["tenant_id"] = tenant_id
        log["action"] = "deploy"
        log["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenantServiceLog = TenantServiceLog(**log)
        tenantServiceLog.save()
        
        
    def create_service_dependency(self, tenant_id, service_id, dep_service_id, region):
        dependS = TenantServiceInfo.objects.get(service_id=dep_service_id)
        task = {}
        task["dep_service_id"] = dep_service_id
        task["tenant_id"] = tenant_id
        task["dep_service_type"] = dependS.service_type
        logger.debug(json.dumps(task))
        
        regionClient.createServiceDependency(region, service_id, json.dumps(task))
        tsr = TenantServiceRelation()
        tsr.tenant_id = tenant_id
        tsr.service_id = service_id
        tsr.dep_service_id = dep_service_id
        tsr.dep_service_type = dependS.service_type
        tsr.dep_order = 0
        tsr.save()
        
    def cancel_service_dependency(self, tenant_id, service_id, dep_service_id, region):
        task = {}        
        task["dep_service_id"] = dep_service_id
        task["tenant_id"] = tenant_id
        task["dep_service_type"] = "v"
        logger.debug(json.dumps(task))
        regionClient.cancelServiceDependency(region, service_id, json.dumps(task))
        TenantServiceRelation.objects.get(service_id=service_id, dep_service_id=dep_service_id).delete()
        
    def create_service_env(self, tenant_id, service_id, region):
        tenantServiceEnvList = TenantServiceEnvVar.objects.filter(service_id=service_id)
        data = {}
        for tenantServiceEnv in tenantServiceEnvList:
            data[tenantServiceEnv.attr_name] = tenantServiceEnv.attr_value
        task = {}
        task["tenant_id"] = tenant_id
        task["attr"] = data
        regionClient.createServiceEnv(region, service_id, json.dumps(task))
    
    def saveServiceEnvVar(self, tenant_id, service_id, name, attr_name, attr_value, isChange):
        tenantServiceEnvVar = {} 
        tenantServiceEnvVar["tenant_id"] = tenant_id
        tenantServiceEnvVar["service_id"] = service_id
        tenantServiceEnvVar["name"] = name
        tenantServiceEnvVar["attr_name"] = attr_name
        tenantServiceEnvVar["attr_value"] = attr_value
        tenantServiceEnvVar["is_change"] = isChange
        TenantServiceEnvVar(**tenantServiceEnvVar).save()

class TenantUsedResource(object):
        
    def __init__(self):
        self.feerule = settings.REGION_RULE
        
    def calculate_used_resource(self, tenant):
        totalMemory = 0 
        if tenant.pay_type == "free":
            dsn = BaseConnection()
            query_sql = '''
                select sum(s.min_node * s.min_memory) as totalMemory from tenant_service s where s.tenant_id = "{tenant_id}"
                '''.format(tenant_id=tenant.tenant_id)
            sqlobj = dsn.query(query_sql)
            if sqlobj is not None and len(sqlobj) > 0:
                oldMemory = sqlobj[0]["totalMemory"]
                if oldMemory is not None:                    
                    totalMemory = int(oldMemory)
        return totalMemory

    def calculate_real_used_resource(self, tenant):
        totalMemory = 0 
        running_data = regionClient.getTenantRunningServiceId(tenant.region, tenant.tenant_id)
        logger.debug(running_data)
        dsn = BaseConnection()
        query_sql = '''
            select service_id, (s.min_node * s.min_memory) as apply_memory, total_memory  from tenant_service s where s.tenant_id = "{tenant_id}"
            '''.format(tenant_id=tenant.tenant_id)
        sqlobjs = dsn.query(query_sql)
        if sqlobjs is not None and len(sqlobjs) > 0:
            for sqlobj in sqlobjs:
                service_id = sqlobj["service_id"]
                apply_memory = sqlobj["apply_memory"]
                total_memory = sqlobj["total_memory"]
                real_memory = running_data.get(service_id)
                disk_storage = total_memory - int(apply_memory)
                if disk_storage < 0 :
                    disk_storage = 0                                    
                if real_memory is not None and real_memory != "" :
                    totalMemory = totalMemory + int(apply_memory) + disk_storage
                else:
                    totalMemory = totalMemory + disk_storage                        
        return totalMemory
    
    def predict_next_memory(self, tenant, newAddMemory):
        result = False
        if tenant.pay_type == "free":
            tm = self.calculate_real_used_resource(tenant) + newAddMemory
            logger.debug(tenant.tenant_id + " used memory " + str(tm))
            if tm <= tenant.limit_memory:
               result = True
        elif tenant.pay_type == "payed":
            tm = self.calculate_real_used_resource(tenant) + newAddMemory
            ruleJson = self.feerule[tenant.region]
            total_money = float(ruleJson['unit_money']) * (tm * 1.0 / 1024)
            logger.debug(tenant.tenant_id + "use memory " + str(tm) + " used money " + str(total_money))
            if tenant.balance >= total_money:
                result = True
        elif tenant.pay_type == "unpay":
            result = True
        return result
