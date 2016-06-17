# -*- coding: utf8 -*-
import datetime
import json

from www.db import BaseConnection
from www.models import Users, TenantServiceInfo, PermRelTenant, TenantServiceLog, TenantServiceRelation, TenantServiceAuth, TenantServiceEnvVar, TenantRegionInfo, TenantServicesPort, TenantRegionPayModel, TenantServiceMountRelation
from www.service_http import RegionServiceApi
from django.conf import settings
from www.monitorservice.monitorhook import MonitorHook
from www.gitlab_http import GitlabApi
from www.github_http import GitHubApi
from www.utils.giturlparse import parse as git_url_parse

import logging
logger = logging.getLogger('default')

monitorhook = MonitorHook()
regionClient = RegionServiceApi()
gitClient = GitlabApi()
gitHubClient = GitHubApi()


class OpenTenantServiceManager(object):

    def _getMaxPort(self, tenant_id, service_key, service_alias):
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
    
    def _getInnerServicePort(self, tenant_id, service_key):
        cur_service_port = 0
        dsn = BaseConnection()
        query_sql = '''select max(service_port) as service_port from tenant_service where tenant_id="{tenant_id}" and service_key="{service_key}";
            '''.format(tenant_id=tenant_id, service_key=service_key)
        data = dsn.query(query_sql)
        logger.debug(data)
        if data is not None:
            temp = data[0]["service_port"]
            if temp is not None:
                cur_service_port = int(temp)
        return cur_service_port

    def _prepare_mapping_port(self, service, container_port):
        port_list = TenantServicesPort.objects.filter(tenant_id=service.tenant_id, mapping_port__gt=container_port).values_list(
            'mapping_port', flat=True).order_by('mapping_port')

        port_list = list(port_list)
        port_list.insert(0, container_port)
        max_port = reduce(lambda x, y: y if (y - x) == 1 else x, port_list)
        return max_port + 1
    
    def create_service(self, tenant_name, service_name, image, region):
        tenantServiceInfo = {}
        tenantServiceInfo["service_id"] = service_id
        tenantServiceInfo["tenant_id"] = tenant_id
        tenantServiceInfo["service_key"] = service.service_key
        tenantServiceInfo["service_alias"] = service_alias
        tenantServiceInfo["service_region"] = region
        tenantServiceInfo["desc"] = service.desc
        tenantServiceInfo["category"] = service.category
        tenantServiceInfo["image"] = service.image
        tenantServiceInfo["cmd"] = service.cmd
        tenantServiceInfo["setting"] = service.setting
        tenantServiceInfo["extend_method"] = service.extend_method
        tenantServiceInfo["env"] = service.env
        tenantServiceInfo["min_node"] = service.min_node
        tenantServiceInfo["min_cpu"] = service.min_cpu
        tenantServiceInfo["min_memory"] = service.min_memory
        tenantServiceInfo["inner_port"] = service.inner_port
        tenantServiceInfo["version"] = service.version
        tenantServiceInfo["namespace"] = service.namespace
        volume_path = ""
        host_path = ""
        if bool(service.volume_mount_path):
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
        newTenantService = TenantServiceInfo(**tenantServiceInfo)
        newTenantService.save()
        return newTenantService
    
    def create_region_service(self, newTenantService, do_deploy=True):
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
        data["extend_method"] = newTenantService.extend_method
        data["status"] = 0
        data["replicas"] = newTenantService.min_node
        data["service_alias"] = newTenantService.service_alias
        data["service_version"] = newTenantService.version
        data["container_env"] = newTenantService.env
        data["container_cmd"] = newTenantService.cmd
        data["node_label"] = ""
        data["deploy_version"] = newTenantService.deploy_version if do_deploy else None
        data["domain"] = domain
        data["category"] = newTenantService.category
        data["operator"] = nick_name
        data["service_type"] = newTenantService.service_type
        data["extend_info"] = {"ports": [], "envs": []}
        data["namespace"] = newTenantService.namespace
    
        ports_info = TenantServicesPort.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        if ports_info:
            data["extend_info"]["ports"] = list(ports_info)
    
        envs_info = TenantServiceEnvVar.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if envs_info:
            data["extend_info"]["envs"] = list(envs_info)
    
        logger.debug(newTenantService.tenant_id + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        regionClient.create_service(region, newTenantService.tenant_id, json.dumps(data))
        logger.debug(newTenantService.tenant_id + " end create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
    
    def delete_service(self, tenant_name, service_name, region):
        return None
    
    def bind_domain(self, tenant_name, service_name, domain_name, region):
        return None
    
    def stop_service(self, tenant_name, service_name, region):
        return None
    
    def start_service(self, tenant_name, service_name, region):
        return None
    
    def get_service_status(self, tenant_name, service_name, region):
        return None