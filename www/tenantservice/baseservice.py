# -*- coding: utf8 -*-
import datetime
import json

from www.db import BaseConnection
from www.models import TenantServiceInfo, PermRelTenant, TenantServiceLog, TenantServiceRelation, TenantServiceStatics
from www.service_http import RegionServiceApi
from www.etcd_client import EtcdClient
from django.conf import settings

import logging
logger = logging.getLogger('default')

client = RegionServiceApi()

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

    def create_service(self, service_id, tenant_id, service_alias, service, creater):        
        deployNum = 0
        if  service.is_service:
            deployNum = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_key=service.service_key).count()
            
        tenantServiceInfo = {}
        tenantServiceInfo["service_id"] = service_id
        tenantServiceInfo["tenant_id"] = tenant_id
        tenantServiceInfo["service_key"] = service.service_key
        tenantServiceInfo["service_alias"] = service_alias
        tenantServiceInfo["service_region"] = 'v1'
        tenantServiceInfo["desc"] = service.desc
        tenantServiceInfo["category"] = service.category
        tenantServiceInfo["service_port"] = service.inner_port + deployNum
        tenantServiceInfo["is_web_service"] = service.is_web_service
        tenantServiceInfo["image"] = service.image
        tenantServiceInfo["cmd"] = service.cmd
        tenantServiceInfo["setting"] = service.setting
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
        newTenantService = TenantServiceInfo(**tenantServiceInfo)
        newTenantService.save()
        return newTenantService
        
        
    def create_region_service(self, newTenantService, service, domain):
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
        data["status"] = False
        data["replicas"] = newTenantService. min_node
        data["service_alias"] = newTenantService.service_alias
        data["service_port"] = newTenantService.service_port
        data["service_version"] = newTenantService.version
        data["container_env"] = newTenantService.env
        data["container_port"] = newTenantService.inner_port
        data["container_cmd"] = newTenantService.cmd
        data["node_label"] = ""
        data["is_create_service"] = service.is_service
        data["is_binding_port"] = newTenantService.is_web_service
        data["deploy_version"] = newTenantService.deploy_version
        data["domain"] = domain
        data["category"] = newTenantService.category
        client.create_service(newTenantService.tenant_id, json.dumps(data))
        
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
        
        
    def create_service_dependency(self, tenant_id, service_id, dep_service_id):
        tenantS = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_id=dep_service_id)
        etcdPath = '/goodrain/' + tenant_id + '/services/' + service_id + '/dependency/' + tenantS.service_id
        etcdClient = EtcdClient(settings.ETCD.get('host'), settings.ETCD.get('port'))
        depNum = TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id, dep_service_type=tenantS.service_type).count()
        attr = tenantS.service_type.upper()
        if depNum > 0 :
            attr = attr + "_" + tenantS.service_alias.upper()
        data = {}
        data[attr + "_HOST"] = "127.0.0.1"
        data[attr + "_PORT"] = tenantS.service_port
        data[attr + "_USER"] = "admin"
        data[attr + "_PASSWORD"] = "admin"
        etcdClient.write(etcdPath, json.dumps(data))
        res = etcdClient.get(etcdPath)
        logger.debug(res)
        tsr = TenantServiceRelation()
        tsr.tenant_id = tenant_id
        tsr.service_id = service_id
        tsr.dep_service_id = tenantS.service_id
        tsr.dep_service_type = tenantS.service_type
        tsr.dep_order = depNum + 1
        tsr.save()
                        
