# -*- coding: utf8 -*-
import datetime
import json

from www.db import BaseConnection
from www.models import TenantServiceInfo, TenantServiceInfoDelete, \
    TenantServiceRelation, TenantServiceAuth, TenantServiceEnvVar, \
    TenantRegionInfo, TenantServicesPort, TenantServiceMountRelation, \
    TenantServiceEnv, ServiceDomain, Tenants, AppService
from www.service_http import RegionServiceApi
from django.conf import settings
from www.monitorservice.monitorhook import MonitorHook
from www.gitlab_http import GitlabApi
from www.github_http import GitHubApi

import logging
logger = logging.getLogger('default')

monitorhook = MonitorHook()
regionClient = RegionServiceApi()
gitClient = GitlabApi()
gitHubClient = GitHubApi()


class OpenTenantServiceManager(object):

    def __init__(self):
        self.feerule = settings.REGION_RULE
        self.MODULES = settings.MODULES

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

    def create_service(self, service_id, tenant_id, service_alias, service, creater, region):
        """创建console服务"""
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

    def create_region_service(self, newTenantService, domain, region, nick_name, do_deploy=True):
        """创建region服务"""
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
    
    def delete_service(self, tenant_name, service_name, username):
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_name)
        except Tenants.DoesNotExist:
            logger.error("openapi.services", "Tenant {0} is not exists".format(tenant_name))
            return 405, False, u"租户不存在,请检查租户名称"
        except TenantServiceInfo.DoesNotExist:
            logger.debug("openapi.services", "Tenant {0} ServiceAlias {1} is not exists".format(tenant_name, service_name))
            return 405, False, u"服务名称不存在"

        try:
            # 检查服务关联
            published = AppService.objects.filter(service_id=service.service_id).count()
            if published:
                logger.debug("openapi.services", "services has related published!".format(tenant_name, service_name))
                return 406, False, u"关联了已发布服务, 不可删除"
            # 检查服务依赖
            dep_service_ids = TenantServiceRelation.objects.filter(dep_service_id=service.service_id).values("service_id")
            if len(dep_service_ids) > 0:
                sids = []
                for ds in dep_service_ids:
                    sids.append(ds["service_id"])
                if len(sids) > 0:
                    alias_list = TenantServiceInfo.objects.filter(service_id__in=sids).values('service_alias')
                    dep_alias = ""
                    for alias in alias_list:
                        if dep_alias != "":
                            dep_alias += ","
                        dep_alias = dep_alias + alias["service_alias"]
                    logger.debug("openapi.services", "{0} depended current services, cannot delete!".format(dep_alias))
                    return 407, False, u"{0} 依赖当前服务,不可删除".format(dep_alias)
            # 检查挂载依赖
            dep_service_ids = TenantServiceMountRelation.objects.filter(dep_service_id=service.service_id).values("service_id")
            if len(dep_service_ids) > 0:
                sids = []
                for ds in dep_service_ids:
                    sids.append(ds["service_id"])
                if len(sids) > 0:
                    alias_list = TenantServiceInfo.objects.filter(service_id__in=sids).values('service_alias')
                    dep_alias = ""
                    for alias in alias_list:
                        if dep_alias != "":
                            dep_alias += ","
                        dep_alias = dep_alias + alias["service_alias"]
                    logger.debug("openapi.services", "{0} mnt depended current services, cannot delete!".format(dep_alias))
                    return 408, False, u"{0} 挂载依赖当前服务,不可删除".format(dep_alias)
            # 删除服务
            # 备份删除数据
            data = service.toJSON()
            tenant_service_info_delete = TenantServiceInfoDelete(**data)
            tenant_service_info_delete.save()
            # 删除region服务
            try:
                regionClient.delete(service.service_region, service.service_id)
            except Exception as e:
                logger.exception("openapi.services", e)
            # 删除gitlab代码,api中不需要
            # if self.service.code_from == 'gitlab_new' and service.git_project_id > 0:
            #     codeRepositoriesService.deleteProject(service)
            # 删除console服务
            TenantServiceInfo.objects.get(service_id=service.service_id).delete()
            # env/auth/domain/relationship/envVar delete
            TenantServiceEnv.objects.filter(service_id=service.service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service.service_id).delete()
            ServiceDomain.objects.filter(service_id=service.service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service.service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service.service_id).delete()
            TenantServiceMountRelation.objects.filter(service_id=service.service_id).delete()
            TenantServicesPort.objects.filter(service_id=service.service_id).delete()
            monitorhook.serviceMonitor(username, service, 'app_delete', True)
            logger.debug("openapi.services", "delete service.result:success")
            return 200, True, u"删除成功"
        except Exception as e:
            logger.exception("openapi.services", e)
            logger.debug("openapi.services", "delete service.result:failure")
            return 409, False, u"删除失败"

    def domain_service(self, action, service, domain_name, tenant_name, username):
        try:
            if action == "start":
                domainNum = ServiceDomain.objects.filter(domain_name=domain_name).count()
                if domainNum > 0:
                    return 201, False, "domain name exists"

                num = ServiceDomain.objects.filter(service_id=service.service_id).count()
                old_domain_name = "goodrain"
                if num == 0:
                    domain = {}
                    domain["service_id"] = service.service_id
                    domain["service_name"] = service.service_alias
                    domain["domain_name"] = domain_name
                    domain["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    domaininfo = ServiceDomain(**domain)
                    domaininfo.save()
                else:
                    domain = ServiceDomain.objects.get(service_id=service.service_id)
                    old_domain_name = domain.domain_name
                    domain.domain_name = domain_name
                    domain.save()
                data = {}
                data["service_id"] = service.service_id
                data["new_domain"] = domain_name
                data["old_domain"] = old_domain_name
                data["pool_name"] = tenant_name + "@" + service.service_alias + ".Pool"
                regionClient.addUserDomain(service.service_region, json.dumps(data))
                monitorhook.serviceMonitor(username, service, 'domain_add', True)
            elif action == "close":
                servicerDomain = ServiceDomain.objects.get(service_id=service.service_id)
                data = {}
                data["service_id"] = servicerDomain.service_id
                data["domain"] = servicerDomain.domain_name
                data["pool_name"] = tenant_name + "@" + service.service_alias + ".Pool"
                regionClient.deleteUserDomain(service.service_region, json.dumps(data))
                ServiceDomain.objects.filter(service_id=service.service_id).delete()
                monitorhook.serviceMonitor(username, service, 'domain_delete', True)
            return 200, True, "success"
        except Exception as e:
            logger.exception("openapi.services", e)
            monitorhook.serviceMonitor(username, service, 'domain_manage', False)
            return 201, False, "failure"

    def query_domain(self, service):
        domain_list = ServiceDomain.objects.filter(service_id=service.service_id)
        if len(domain_list) > 0:
            return [x.domain_name for x in domain_list]
        else:
            return []

    def stop_service(self, service, username):
        try:
            body = {}
            body["operator"] = str(username)
            regionClient.stop(service.service_region, service.service_id, json.dumps(body))
            monitorhook.serviceMonitor(username, service, 'app_stop', True)
            return 200, True, "success"
        except Exception as e:
            logger.exception("openapi.services", e)
            monitorhook.serviceMonitor(username, service, 'app_stop', False)
            return 201, False, "failure"

    def start_service(self, tenant, service, username):
        try:
            # calculate resource
            diff_memory = service.min_node * service.min_memory
            rt_type, flag = self.predict_next_memory(tenant, service, diff_memory, False)
            if not flag:
                if rt_type == "memory":
                    return 201, False, "over_memory"
                else:
                    return 202, False, "over_money"

            body = {}
            body["deploy_version"] = service.deploy_version
            body["operator"] = str(username)
            regionClient.restart(service.service_region, service.service_id, json.dumps(body))
            monitorhook.serviceMonitor(username, service, 'app_start', True)
            return 200, True, "success"
        except Exception as e:
            logger.exception("openapi.services", e)
            monitorhook.serviceMonitor(username, service, 'app_start', False)
            return 203, False, "failed"
    
    def status_service(self, service):
        result = {}
        try:
            if service.deploy_version is None or service.deploy_version == "":
                result["totalMemory"] = 0
                result["status"] = "Undeployed"
                return 200, True, result
            else:
                body = regionClient.check_service_status(service.service_region, service.service_id)
                status = body[service.service_id]
                if status == "running":
                    result["totalMemory"] = service.min_node * service.min_memory
                else:
                    result["totalMemory"] = 0
                result["status"] = status
            return 200, True, result
        except Exception as e:
            logger.exception("openapi.services", e)
            logger.debug(service.service_region + "-" + service.service_id + " check_service_status is error")
            result["totalMemory"] = 0
            result['status'] = "failure"
            return 201, False, result

    def predict_next_memory(self, tenant, cur_service, newAddMemory, ischeckStatus):
        result = True
        rt_type = "memory"
        if self.MODULES["Memory_Limit"]:
            result = False
            if ischeckStatus:
                newAddMemory = newAddMemory + self._curServiceMemory(cur_service)
            if tenant.pay_type == "free":
                tm = self._calculate_real_used_resource(tenant) + newAddMemory
                logger.debug(tenant.tenant_id + " used memory " + str(tm))
                if tm <= tenant.limit_memory:
                    result = True
            elif tenant.pay_type == "payed":
                tm = self._calculate_real_used_resource(tenant) + newAddMemory
                guarantee_memory = self._calculate_real_used_resource(tenant)
                logger.debug(tenant.tenant_id + " used memory:" + str(tm) + " guarantee_memory:" + str(guarantee_memory))
                if tm - guarantee_memory <= 102400:
                    ruleJson = self.feerule[cur_service.service_region]
                    unit_money = 0
                    if tenant.pay_level == "personal":
                        unit_money = float(ruleJson['personal_money'])
                    elif tenant.pay_level == "company":
                        unit_money = float(ruleJson['company_money'])
                    total_money = unit_money * (tm * 1.0 / 1024)
                    logger.debug(tenant.tenant_id + " use memory " + str(tm) + " used money " + str(total_money))
                    if tenant.balance >= total_money:
                        result = True
                    else:
                        rt_type = "money"
            elif tenant.pay_type == "unpay":
                result = True
        return rt_type, result

    def addServicePort(self, service, is_init_account, container_port=0, protocol='', port_alias='', is_inner_service=False, is_outer_service=False):
        port = TenantServicesPort(tenant_id=service.tenant_id, service_id=service.service_id, container_port=container_port,
                                  protocol=protocol, port_alias=port_alias, is_inner_service=is_inner_service,
                                  is_outer_service=is_outer_service)
        try:
            env_prefix = port_alias.upper() if bool(port_alias) else service.service_key.upper()
            if is_inner_service:
                mapping_port = self._prepare_mapping_port(service, container_port)
                port.mapping_port = mapping_port
                self._saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"连接地址", env_prefix + "_HOST", "127.0.0.1", False, scope="outer")
                self._saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"端口", env_prefix + "_PORT", mapping_port, False, scope="outer")
            if is_init_account:
                password = service.service_id[:8]
                TenantServiceAuth.objects.create(service_id=service.service_id, user="admin", password=password)
                self._saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"用户名", env_prefix + "_USER", "admin", False, scope="both")
                self._saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"密码", env_prefix + "_PASS", password, False, scope="both")
            port.save()
        except Exception as e:
            logger.exception("openapi.services", e)

    def _saveServiceEnvVar(self, tenant_id, service_id, container_port, name, attr_name, attr_value, isChange, scope="outer"):
        tenantServiceEnvVar = {}
        tenantServiceEnvVar["tenant_id"] = tenant_id
        tenantServiceEnvVar["service_id"] = service_id
        tenantServiceEnvVar['container_port'] = container_port
        tenantServiceEnvVar["name"] = name
        tenantServiceEnvVar["attr_name"] = attr_name
        tenantServiceEnvVar["attr_value"] = attr_value
        tenantServiceEnvVar["is_change"] = isChange
        tenantServiceEnvVar["scope"] = scope
        TenantServiceEnvVar(**tenantServiceEnvVar).save()

    def _curServiceMemory(self, cur_service):
        memory = 0
        try:
            body = regionClient.check_service_status(cur_service.service_region, cur_service.service_id)
            status = body[cur_service.service_id]
            if status != "running":
                memory = cur_service.min_node * cur_service.min_memory
        except Exception as e:
            logger.exception("openapi.services", e)
        return memory

    def _calculate_real_used_resource(self, tenant):
        totalMemory = 0
        tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True)
        running_data = {}
        for tenant_region in tenant_region_list:
            logger.debug(tenant_region.region_name)
            temp_data = regionClient.getTenantRunningServiceId(tenant_region.region_name, tenant_region.tenant_id)
            logger.debug(temp_data)
            if len(temp_data["data"]) > 0:
                running_data.update(temp_data["data"])
        logger.debug(running_data)
        dsn = BaseConnection()
        query_sql = '''select service_id, (s.min_node * s.min_memory) as apply_memory, total_memory  from tenant_service s where s.tenant_id = "{tenant_id}"'''.format(tenant_id=tenant.tenant_id)
        sqlobjs = dsn.query(query_sql)
        if sqlobjs is not None and len(sqlobjs) > 0:
            for sqlobj in sqlobjs:
                service_id = sqlobj["service_id"]
                apply_memory = sqlobj["apply_memory"]
                total_memory = sqlobj["total_memory"]
                disk_storage = total_memory - int(apply_memory)
                if disk_storage < 0:
                    disk_storage = 0
                real_memory = running_data.get(service_id)
                if real_memory is not None and real_memory != "":
                    totalMemory = totalMemory + int(apply_memory) + disk_storage
                else:
                    totalMemory = totalMemory + disk_storage
        return totalMemory
