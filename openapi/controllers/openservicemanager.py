# -*- coding: utf8 -*-
import datetime
import json

from www.apiclient.regionapi import RegionInvokeApi

from www.models import TenantServiceInfo, TenantServiceInfoDelete, \
    TenantServiceRelation, TenantServiceAuth, TenantServiceEnvVar, \
    TenantRegionInfo, TenantServicesPort, TenantServiceMountRelation, \
    TenantServiceEnv, ServiceDomain, Tenants, Users, \
    TenantServiceVolume, ServiceInfo, AppServiceRelation, ServiceEvent, ServiceGroupRelation, ServiceAttachInfo, \
    ServiceCreateStep, ServiceProbe
from www.service_http import RegionServiceApi
from www.app_http import AppServiceApi
from www.region import RegionInfo
from django.conf import settings
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource
from www.services import enterprise_svc,tenant_svc

import logging

from www.utils.crypt import make_uuid

logger = logging.getLogger('default')

monitorhook = MonitorHook()
regionClient = RegionServiceApi()
region_api = RegionInvokeApi()
appClient = AppServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()

class OpenTenantServiceManager(object):

    def __init__(self):
        self.feerule = settings.REGION_RULE
        self.MODULES = settings.MODULES

    def prepare_mapping_port(self, service, container_port):
        port_list = TenantServicesPort.objects.filter(tenant_id=service.tenant_id, mapping_port__gt=container_port).values_list(
            'mapping_port', flat=True).order_by('mapping_port')

        port_list = list(port_list)
        port_list.insert(0, container_port)
        max_port = reduce(lambda x, y: y if (y - x) == 1 else x, port_list)
        return max_port + 1

    def create_service(self, service_id, tenant_id, service_alias, service, creater, region, service_origin='assistant'):
        """创建console服务"""
        tenantServiceInfo = {}
        tenantServiceInfo["service_id"] = service_id
        tenantServiceInfo["tenant_id"] = tenant_id
        tenantServiceInfo["service_key"] = service.service_key
        tenantServiceInfo["service_alias"] = service_alias
        tenantServiceInfo["service_cname"] = service_alias
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
        tenantServiceInfo["update_version"] = service.update_version
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
        tenantServiceInfo["service_origin"] = service_origin
        tenantServiceInfo["port_type"] = "multi_outer"
        # tenantServiceInfo["port_type"] = "one_outer"
        newTenantService = TenantServiceInfo(**tenantServiceInfo)
        newTenantService.save()
        return newTenantService

    def create_region_service(self, newTenantService, domain, region, nick_name, do_deploy=True, dep_sids=None):
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
        data["code_from"] = newTenantService.code_from
        data["dep_sids"] = dep_sids
        data["port_type"] = newTenantService.port_type
        data["ports_info"] = []
        data["envs_info"] = []
        data["volumes_info"] = []

        if hasattr(newTenantService, "service_origin"):
            data["service_origin"] = newTenantService.service_origin

        ports_info = TenantServicesPort.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        if ports_info:
            data["ports_info"] = list(ports_info)

        envs_info = TenantServiceEnvVar.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if envs_info:
            data["envs_info"] = list(envs_info)

        volume_info = TenantServiceVolume.objects.filter(service_id=newTenantService.service_id).values(
            'service_id', 'category', 'host_path', 'volume_path')
        if volume_info:
            data["volumes_info"] = list(volume_info)

        # 创建操作
        event = ServiceEvent(event_id=make_uuid(), service_id=newTenantService.service_id,
                             tenant_id=newTenantService.tenant_id, type="create",
                             deploy_version=newTenantService.deploy_version if do_deploy else None,
                             user_name=nick_name, start_time=datetime.datetime.now())
        event.save()

        data["event_id"] = event.event_id
        logger.debug(newTenantService.tenant_id + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        tenant = Tenants.objects.get(tenant_id=newTenantService.tenant_id)
        data["enterprise_id"] = tenant.enterprise_id
        region_api.create_service(region, tenant.tenant_name, data)
        logger.debug(newTenantService.tenant_id + " end create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))

    def remove_service(self, tenant, service, username):
        try:
            # 检查当前服务的依赖服务
            dep_service_relation = TenantServiceRelation.objects.filter(service_id=service.service_id)
            if len(dep_service_relation) > 0:
                dep_service_ids = [x.dep_service_id for x in list(dep_service_relation)]
                logger.debug(dep_service_ids)
                # 删除依赖服务
                dep_service_list = TenantServiceInfo.objects.filter(service_id__in=list(dep_service_ids))
                for dep_service in list(dep_service_list):
                    try:
                        region_api.delete_service(dep_service.service_region, tenant.tenant_name, dep_service.service_alias,tenant.enterprise_id)
                        TenantServiceInfo.objects.filter(pk=dep_service.ID).delete()
                        TenantServiceEnv.objects.filter(service_id=dep_service.service_id).delete()
                        TenantServiceAuth.objects.filter(service_id=dep_service.service_id).delete()
                        ServiceDomain.objects.filter(service_id=dep_service.service_id).delete()
                        TenantServiceRelation.objects.filter(service_id=dep_service.service_id).delete()
                        TenantServiceEnvVar.objects.filter(service_id=dep_service.service_id).delete()
                        TenantServiceMountRelation.objects.filter(service_id=dep_service.service_id).delete()
                        TenantServicesPort.objects.filter(service_id=dep_service.service_id).delete()
                        TenantServiceVolume.objects.filter(service_id=dep_service.service_id).delete()
                        ServiceGroupRelation.objects.filter(service_id=dep_service.service_id).delete()
                        ServiceAttachInfo.objects.filter(service_id=dep_service.service_id).delete()
                        ServiceCreateStep.objects.filter(service_id=dep_service.service_id).delete()

                        events = ServiceEvent.objects.filter(service_id=dep_service.service_id)

                        ServiceEvent.objects.filter(service_id=dep_service.service_id).delete()
                        # 删除应用检测数据
                        ServiceProbe.objects.filter(service_id=service.service_id).delete()

                        monitorhook.serviceMonitor(username, dep_service, 'app_delete', True)
                    except Exception as e:
                        logger.exception("openapi.services", e)
            logger.debug("openapi.services", "dep service delete!")
            # 删除挂载关系
            TenantServiceMountRelation.objects.filter(service_id=service.service_id).delete()
            # 删除被挂载关系
            TenantServiceMountRelation.objects.filter(dep_service_id=service.service_id).delete()
            logger.debug("openapi.services", "dep mnt delete!")
            data = service.toJSON()
            tenant_service_info_delete = TenantServiceInfoDelete(**data)
            tenant_service_info_delete.save()
            logger.debug("openapi.services", "add delete record!")
            # 删除region服务
            try:
                region_api.delete_service(service.service_region, tenant.tenant_name, service.service_alias,tenant.enterprise_id)
            except Exception as e:
                logger.exception("openapi.services", e)
            logger.debug("openapi.services", "delete region service!")
            # 删除console服务
            TenantServiceInfo.objects.filter(service_id=service.service_id).delete()
            # env/auth/domain/relationship/envVar delete
            TenantServiceEnv.objects.filter(service_id=service.service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service.service_id).delete()
            ServiceDomain.objects.filter(service_id=service.service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service.service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service.service_id).delete()
            TenantServiceMountRelation.objects.filter(service_id=service.service_id).delete()
            TenantServicesPort.objects.filter(service_id=service.service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service.service_id).delete()
            ServiceGroupRelation.objects.filter(service_id=service.service_id).delete()
            ServiceAttachInfo.objects.filter(service_id=service.service_id).delete()
            ServiceCreateStep.objects.filter(service_id=service.service_id).delete()

            events = ServiceEvent.objects.filter(service_id=service.service_id)

            ServiceEvent.objects.filter(service_id=service.service_id).delete()

            monitorhook.serviceMonitor(username, service, 'app_delete', True)
            logger.debug("openapi.services", "delete service.result:success")
            return 200, True, u"删除成功"
        except Exception as e:
            logger.exception("openapi.services", e)
            logger.debug("openapi.services", "delete service.result:failure")
            return 412, False, u"删除失败"

    def domain_service(self, action, service, domain_name, tenant_name, username):
        try:
            if action == "start":
                domainNum = ServiceDomain.objects.filter(domain_name=domain_name).count()
                if domainNum > 0:
                    return 410, False, "域名已经存在"

                num = ServiceDomain.objects.filter(service_id=service.service_id).count()
                old_domain_name = "goodrain"
                if num == 0:
                    domain = {}
                    domain["service_id"] = service.service_id
                    domain["service_name"] = service.service_alias
                    domain["domain_name"] = domain_name
                    domain["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    domain["container_port"] = 0
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
                data["container_port"] = 0
                regionClient.addUserDomain(service.service_region, json.dumps(data))
                monitorhook.serviceMonitor(username, service, 'domain_add', True)
            elif action == "close":
                servicerDomain = ServiceDomain.objects.get(service_id=service.service_id)
                data = {}
                data["service_id"] = servicerDomain.service_id
                data["domain"] = servicerDomain.domain_name
                data["pool_name"] = tenant_name + "@" + service.service_alias + ".Pool"
                data["container_port"] = 0
                regionClient.unbindDomain(service.service_region, tenant_name, service.service_alias,json.dumps(data))
                ServiceDomain.objects.filter(service_id=service.service_id).delete()
                monitorhook.serviceMonitor(username, service, 'domain_delete', True)
            return 200, True, "success"
        except Exception as e:
            logger.exception("openapi.services", e)
            monitorhook.serviceMonitor(username, service, 'domain_manage', False)
            return 411, False, "操作失败"

    def query_domain(self, service):
        domain_list = ServiceDomain.objects.filter(service_id=service.service_id)
        if len(domain_list) > 0:
            return [x.domain_name for x in domain_list]
        else:
            return []

    def stop_service(self, service, username, tenant_id=None):
        try:
            event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                                 tenant_id=tenant_id, type="stop",
                                 deploy_version=service.deploy_version,
                                 user_name=username, start_time=datetime.datetime.now())
            event.save()

            body = {}
            body["operator"] = str(username)
            body["event_id"] = event.event_id
            tenant = Tenants.objects.get(tenant_id=service.tenant_id)
            body["enterprise_id"] = tenant.enterprise_id
            region_api.stop_service(service.service_region,
                                    tenant.tenant_name,
                                    service.service_alias,
                                    body)

            monitorhook.serviceMonitor(username, service, 'app_stop', True)
            return 200, True, "success"
        except Exception as e:
            logger.exception("openapi.services", e)
            monitorhook.serviceMonitor(username, service, 'app_stop', False)
            return 409, False, "停止服务失败"

    def start_service(self, tenant, service, username, limit=True):
        try:
            # calculate resource
            diff_memory = service.min_node * service.min_memory
            if limit:
                rt_type, flag = self.predict_next_memory(tenant, service, diff_memory, False)
                if not flag:
                    if rt_type == "memory":
                        return 410, False, "内存不足"
                    else:
                        return 411, False, "余额不足"

            event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                                 tenant_id=tenant.tenant_id, type="restart",
                                 deploy_version=service.deploy_version,
                                 user_name=username, start_time=datetime.datetime.now())
            event.save()

            body = {}
            body["deploy_version"] = service.deploy_version
            body["operator"] = str(username)
            body["event_id"] = event.event_id
            body["enterprise_id"] = tenant.enterprise_id
            region_api.start_service(service.service_region, tenant.tenant_name, service.service_alias,
                                     body)
            monitorhook.serviceMonitor(username, service, 'app_start', True)
            return 200, True, "success"
        except Exception as e:
            logger.exception("openapi.services", e)
            monitorhook.serviceMonitor(username, service, 'app_start', False)
            return 412, False, "启动失败"

    def status_service(self, service):
        result = {}
        try:
            if service.deploy_version is None or service.deploy_version == "":
                result["totalMemory"] = 0
                result["status"] = "undeploy"
                return 200, True, result
            else:
                tenant = Tenants.objects.get(tenant_id=service.tenant_id)
                body = region_api.check_service_status(service.service_region, tenant.tenant_name, service.service_alias, tenant.enterprise_id)
                bean = body["bean"]
                status = bean["cur_status"]
                if status == "running":
                    result["totalMemory"] = service.min_node * service.min_memory
                else:
                    result["totalMemory"] = 0
                status_cn = bean["status_cn"]
                from www.utils.status_translate import get_status_info_map
                status_info_map = get_status_info_map(status)
                result.update(status_info_map)
                if status_cn:
                    result["status_cn"] = status_cn
                result["status"] = status
            return 200, True, result
        except Exception as e:
            logger.exception("openapi.services", e)
            # logger.debug(service.service_region + "-" + service.service_id + " check_service_status is error")
            result["totalMemory"] = 0
            result['status'] = "failure"
            result["status_cn"] = "未知"
            return 409, False, result

    def predict_next_memory(self, tenant, cur_service, newAddMemory, ischeckStatus):
        result = True
        rt_type = "memory"
        if self.MODULES["Memory_Limit"]:
            result = False
            if ischeckStatus:
                newAddMemory = newAddMemory + self.curServiceMemory(cur_service)
            if tenant.pay_type == "free":
                tm = self.calculate_real_used_resource(tenant) + newAddMemory
                logger.debug(tenant.tenant_id + " used memory " + str(tm))
                # if tm <= tenant.limit_memory:
                if tm <= tenantUsedResource.get_limit_memory(tenant, cur_service.service_region):
                    result = True
            elif tenant.pay_type == "payed":
                tm = self.calculate_real_used_resource(tenant) + newAddMemory
                guarantee_memory = self.calculate_real_used_resource(tenant)
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
                mapping_port = self.prepare_mapping_port(service, container_port)
                port.mapping_port = mapping_port
                self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"连接地址", env_prefix + "_HOST", "127.0.0.1", False, scope="outer")
                self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"端口", env_prefix + "_PORT", mapping_port, False, scope="outer")
            if is_init_account:
                password = service.service_id[:8]
                TenantServiceAuth.objects.create(service_id=service.service_id, user="admin", password=password)
                self.saveServiceEnvVar(service.tenant_id, service.service_id, -1, u"用户名", env_prefix + "_USER", "admin", False, scope="both")
                self.saveServiceEnvVar(service.tenant_id, service.service_id, -1, u"密码", env_prefix + "_PASS", password, False, scope="both")
            port.save()
        except Exception as e:
            logger.exception("openapi.services", e)

    def saveServiceEnvVar(self, tenant_id, service_id, container_port, name, attr_name, attr_value, isChange, scope="outer"):
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

    def curServiceMemory(self, cur_service):
        memory = 0
        try:
            tenant = Tenants.objects.get(tenant_id=cur_service.tenant_id)
            body = region_api.check_service_status(cur_service.service_region, tenant.tenant_name, cur_service.service_alias,tenant.enterprise_id)
            status = body[cur_service.service_id]
            if status != "running":
                memory = cur_service.min_node * cur_service.min_memory
        except Exception as e:
            logger.exception("openapi.services", e)
        return memory

    def calculate_real_used_resource(self, tenant):
        totalMemory = 0
        tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True, is_init=True)
        running_data = {}
        for tenant_region in tenant_region_list:
            logger.debug(tenant_region.region_name)
            if tenant_region.region_name in RegionInfo.valid_regions():
                res = region_api.get_tenant_resources(tenant_region.region_name,tenant.tenant_name,tenant.enterprise_id)
                bean = res["bean"]
                memory = int(bean["memory"])
                totalMemory += memory
        return totalMemory

    def create_tenant(self, tenant_name, region, user_id, nick_name,enterprise_id):
        """创建租户"""
        regions = [region] if region else []
        tenant = enterprise_svc.create_and_init_tenant(user_id, tenant_name, regions)
        return tenant

    def save_mnt_volume(self, service, host_path, volume_path):
        try:
            category = service.category
            region = service.service_region
            tenant_id = service.tenant_id
            service_id = service.service_id
            volume = TenantServiceVolume(service_id=service_id,
                                         category=category)
            volume.host_path = host_path
            volume.volume_path = volume_path
            volume.save()
            return volume.ID
        except Exception as e:
            logger.exception("openapi.services", e)

    def add_volume_list(self, service, volume_path):
        try:
            category = service.category
            region = service.service_region
            tenant_id = service.tenant_id
            service_id = service.service_id
            volume = TenantServiceVolume(service_id=service_id,
                                         category=category)
            # 确定host_path
            if region == "ali-sh":
                host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
            else:
                host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
            volume.host_path = host_path
            volume.volume_path = volume_path
            volume.save()
            return host_path, volume.ID
        except Exception as e:
            logger.exception("openapi.services", e)

    def downloadImage(self, base_info):
        try:
            download_task = {}
            if base_info.is_slug():
                download_task = {"action": "download_and_deploy", "app_key": base_info.service_key, "app_version": base_info.version, "namespace": base_info.namespace, "dep_sids": json.dumps([])}
                for region in RegionInfo.valid_regions():
                    logger.info(region)
                    # TODO v2 api修改
                    regionClient.send_task(region, 'app_slug', json.dumps(download_task))
            else:
                download_task = {"action": "download_and_deploy", "image": base_info.image, "namespace": base_info.namespace, "dep_sids": json.dumps([])}
                for region in RegionInfo.valid_regions():
                    # TODO v2 api修改
                    regionClient.send_task(region, 'app_image', json.dumps(download_task))
        except Exception as e:
            logger.exception(e)

    def restart_service(self, tenant, service, username, limit=True):
        diff_memory = service.min_node * service.min_memory
        if limit:
            rt_type, flag = self.predict_next_memory(tenant, service, diff_memory, False)
            if not flag:
                if rt_type == "memory":
                    return 410, False, "内存不足"
                else:
                    return 411, False, "余额不足"

        # stop service
        code, is_success, msg = self.stop_service(service, username)
        if code == 200:
            code, is_success, msg = self.start_service(tenant, service, username, limit)
        return code, is_success, msg

    def update_service_memory(self, tenant, service, username, memory, limit=True):
        cpu = baseService.calculate_service_cpu(service.service_region, memory)
        old_cpu = service.min_cpu
        old_memory = service.min_memory
        if int(memory) != old_memory or cpu != old_cpu:
            left = memory % 128
            if memory > 0 and memory <= 65536 and left == 0:
                # calculate resource
                diff_memory = memory - int(old_memory)
                if limit:
                    rt_type, flag = self.predict_next_memory(tenant, service, diff_memory, True)
                    if not flag:
                        if rt_type == "memory":
                            return 410, False, "内存不足"
                        else:
                            return 411, False, "余额不足"

                event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                                     tenant_id=tenant.tenant_id, type="update",
                                     deploy_version=service.deploy_version,
                                     user_name=username, start_time=datetime.datetime.now())
                event.save()

                body = {
                    "container_memory": memory,
                    "deploy_version": service.deploy_version,
                    "container_cpu": cpu,
                    "operator": username,
                    "event_id":event.event_id,
                    "enterprise_id":tenant.enterprise_id
                }
                region_api.vertical_upgrade(service.service_region,
                                            tenant.tenant_name,
                                            service.service_alias,
                                            body)
                # 更新console记录
                service.min_cpu = cpu
                service.min_memory = memory
                service.save()
                # 添加记录
                monitorhook.serviceMonitor(username, service, 'app_vertical', True)
        return 200, True, "success"

    def update_service_node(self, tenant, service, username, node_num, limit=True):
        new_node_num = int(node_num)
        old_min_node = service.min_node
        if new_node_num >= 0 and new_node_num != old_min_node:
            # calculate resource
            diff_memory = (new_node_num - old_min_node) * service.min_memory
            if limit:
                rt_type, flag = self.predict_next_memory(tenant, service, diff_memory, True)
                if not flag:
                    if rt_type == "memory":
                        return 410, False, "内存不足"
                    else:
                        return 411, False, "余额不足"
            event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                                 tenant_id=tenant.tenant_id, type="update",
                                 deploy_version=service.deploy_version,
                                 user_name=username, start_time=datetime.datetime.now())
            event.save()
            body = {
                "node_num": new_node_num,
                "deploy_version": service.deploy_version,
                "operator": username,
                "event_id":event.event_id,
                "enterprise_id":tenant.enterprise_id
            }
            region_api.horizontal_upgrade(service.service_region, tenant.tenant_name,
                                          service.service_alias, body)
            service.min_node = new_node_num
            service.save()
            monitorhook.serviceMonitor(username, service, 'app_horizontal', True)
        return 200, True, "success"

    def update_service_version(self, service):
        service_key = service.service_key
        version = service.version
        base_service = ServiceInfo.objects.get(service_key=service_key, version=version)
        if base_service.update_version != service.update_version:
            tenant = Tenants.objects.get(tenant_id=service.tenant_id)
            region_api.update_service(service.service_region,
                                      tenant.tenant_name,
                                      service.service_alias,
                                      {"image_name": base_service.image,"enterprise_id":tenant.enterprise_id})
            service.image = base_service.image
            service.update_version = base_service.update_version
            service.save()
        return 200, True, "success"

    def download_service(self, service_key, version):
        # 从服务模版中查询依赖信息
        num = ServiceInfo.objects.filter(service_key=service_key, version=version).count()
        if num == 0:
            # 下载模版
            dep_code = self.download_remote_service(service_key, version)
            if dep_code == 500 or dep_code == 501:
                return 500, False, None, "下载{0}:{1}失败".format(service_key, version)
        # 下载依赖服务
        relation_list = AppServiceRelation.objects.filter(service_key=service_key, app_version=version)
        result_list = list(relation_list)
        dep_map = {}
        for relation in result_list:
            dep_key = relation.dep_service_key
            dep_version = relation.dep_app_version
            dep_map[dep_key] = dep_version
            num = ServiceInfo.objects.filter(service_key=dep_key, version=dep_version).count()
            if num == 0:
                status, success, tmp_map, msg = self.download_service(dep_key, dep_version)
                # 检查返回的数据
                if tmp_map is not None:
                    dep_map = dict(dep_map, **tmp_map)
                if status == 500:
                    return 500, False, None, "下载{0}:{1}失败".format(dep_key, dep_version)

        return 200, True, dep_map, "success"

    def create_service_dependency(self, tenant_id, service_id, dep_service_id, region):
        dependS = TenantServiceInfo.objects.get(service_id=dep_service_id)
        service = TenantServiceInfo.objects.get(service_id=service_id)
        tenant = Tenants.objects.get(tenant_id=tenant_id)
        task = {}
        task["dep_service_id"] = dep_service_id
        task["tenant_id"] = tenant_id
        task["dep_service_type"] = dependS.service_type
        task["enterprise_id"] = tenant.enterprise_id

        region_api.add_service_dependency(region, tenant.tenant_name, service.service_alias, task)
        tsr = TenantServiceRelation()
        tsr.tenant_id = tenant_id
        tsr.service_id = service_id
        tsr.dep_service_id = dep_service_id
        tsr.dep_service_type = dependS.service_type
        tsr.dep_order = 0
        tsr.save()

    def init_region_tenant(self, region, tenant_name, tenant_id, nick_name):
        user = Users(nick_name=nick_name)
        for num in range(0, 3):
            result = tenant_svc.init_for_region(region,
                                                         tenant_name,
                                                         tenant_id,
                                                         user)
            if result:
                logger.debug("openapi.cloudservice", "init tenant region success!")
                return result
            else:
                logger.error("openapi.cloudservice", "init tenant region failed! try again!num:{0}".format(num))

        return False

