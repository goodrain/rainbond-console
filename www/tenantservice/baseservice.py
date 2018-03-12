# -*- coding: utf8 -*-
import datetime
import json
import time
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.forms import model_to_dict

from share.manager.region_provier import RegionProviderManager
from www.apiclient.regionapi import RegionInvokeApi
from www.db import BaseConnection
from www.models import Users, TenantServiceInfo, PermRelTenant, Tenants, \
    TenantServiceRelation, TenantServiceAuth, TenantServiceEnvVar, \
    TenantRegionInfo, TenantServicesPort, TenantServiceMountRelation, \
    TenantServiceVolume, ServiceInfo, AppServiceRelation, AppServiceEnv, \
    AppServicePort, ServiceExtendMethod, AppServiceVolume, ServiceAttachInfo, ServiceEvent, AppServiceGroup, \
    PublishedGroupServiceRelation, ServiceExec, TenantServicePluginRelation, PluginBuildVersion, TenantRegionResource

from www.models.main import TenantRegionPayModel, TenantServiceEnv, ServiceProbe
from django.conf import settings
from goodrain_web.custom_config import custom_config
from www.monitorservice.monitorhook import MonitorHook
from www.gitlab_http import GitlabApi
from www.github_http import GitHubApi
from www.utils.giturlparse import parse as git_url_parse
from www.utils.sn import instance
from www.app_http import AppServiceApi

from www.utils.crypt import make_uuid
from www.region import RegionInfo
import logging

logger = logging.getLogger('default')

monitorhook = MonitorHook()
gitClient = GitlabApi()
gitHubClient = GitHubApi()
appClient = AppServiceApi()
rpmManager = RegionProviderManager()
region_api = RegionInvokeApi()


class BaseTenantService(object):
    def get_service_list(self, tenant_pk, user, tenant_id, region):
        user_pk = user.pk
        services = []
        if user.is_sys_admin:
            services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region)
        else:
            try:
                my_tenant_identity = PermRelTenant.objects.get(tenant_id=tenant_pk, user_id=user_pk).identity
                if my_tenant_identity in ('owner', 'admin', 'developer', 'viewer', 'gray'):
                    services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region).order_by(
                        'service_alias')
                else:
                    dsn = BaseConnection()
                    add_sql = ''
                    query_sql = '''
                        select s.* from tenant_service s, service_perms sp where s.tenant_id = "{tenant_id}"
                        and sp.user_id = {user_id} and sp.service_id = s.ID and s.service_region = "{region}" {add_sql} order by s.service_alias
                        '''.format(tenant_id=tenant_id, user_id=user_pk, region=region, add_sql=add_sql)
                    services = dsn.query(query_sql)
            except PermRelTenant.DoesNotExist:
                if tenant_pk == 5073:
                    services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region).order_by(
                        'service_alias')

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

    def getInnerServicePort(self, tenant_id, service_key):
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

    def prepare_mapping_port(self, service, container_port):
        port_list = TenantServicesPort.objects.filter(tenant_id=service.tenant_id,
                                                      mapping_port__gt=container_port).values_list(
            'mapping_port', flat=True).order_by('mapping_port')

        port_list = list(port_list)
        port_list.insert(0, container_port)
        max_port = reduce(lambda x, y: y if (y - x) == 1 else x, port_list)
        return max_port + 1

    def calculate_service_cpu(self, region, min_memory):
        min_cpu = int(min_memory) / 128 * 20
        if region == "ali-hz":
            min_cpu = min_cpu * 2
        return min_cpu

    def create_service(self, service_id, tenant_id, service_alias, service_cname, service, creater, region,
                       tenant_service_group_id=0, service_origin='assistant'):
        tenantServiceInfo = {}
        tenantServiceInfo["service_id"] = service_id
        tenantServiceInfo["tenant_id"] = tenant_id
        tenantServiceInfo["service_key"] = service.service_key
        tenantServiceInfo["service_alias"] = service_alias
        tenantServiceInfo["service_cname"] = service_cname
        tenantServiceInfo["service_region"] = region
        tenantServiceInfo["desc"] = service.desc
        tenantServiceInfo["category"] = service.category
        tenantServiceInfo["image"] = service.image
        tenantServiceInfo["cmd"] = service.cmd
        tenantServiceInfo["setting"] = ""
        tenantServiceInfo["extend_method"] = service.extend_method
        tenantServiceInfo["env"] = service.env
        tenantServiceInfo["min_node"] = service.min_node
        tenantServiceInfo["min_cpu"] = service.min_cpu
        tenantServiceInfo["min_memory"] = service.min_memory
        tenantServiceInfo["inner_port"] = service.inner_port
        tenantServiceInfo["version"] = service.version
        tenantServiceInfo["namespace"] = service.namespace
        tenantServiceInfo["update_version"] = service.update_version
        tenantServiceInfo["port_type"] = "multi_outer"
        volume_path = ""
        host_path = ""
        if bool(service.volume_mount_path):
            volume_path = service.volume_mount_path
            logger.debug("region:{0} and service_type:{1}".format(region, service.service_type))
            if region == "ali-sh":
                host_path = "/grdata/tenant/" + tenant_id + "/service/" + service_id
            else:
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
        tenantServiceInfo["tenant_service_group_id"] = tenant_service_group_id or 0
        tenantServiceInfo["service_origin"] = service_origin
        newTenantService = TenantServiceInfo(**tenantServiceInfo)
        newTenantService.save()
        return newTenantService

    def create_region_service(self, newTenantService, domain, region, nick_name, do_deploy=True, dep_sids=None):
        data = {}
        data["tenant_id"] = newTenantService.tenant_id
        data["service_id"] = newTenantService.service_id
        data["service_key"] = newTenantService.service_key
        data["comment"] = newTenantService.desc
        data["image_name"] = newTenantService.image
        data["container_cpu"] = newTenantService.min_cpu
        data["container_memory"] = newTenantService.min_memory
        data["volume_path"] = "vol" + newTenantService.service_id[0:10]
        # data["volume_mount_path"] = newTenantService.volume_mount_path
        # data["host_path"] = newTenantService.host_path
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
        data["service_label"] = "StatefulServiceType " if newTenantService.extend_method == "state" else "StatelessServiceType"

        depend_ids = [{
            "dep_order": dep.dep_order,
            "dep_service_type": dep.dep_service_type,
            "depend_service_id": dep.dep_service_id,
            "service_id": dep.service_id,
            "tenant_id": dep.tenant_id
        } for dep in TenantServiceRelation.objects.filter(service_id=newTenantService.service_id)]
        data["depend_ids"] = depend_ids

        ports_info = TenantServicesPort.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')

        for port_info in ports_info:
            port_info["is_inner_service"] = False
            port_info["is_outer_service"] = False

        if ports_info:
            data["ports_info"] = list(ports_info)

        envs_info = TenantServiceEnvVar.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if envs_info:
            data["envs_info"] = list(envs_info)

        # 获取数据持久化数据
        volume_info = TenantServiceVolume.objects.filter(service_id=newTenantService.service_id).values(
            'service_id', 'category', 'volume_name', 'volume_path', 'volume_type')
        if volume_info:
            data["volumes_info"] = list(volume_info)

        logger.debug(
            newTenantService.tenant_id + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))

        try:
            tenant = Tenants.objects.get(tenant_id=newTenantService.tenant_id)
            logger.debug("----- create service {0}".format(json.dumps(data)))
            data["enterprise_id"] = tenant.enterprise_id
            region_api.create_service(region, tenant.tenant_name, data)
            temp_port_info = TenantServicesPort.objects.filter(service_id=newTenantService.service_id)
            self.handle_service_port(tenant, newTenantService, temp_port_info)
        except Exception as e:
            logging.exception(e)
            raise e

    def handle_service_port(self, tenant, service, ports_info):
        """处理服务端口"""
        for port in ports_info:
            # 如果对外访问为打开,则调用api 打开数据
            if port.is_outer_service:
                if port.protocol != "http":
                    stream_outer_num = TenantServicesPort.objects.filter(service_id=port.service_id,
                                                                         is_outer_service=True).exclude(
                        container_port=port.container_port, protocol="http").count()
                    if stream_outer_num > 0:
                        logger.error("stream协议族外部访问只能开启一个")
                        continue
                try:
                    body = region_api.manage_outer_port(service.service_region, tenant.tenant_name,
                                                        service.service_alias,
                                                        port.container_port,
                                                        {"operation": "open",
                                                         "enterprise_id": tenant.enterprise_id})
                    logger.debug("open outer port body {}".format(body))
                    mapping_port = body["bean"]["port"]
                    port.mapping_port = port.container_port
                    port.lb_mapping_port = mapping_port
                    port.save()
                except Exception as e:
                    logger.exception(e)
                    port.is_outer_service = False
                    port.save()
            # 打开对内服务
            if port.is_inner_service:
                mapping_port = port.container_port
                try:
                    port.save(update_fields=['mapping_port'])

                    TenantServiceEnvVar.objects.filter(service_id=port.service_id,
                                                       container_port=port.container_port).delete()
                    self.saveServiceEnvVar(port.tenant_id, port.service_id, port.container_port,
                                           u"连接地址", port.port_alias + "_HOST", "127.0.0.1", False, scope="outer")
                    self.saveServiceEnvVar(port.tenant_id, port.service_id, port.container_port,
                                           u"端口", port.port_alias + "_PORT", mapping_port, False, scope="outer")
                    port_envs = TenantServiceEnvVar.objects.filter(service_id=port.service_id,
                                                                   container_port=port.container_port)

                    for env in port_envs:
                        region_api.delete_service_env(service.service_region,
                                                      tenant.tenant_name,
                                                      service.service_alias,
                                                      {"env_name": env.attr_name,
                                                       "enterprise_id": tenant.enterprise_id})
                        add_attr = {"container_port": env.container_port, "env_name": env.attr_name,
                                    "env_value": env.attr_value, "is_change": env.is_change, "name": env.name,
                                    "scope": env.scope, "enterprise_id": tenant.enterprise_id}
                        region_api.add_service_env(service.service_region,
                                                   tenant.tenant_name,
                                                   service.service_alias,
                                                   add_attr)
                    region_api.manage_inner_port(service.service_region, tenant.tenant_name, service.service_alias,
                                                 port.container_port,
                                                 {"operation": "open", "enterprise_id": tenant.enterprise_id})
                    port.save()
                except Exception as e:
                    logger.exception(e)
                    port.is_inner_service = False
                    port.save()

    def create_service_dependency(self, tenant, service, dep_service_id, region):
        logger.debug("-------- {}".format(dep_service_id))
        dependS = TenantServiceInfo.objects.get(service_id=dep_service_id)
        task = {}
        task["dep_service_id"] = dep_service_id
        task["tenant_id"] = tenant.tenant_id
        task["dep_service_type"] = dependS.service_type
        task["enterprise_id"] = tenant.enterprise_id
        region_api.add_service_dependency(region, tenant.tenant_name, service.service_alias, task)
        tsr = TenantServiceRelation()
        tsr.tenant_id = tenant.tenant_id
        tsr.service_id = service.service_id
        tsr.dep_service_id = dep_service_id
        tsr.dep_service_type = dependS.service_type
        tsr.dep_order = 0
        tsr.save()

    def cancel_service_dependency(self, tenant, service, dep_service_id, region):
        task = {}
        task["dep_service_id"] = dep_service_id
        task["tenant_id"] = tenant.tenant_id
        task["dep_service_type"] = "v"
        task["enterprise_id"] = tenant.enterprise_id

        region_api.delete_service_dependency(region, tenant.tenant_name, service.service_alias, task)
        TenantServiceRelation.objects.get(service_id=service.service_id, dep_service_id=dep_service_id).delete()

    def create_service_env(self, tenant, service_id, region):
        tenantServiceEnvList = TenantServiceEnvVar.objects.filter(service_id=service_id)
        data = {}
        for tenantServiceEnv in tenantServiceEnvList:
            service = TenantServiceInfo.objects.get(service_id=service_id)
            attr = {"tenant_id": tenant.tenant_id, "name": tenantServiceEnv.attr_name,
                    "env_name": tenantServiceEnv.attr_name, "env_value": tenantServiceEnv.attr_value,
                    "is_change": False, "scope": "outer", "container_port": service.inner_port,
                    "enterprise_id": tenant.enterprise_id}
            region_api.add_service_env(region, tenant.tenant_name, service.service_alias, attr)

    def cancel_service_env(self, tenant_id, service_id, region):
        task = {}
        task["tenant_id"] = tenant_id
        task["attr"] = {}

    def saveServiceEnvVar(self, tenant_id, service_id, container_port, name, attr_name, attr_value, isChange,
                          scope="outer"):
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

    def addServicePort(self, service, is_init_account, container_port=0, protocol='', port_alias='',
                       is_inner_service=False, is_outer_service=False):
        port = TenantServicesPort(tenant_id=service.tenant_id, service_id=service.service_id,
                                  container_port=container_port,
                                  protocol=protocol, port_alias=port_alias, is_inner_service=is_inner_service,
                                  is_outer_service=is_outer_service)
        try:
            env_prefix = port_alias.upper() if bool(port_alias) else service.service_key.upper()
            if is_inner_service:
                # 取消mapping端口
                mapping_port = container_port
                port.mapping_port = mapping_port
                if service.language == "docker-compose":
                    self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"连接地址",
                                           env_prefix + "_PORT_" + str(container_port) + "_TCP_ADDR", "127.0.0.1",
                                           False, scope="outer")
                    self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"端口",
                                           env_prefix + "_PORT_" + str(container_port) + "_TCP_PORT", mapping_port,
                                           False, scope="outer")
                else:
                    self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"连接地址",
                                           env_prefix + "_HOST", "127.0.0.1", False, scope="outer")
                    self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"端口",
                                           env_prefix + "_PORT", mapping_port, False, scope="outer")
            if is_init_account:
                password = service.service_id[:8]
                TenantServiceAuth.objects.create(service_id=service.service_id, user="admin", password=password)
                self.saveServiceEnvVar(service.tenant_id, service.service_id, -1, u"用户名", env_prefix + "_USER", "admin",
                                       False, scope="both")
                self.saveServiceEnvVar(service.tenant_id, service.service_id, -1, u"密码", env_prefix + "_PASS", password,
                                       False, scope="both")
            port.save()
        except Exception, e:
            logger.exception(e)

    # 检查事件是否超时，应用起停操作30s超时，其他操作3m超时
    def checkEventTimeOut(self, event):
        start_time = event.start_time
        if event.type == "deploy" or event.type == "create":
            if (datetime.datetime.now() - start_time).seconds > 180:
                event.final_status = "timeout"
                event.save()
                return True
        else:
            if (datetime.datetime.now() - start_time).seconds > 30:
                event.final_status = "timeout"
                event.save()
                return True
        return False

    def check_volume_name_uniqueness(self, volume_name, service_id):
        volumes = TenantServiceVolume.objects.filter(service_id=service_id, volume_name=volume_name)
        return volumes.count() > 1

    def check_volume_path_uniqueness(self, volume_path, service_id):
        volumes = TenantServiceVolume.objects.filter(service_id=service_id, volume_path=volume_path)
        return volumes.count() > 1

    def get_volume_by_name(self, volume_name, service_id):
        try:
            return TenantServiceVolume.objects.get(volume_name=volume_name, service_id=service_id)
        except TenantServiceVolume.DoesNotExist:
            return None

    def get_volume_by_id(self, volume_id):
        try:
            return TenantServiceVolume.objects.get(ID=volume_id)
        except TenantServiceVolume.DoesNotExist:
            return None

    def get_volumes_by_type(self, volume_type, service_id):
        return TenantServiceVolume.objects.filter(volume_type=volume_type, service_id=service_id)

    def create_service_mnt(self, tenant, service, dep_service_alias, region):
        dependS = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=dep_service_alias)
        task = {}
        task["depend_service_id"] = dependS.service_id
        task["tenant_id"] = tenant.tenant_id
        task["mnt_name"] = "/mnt/" + dependS.service_alias
        task["mnt_dir"] = dependS.host_path
        task["enterprise_id"] = tenant.enterprise_id
        region_api.add_service_volume_dependency(region, tenant.tenant_name, service.service_alias, task)
        tsr = TenantServiceMountRelation()
        tsr.tenant_id = tenant.tenant_id
        tsr.service_id = service.service_id
        tsr.dep_service_id = dependS.service_id
        tsr.mnt_name = "/mnt/" + dependS.service_alias
        tsr.mnt_dir = dependS.host_path
        tsr.dep_order = 0
        tsr.save()

    def cancel_service_mnt(self, tenant, service, dep_service_alias, region):
        dependS = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=dep_service_alias)
        task = {}
        task["depend_service_id"] = dependS.service_id
        task["tenant_id"] = tenant.tenant_id
        task["mnt_name"] = "v"
        task["mnt_dir"] = "v"
        task["enterprise_id"] = tenant.enterprise_id
        region_api.delete_service_volume_dependency(region, tenant.tenant_name, service.service_alias, task)
        TenantServiceMountRelation.objects.get(service_id=service.service_id,
                                               dep_service_id=dependS.service_id).delete()

    def create_service_volume(self, service, volume_path):
        category = service.category
        region = service.service_region
        service_id = service.service_id
        host_path, volume_id = self.add_volume_list(service, volume_path)
        if volume_id is None:
            logger.error("add volume error!")
            return None
        # 发送到region进行处理
        tenant = Tenants.objects.get(tenant_id=service.tenant_id)
        json_data = {
            "service_id": service_id,
            "category": category,
            "host_path": host_path,
            "volume_path": volume_path,
            "enterprise_id": tenant.enterprise_id
        }

        res, body = region_api.add_service_volume(service.service_region,
                                                  tenant.tenant_name,
                                                  service.service_alias,
                                                  json_data)
        if res.status == 200:
            return volume_id
        else:
            TenantServiceVolume.objects.filter(pk=volume_id).delete()
            return None

    def cancel_service_volume(self, service, volume_id):
        # 发送到region进行删除
        region = service.service_region
        service_id = service.service_id
        try:
            volume = TenantServiceVolume.objects.get(pk=volume_id)
        except TenantServiceVolume.DoesNotExist:
            return True
        tenant = Tenants.objects.get(tenant_id=service.tenant_id)
        json_data = {
            "service_id": service_id,
            "category": volume.category,
            "host_path": volume.host_path,
            "volume_path": volume.volume_path,
            "enterprise_id": tenant.enterprise_id
        }
        res, body = region_api.delete_service_volume(region, tenant.tenant_name, service.service_alias,
                                                     json_data)
        if res.status == 200:
            TenantServiceVolume.objects.filter(pk=volume_id).delete()
            return True
        else:
            return False

    def check_app_vol_path(self, service, dep_vols):
        logger.debug('check vol path')
        existed = []
        for vol in dep_vols:
            path = vol['path']
            path = path if path.startswith('/') else '/' + path
            logger.debug('path {0}'.format(path))
            if TenantServiceVolume.objects.filter(
                    service_id=service.service_id, volume_path=path).count() > 0:
                existed.append(path)
        return existed

    def batch_add_dep_volume_v2(self, tenant, service, dep_vol_ids):
        existed = self.check_app_vol_path(service, dep_vol_ids)
        if existed:
            return False, None, '存储路径:{0}已存在'.format(existed)

        failed = []
        message = []
        for vol in dep_vol_ids:
            dep_vol_id = vol['id']
            source_path = vol['path']
            source_path = source_path if source_path.startswith('/') else '/' + source_path
            dep_volume = self.get_volume_by_id(int(dep_vol_id))
            data = {
                "depend_service_id": dep_volume.service_id,
                "volume_name": dep_volume.volume_name,
                "volume_path": source_path,
                "enterprise_id": tenant.enterprise_id
            }
            try:
                logger.debug('send add dep volume with region:{0},tenant:{1},service:{2},data:{3}'.format(
                    service.service_region, tenant.tenant_name, service.service_alias, json.dumps(data)
                ))
                res, body = region_api.add_service_dep_volumes(
                    service.service_region, tenant.tenant_name, service.service_alias, data
                )
                if res.status == 200:
                    tsr = TenantServiceMountRelation(
                        tenant_id=service.tenant_id,
                        service_id=service.service_id,
                        dep_service_id=dep_volume.service_id,
                        mnt_name=dep_volume.volume_name,
                        mnt_dir=source_path  # this dir is source app's volume path
                    )
                    tsr.save()
                else:
                    logger.debug('add dep volume error:{0}'.format(json.dumps(body)))
                    failed.append(dep_volume.volume_name)
                    message.append(json.dumps(body))
            except Exception as e:
                logger.error(e)
                failed.append(dep_volume.volume_name)
                message.append(e.message)
        if not failed:
            return True, None, None
        logger.debug('service {0} volume path existed {1}'.format(service.service_id, failed))
        return False, failed, message

    def delete_dep_volume_v2(self, tenant, service, dep_vol_id):
        dep_volume = self.get_volume_by_id(dep_vol_id)
        data = {
            "depend_service_id": dep_volume.service_id,
            "volume_name": dep_volume.volume_name,
            "enterprise_id": tenant.tenant_name
        }
        try:
            res, body = region_api.delete_service_dep_volumes(
                service.service_region, tenant.tenant_name, service.service_alias, data
            )
            if res.status == 200:
                TenantServiceMountRelation.objects.get(
                    service_id=service.service_id, dep_service_id=dep_volume.service_id
                ).delete()
                return True
            return False
        except region_api.CallApiError as e:
            if e.status == 404:
                logger.debug('service mnt relation not in region then delete rel directly in console')
                TenantServiceMountRelation.objects.get(
                    service_id=service.service_id, dep_service_id=dep_volume.service_id
                ).delete()
                return True
            return False

    def add_volume_v2(self, tenant, service, volume_name, volume_path, volume_type):
        volume = self.add_volume_with_type(service, volume_path, volume_type, volume_name)
        if not volume:
            logger.error("add volume error")
            return None, None
        data = {
            "category": service.category,
            "volume_name": volume_name,
            "volume_path": volume_path,
            "volume_type": volume_type,
            "enterprise_id": tenant.enterprise_id
        }
        try:
            res, body = region_api.add_service_volumes(
                service.service_region, tenant.tenant_name, service.service_alias, data
            )
            if res.status == 200:
                return volume, None
            volume.delete()
            return None, body
        except Exception as e:
            logger.debug('add volume failed,msg:{0}'.format(e.message))
            volume.delete()
            return None, e.message

    def delete_volume_v2(self, tenant, service, volume_id):
        try:
            volume = TenantServiceVolume.objects.get(ID=volume_id)
            if volume.volume_type == TenantServiceVolume.SHARE:
                if TenantServiceMountRelation.objects.filter(
                        dep_service_id=volume.service_id, mnt_name=volume.volume_name).count() > 0:
                    return False, '有依赖的应用'
            try:
                res, body = region_api.delete_service_volumes(
                    service.service_region, tenant.tenant_name, service.service_alias, volume.volume_name,
                    tenant.enterprise_id
                )
                if res.status == 200:
                    volume.delete()
                    return True, None
                return False, 'api delete failed'
            except region_api.CallApiError as e:
                if e.status == 404:
                    logger.debug(
                        'service {0} volume {1} not found in region'.format(service.service_alias, volume.volume_name)
                    )
                    volume.delete()
                    return True, None
                return False, e.message
        except TenantServiceVolume.DoesNotExist:
            return False, 'volume not exist'

    def add_volume_list(self, service, volume_path):
        try:
            category = service.category
            region = service.service_region
            tenant_id = service.tenant_id
            service_id = service.service_id
            volume = TenantServiceVolume(service_id=service_id, category=category)
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
            logger.exception(e)

    def add_volume_with_type(self, service, volume_path, volume_type, volume_name):
        try:
            category = service.category
            region = service.service_region
            tenant_id = service.tenant_id
            service_id = service.service_id
            if region == "ali-sh":
                host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
            else:
                host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
            volume = TenantServiceVolume(service_id=service_id, category=category)
            volume.host_path = host_path
            volume.volume_path = volume_path
            volume.volume_name = volume_name
            volume.volume_type = volume_type
            volume.save()
            return volume
        except Exception as e:
            logger.exception(e)
            return None

    # 下载服务组模板逻辑
    def download_group_info(self, group_key, group_version, action=None):
        num = AppServiceGroup.objects.filter(group_share_id=group_key, group_version=group_version).count()
        if num == 0:
            dep_code = 500
            for num in range(0, 3):
                dep_code, group_info = self.download_remote_group(group_key, group_version)
                if dep_code in (500, 501,):
                    logger.error("download group failed! try again! num:{0} ".format(num))
                    continue
                else:
                    break
            if dep_code in (500, 501,):
                return 500, None, "download group {0}:{1} failed!".format(group_key, group_version)
        else:
            group_list = AppServiceGroup.objects.filter(group_share_id=group_key, group_version=group_version)
            group_info = list(group_list)[0]
        return 200, group_info, "success"

    # 云市下载服务数据
    def download_remote_group(self, group_key, group_version):
        """获取远程服务信息"""
        all_data = {
            'group_key': group_key,
            'group_version': group_version,
            'cloud_assistant': instance.cloud_assistant,
        }

        data = json.dumps(all_data)
        logger.debug("post group json data={}".format(data))
        res, resp = appClient.getGroupData(body=data)
        if res.status == 200:
            json_data = json.loads(resp.data)
            group_data = json_data.get("group", None)
            if not group_data:
                logger.error("no group data!")
                return 500, None
            # 模板信息
            group_info = None
            try:
                group_info = AppServiceGroup.objects.get(group_share_id=group_key, group_version=group_version)
            except Exception:
                pass
            if not group_info:
                group_info = AppServiceGroup()
            group_info.tenant_id = group_data.get("publisher_tenant_id")
            group_info.group_share_alias = group_data.get("group_name")
            group_info.group_share_id = group_data.get("group_key")
            group_info.group_id = "0"
            group_info.service_ids = ""
            group_info.group_version = group_data.get("group_version")
            group_info.desc = group_data.get("info")
            group_info.save()

            PublishedGroupServiceRelation.objects.filter(group_pk=group_info.ID).delete()
            relation_list = json_data.get("relation_list", None)
            if relation_list:
                pgsrs = []
                for rl in relation_list:
                    service_key = rl.get("service_key")
                    version = rl.get("version")
                    pgsr = PublishedGroupServiceRelation(group_pk=group_info.ID, service_id="", service_key=service_key,
                                                         version=version)
                    pgsrs.append(pgsr)
                PublishedGroupServiceRelation.objects.bulk_create(pgsrs)
            return 200, group_info
        else:
            return 501, None

    # 下载服务模版逻辑
    def download_service_info(self, service_key, app_version, action=None):
        num = ServiceInfo.objects.filter(service_key=service_key, version=app_version).count()
        if num == 0 or action == "update":
            dep_code = 500
            for num in range(0, 3):
                dep_code, base_info = self.download_remote_service(service_key, app_version)
                if dep_code == 500 or dep_code == 501:
                    logger.error("download service failed! try again!num:{0}".format(num))
                    continue
                else:
                    break
            if dep_code == 500 or dep_code == 501:
                return 500, None, None, "download {0}:{1} failed!".format(service_key, app_version)
        else:
            info_list = ServiceInfo.objects.filter(service_key=service_key, version=app_version)
            base_info = list(info_list)[0]

        # 下载依赖服务
        relation_list = AppServiceRelation.objects.filter(service_key=service_key, app_version=app_version)
        result_list = list(relation_list)
        dep_map = {}
        for relation in result_list:
            dep_key = relation.dep_service_key
            dep_version = relation.dep_app_version
            dep_map[dep_key] = dep_version
            num = ServiceInfo.objects.filter(service_key=dep_key, version=dep_version).count()
            if num == 0:
                status, success, tmp_map, msg = self.download_service_info(dep_key, dep_version)
                # 检查返回的数据
                if tmp_map is not None:
                    dep_map = dict(dep_map, **tmp_map)
                if status == 500:
                    return 500, None, None, "download {0}:{1} failed!".format(dep_key, dep_version)
        return 200, base_info, dep_map, "success"

    # 下载服务模版数据
    def download_remote_service(self, service_key, version):
        """获取远程服务信息"""
        all_data = {
            'service_key': service_key,
            'app_version': version,
            'cloud_assistant': instance.cloud_assistant,
        }
        data = json.dumps(all_data)
        logger.debug('post service json data={}'.format(data))
        res, resp = appClient.getServiceData(body=data)
        if res.status == 200:
            json_data = json.loads(resp.data)
            service_data = json_data.get("service", None)
            if not service_data:
                logger.error("no service data!")
                return 500, None
            # 模版信息
            base_info = None
            try:
                base_info = ServiceInfo.objects.get(service_key=service_key, version=version)
            except Exception:
                pass
            if base_info is None:
                base_info = ServiceInfo()
            base_info.service_key = service_data.get("service_key")
            base_info.publisher = service_data.get("publisher")
            base_info.service_name = service_data.get("service_name")
            base_info.pic = service_data.get("pic")
            base_info.info = service_data.get("info")
            base_info.desc = service_data.get("desc")
            base_info.status = service_data.get("status")
            # 下载模版后在本地应用市场安装
            if base_info.service_key != "application":
                base_info.status = "published"
            base_info.category = service_data.get("category")
            base_info.is_service = service_data.get("is_service")
            base_info.is_web_service = service_data.get("is_web_service")
            base_info.version = service_data.get("version")
            base_info.update_version = service_data.get("update_version")
            base_info.image = service_data.get("image")
            base_info.slug = service_data.get("slug")
            base_info.extend_method = service_data.get("extend_method")
            base_info.cmd = service_data.get("cmd")
            base_info.setting = service_data.get("setting")
            base_info.env = service_data.get("env")
            base_info.dependecy = service_data.get("dependecy")
            base_info.min_node = service_data.get("min_node")
            base_info.min_cpu = service_data.get("min_cpu")
            base_info.min_memory = service_data.get("min_memory")
            base_info.inner_port = service_data.get("inner_port")
            base_info.volume_mount_path = service_data.get("volume_mount_path")
            base_info.service_type = service_data.get("service_type")
            base_info.is_init_accout = service_data.get("is_init_accout")
            base_info.namespace = service_data.get("namespace")
            base_info.save()
            logger.debug('---add app service---ok---')
            # 保存service_env
            pre_list = json_data.get('pre_list', None)
            suf_list = json_data.get('suf_list', None)
            env_list = json_data.get('env_list', None)
            port_list = json_data.get('port_list', None)
            extend_list = json_data.get('extend_list', None)
            volume_list = json_data.get('volume_list', None)
            # 新增环境参数
            env_data = []
            if env_list:
                for env in env_list:
                    app_env = AppServiceEnv(service_key=env.get("service_key"),
                                            app_version=env.get("app_version"),
                                            name=env.get("name"),
                                            attr_name=env.get("attr_name"),
                                            attr_value=env.get("attr_value"),
                                            scope=env.get("scope"),
                                            is_change=env.get("is_change"),
                                            container_port=env.get("container_port"))
                    env_data.append(app_env)
            AppServiceEnv.objects.filter(service_key=service_key, app_version=version).delete()
            if len(env_data) > 0:
                AppServiceEnv.objects.bulk_create(env_data)
            logger.debug('---add app service env---ok---')
            # 端口信息
            port_data = []
            if port_list:
                for port in port_list:
                    app_port = AppServicePort(service_key=port.get("service_key"),
                                              app_version=port.get("app_version"),
                                              container_port=port.get("container_port"),
                                              protocol=port.get("protocol"),
                                              port_alias=port.get("port_alias"),
                                              is_inner_service=port.get("is_inner_service"),
                                              is_outer_service=port.get("is_outer_service"))
                    port_data.append(app_port)
            AppServicePort.objects.filter(service_key=service_key, app_version=version).delete()
            if len(port_data) > 0:
                AppServicePort.objects.bulk_create(port_data)
            logger.debug('---add app service port---ok---')
            # 扩展信息
            extend_data = []
            if extend_list:
                for extend in extend_list:
                    app_port = ServiceExtendMethod(service_key=extend.get("service_key"),
                                                   app_version=extend.get("app_version"),
                                                   min_node=extend.get("min_node"),
                                                   max_node=extend.get("max_node"),
                                                   step_node=extend.get("step_node"),
                                                   min_memory=extend.get("min_memory"),
                                                   max_memory=extend.get("max_memory"),
                                                   step_memory=extend.get("step_memory"),
                                                   is_restart=extend.get("is_restart"))
                    extend_data.append(app_port)
            ServiceExtendMethod.objects.filter(service_key=service_key, app_version=version).delete()
            if len(extend_data) > 0:
                ServiceExtendMethod.objects.bulk_create(extend_data)
            logger.debug('---add app service extend---ok---')
            # 服务依赖关系
            # step1:现将该服务已经配置进行删除
            AppServiceRelation.objects.filter(service_key=service_key, app_version=version).delete()
            pre_relation_data = []
            if pre_list:
                for relation in pre_list:
                    app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                      app_version=relation.get("app_version"),
                                                      app_alias=relation.get("app_alias"),
                                                      dep_service_key=relation.get("dep_service_key"),
                                                      dep_app_version=relation.get("dep_app_version"),
                                                      dep_app_alias=relation.get("dep_app_alias"))

                    # step2:将原有的前置依赖数据删除
                    query_set = AppServiceRelation.objects.filter(service_key=relation.get("service_key"),
                                                                  app_version=relation.get("app_version"),
                                                                  dep_service_key=relation.get("dep_service_key"),
                                                                  dep_app_version=relation.get("dep_app_version"))
                    if not query_set:
                        pre_relation_data.append(app_relation)
            if len(pre_relation_data) > 0:
                AppServiceRelation.objects.bulk_create(pre_relation_data)
            logger.debug('---add app service pre_list relation---ok---')
            logger.debug('----------> pre_list {}'.format(pre_list))
            suf_relation_data = []
            if suf_list:
                for relation in suf_list:
                    app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                      app_version=relation.get("app_version"),
                                                      app_alias=relation.get("app_alias"),
                                                      dep_service_key=relation.get("dep_service_key"),
                                                      dep_app_version=relation.get("dep_app_version"),
                                                      dep_app_alias=relation.get("dep_app_alias"))

                    # step3:将原有的后置依赖数据删除
                    query_set = AppServiceRelation.objects.filter(service_key=relation.get("service_key"),
                                                                  app_version=relation.get("app_version"),
                                                                  dep_service_key=relation.get("dep_service_key"),
                                                                  dep_app_version=relation.get("dep_app_version"))
                    if not query_set:
                        suf_relation_data.append(app_relation)
            if len(suf_relation_data) > 0:
                AppServiceRelation.objects.bulk_create(suf_relation_data)
            logger.debug('---add app service suf_list relation---ok---')
            logger.debug('----------> suf_list {}'.format(suf_list))
            # 服务持久化记录
            volume_data = []
            if volume_list:
                for app_volume in volume_list:
                    volume = AppServiceVolume(service_key=app_volume.get("service_key"),
                                              app_version=app_volume.get("app_version"),
                                              category=app_volume.get("category"),
                                              volume_path=app_volume.get("volume_path"))

                    volume_data.append(volume)
            AppServiceVolume.objects.filter(service_key=service_key, app_version=version).delete()
            if len(volume_data) > 0:
                AppServiceVolume.objects.bulk_create(volume_data)
            logger.debug('---add app service volume---ok---')
            return 200, base_info
        else:
            return 501, None

    # 获取服务类型
    def get_service_kind(self, service):
        # 自定义镜像
        kind = "image"
        if service.category == "application":
            # 源码构建
            kind = "source"
        if service.category == "app_publish":
            # 镜像分享到云市
            kind = "market"
            if service.is_slug():
                # 源码分享到云市
                kind = "slug"
            # 自定义镜像
            if service.service_key == "0000":
                kind = "image"
        return kind

    def create_label_event(self, tenant, user, service, action):
        try:
            event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                                 tenant_id=tenant.tenant_id, type="{0}".format(action),
                                 deploy_version=service.deploy_version,
                                 old_deploy_version=service.deploy_version,
                                 user_name=user.nick_name, start_time=datetime.datetime.now())
            event.save()
            return event.event_id
        except Exception as e:
            raise e

    def add_service_default_probe(self, tenant, service):
        ports = TenantServicesPort.objects.filter(tenant_id=tenant.tenant_id, service_id=service.service_id)
        port_length = len(ports)
        if port_length >= 1:
            try:
                container_port = ports[0].container_port
                for p in ports:
                    if p.is_outer_service:
                        container_port = p.container_port
                service_probe = ServiceProbe(
                    service_id=service.service_id,
                    scheme="tcp",
                    path="",
                    port=container_port,
                    cmd="",
                    http_header="",
                    initial_delay_second=2,
                    period_second=3,
                    timeout_second=30,
                    failure_threshold=3,
                    success_threshold=1,
                    is_used=True,
                    probe_id=make_uuid(),
                    mode="readiness")
                json_data = model_to_dict(service_probe)
                is_used = 1 if json_data["is_used"] else 0
                json_data.update({"is_used": is_used})
                json_data["enterprise_id"] = tenant.enterprise_id
                res, body = region_api.add_service_probe(service.service_region, tenant.tenant_name,
                                                         service.service_alias,
                                                         json_data)
                service_probe.save()
            except Exception as e:
                logger.error("add service probe error !")
                logger.exception(e)


class ServicePluginResource(object):
    def get_service_plugin_resource(self, service_id):
        tprs = TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_status=True)
        memory = 0
        for tpr in tprs:
            try:
                pbv = PluginBuildVersion.objects.get(plugin_id=tpr.plugin_id, build_version=tpr.build_version)
                memory += pbv.min_memory
            except Exception as e:
                pass
        return memory

    def get_services_plugin_resource_map(self, service_ids):
        tprs = TenantServicePluginRelation.objects.filter(service_id__in=service_ids, plugin_status=True)
        service_plugin_map = {}
        for tpr in tprs:
            pbv = PluginBuildVersion.objects.filter(plugin_id=tpr.plugin_id, build_version=tpr.build_version).values(
                "min_memory")
            if pbv:
                p = pbv[0]
                if service_plugin_map.get(tpr.service_id, None):
                    service_plugin_map[tpr.service_id] += p["min_memory"]
                else:
                    service_plugin_map[tpr.service_id] = p["min_memory"]
        return service_plugin_map

class TenantUsedResource(object):
    def __init__(self):
        self.feerule = settings.REGION_RULE
        self.MODULES = settings.MODULES

    def calculate_real_used_resource(self, tenant, region=None):
        totalMemory = 0
        if region:
            tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id,
                                                                 is_active=True, is_init=True)
        else:
            tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, region_name=region,
                                                                 is_active=True,
                                                                 is_init=True)

        running_data = {}
        for tenant_region in tenant_region_list:
            logger.debug(tenant_region.region_name)
            if tenant_region.region_name in RegionInfo.valid_regions():
                res = region_api.get_tenant_resources(tenant_region.region_name, tenant.tenant_name,
                                                      tenant.enterprise_id)
                bean = res["bean"]
                memory = int(bean["memory"])
                totalMemory += memory
        return totalMemory

    def calculate_guarantee_resource(self, tenant):
        memory = 0
        if tenant.pay_type == "company":
            cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            dsn = BaseConnection()
            query_sql = "select region_name,sum(buy_memory) as buy_memory,sum(buy_disk) as buy_disk, sum(buy_net) as buy_net  from tenant_region_pay_model where tenant_id='" + \
                        tenant.tenant_id + "' and buy_end_time <='" + cur_time + "' group by region_name"
            sqlobjs = dsn.query(query_sql)
            if sqlobjs is not None and len(sqlobjs) > 0:
                for sqlobj in sqlobjs:
                    memory = memory + int(sqlobj["buy_memory"])
        return memory

    def predict_next_memory(self, tenant, cur_service, newAddMemory, ischeckStatus):
        result = True
        rt_type = "memory"
        if self.MODULES["Memory_Limit"]:
            result = False
            if ischeckStatus:
                newAddMemory = newAddMemory + self.curServiceMemory(tenant, cur_service)
            if tenant.pay_type == "free":
                tm = self.calculate_real_used_resource(tenant, cur_service.service_region) + newAddMemory
                logger.debug(tenant.tenant_id + " used memory " + str(tm))
                # if tm <= tenant.limit_memory:
                if tm <= self.get_limit_memory(tenant, cur_service.service_region):
                    result = True
            elif tenant.pay_type == "payed":
                tm = self.calculate_real_used_resource(tenant, cur_service.service_region) + newAddMemory
                guarantee_memory = self.calculate_guarantee_resource(tenant)
                logger.debug(
                    tenant.tenant_id + " used memory:" + str(tm) + " guarantee_memory:" + str(guarantee_memory))
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

    def curServiceMemory(self, tenant, cur_service):
        memory = 0
        try:
            body = region_api.check_service_status(cur_service.service_region, tenant.tenant_name,
                                                   cur_service.service_alias, tenant.enterprise_id)
            status = body["bean"]["cur_status"]
            if status != "running":
                memory = cur_service.min_node * cur_service.min_memory
        except Exception:
            pass
        return memory

    def predict_batch_services_memory(self, tenant, services, region):
        total_memory = 0
        for service in services:
            total_memory += service.min_memory * service.min_node
        if tenant.pay_type == "free":
            used_memory = self.calculate_real_used_resource(tenant, region)
            tm = used_memory + total_memory
            # if tm <= tenant.limit_memory:
            if tm <= self.get_limit_memory(tenant, region):
                result = True
            else:
                result = False
        else:
            result = True
        return result

    def get_limit_memory(self, tenant, region):
        res = TenantRegionResource.objects.filter(tenant_id=tenant.tenant_id, region_name=region)
        # 领了云市资源包
        if res:
            pkg_tag = True
            expire = False
            if datetime.datetime.now() < res[0].memory_expire_date:
                memory = res[0].memory_limit
            else:
                expire = True
                memory = 0
        # 没领资源包根据云帮租户状态限制可用内存上线
        else:
            pkg_tag = False
            expire = False
            if tenant.pay_type == 'free':
                expire = True
                memory = 0
            elif tenant.pay_type == 'payed':
                memory = 1024 * 1024
            else:
                memory = 9999 * 1024

        logger.debug('[{}:{}-{}] package:{}, expire:{}, memory:{}'.format(tenant.tenant_name, tenant.pay_type, region,
                                                                          pkg_tag, expire, memory))
        return memory

class TenantAccountService(object):
    def __init__(self):
        self.MODULES = settings.MODULES

    def isOwnedMoney(self, tenant, region_name):
        if self.MODULES["Owned_Fee"]:
            tenant_region = TenantRegionInfo.objects.get(tenant_id=tenant.tenant_id, region_name=region_name)
            if tenant.balance < 0 and tenant.pay_type == "payed":
                return True
        return False

    def isExpired(self, tenant, service):
        if service.expired_time is not None:
            if tenant.pay_type == "free" and service.expired_time < datetime.datetime.now():
                return True
        else:
            # 将原有免费用户的服务设置为7天后
            service.expired_time = datetime.datetime.now() + datetime.timedelta(days=7)
        return False

    def get_monthly_payment(self, tenant, region_name):
        # 0 未包月 1快到期 2 已到期 3离到期时间很长
        flag = 0
        tenant_region_pay_list = TenantRegionPayModel.objects.filter(tenant_id=tenant.tenant_id,
                                                                     region_name=region_name)
        if len(tenant_region_pay_list) == 0:
            return flag
        for pay_model in tenant_region_pay_list:
            if pay_model.buy_end_time > datetime.datetime.now():
                timedelta = (pay_model.buy_end_time - datetime.datetime.now()).days
                if timedelta < 3:
                    flag = 1
                else:
                    flag = 3
            else:
                flag = 2

        return flag


class TenantServiceExec(object):
    def __init__(self, region, tenant_id, service_id, run_exec):
        self.region = region
        self.tenant_id = tenant_id
        self.service_id = service_id
        self.run_exec = run_exec

        # def sendExec(self, method):
        #     api = RegionServiceApi()
        #     try:
        #         res, body = api.send_service_exec(self.region, self.tenant_id, self.service_id, self.run_exec, method)
        #     except api.CallApiError, e:
        #         logger.error("service {0} send exec error. {1}".format(self.service_id, str(e)))
        #         return False, None, None
        #     return True, res, body

        # def insertExec(self):
        #     res = {"status":500}
        #     if self.run_exec:
        #         try:
        #             execList = ServiceExec.objects.filter(service_id=self.service_id)
        #         except Exception, e:
        #             logger.error("filter sql error. {}".format(str(e)))
        #             return False, res, None
        #         if len(execList) == 0 :
        #             try:
        #                 ServiceExec.objects.create(tenant_id=self.tenant_id, service_id=self.service_id, run_exec=self.run_exec)
        #                 jud, res, body = self.sendExec("create")
        #             except Exception as e:
        #                 logger.error("create table service_exec error. {}".format(str(e)))
        #                 return False, res, None
        #         elif len(execList) == 1:
        #             try:
        #                 ServiceExec.objects.filter(tenant_id=self.tenant_id, service_id=self.service_id).update(run_exec=self.run_exec)
        #                 jud, res, body = self.sendExec("update")
        #             except Exception as e:
        #                 logger.error("update table service_exec error. {}".format(str(e)))
        #                 return False, res, None
        #         else:
        #             return False, res, None
        #         return True, res, body
        #     else:
        #         # 无需请求
        #         return True, {"status":200}, None


class CodeRepositoriesService(object):
    def __init__(self):
        self.MODULES = settings.MODULES

    def initRepositories(self, tenant, user, service, service_code_from, code_url, code_id, code_version):
        if service_code_from == "gitlab_new":
            if custom_config.GITLAB_SERVICE_API:
                project_id = 0
                if user.git_user_id > 0:
                    project_id = gitClient.createProject(tenant.tenant_name + "_" + service.service_alias)
                    logger.debug(project_id)
                    monitorhook.gitProjectMonitor(user.nick_name, service, 'create_git_project', project_id)
                    ts = TenantServiceInfo.objects.get(service_id=service.service_id)
                    if project_id > 0:
                        gitClient.addProjectMember(project_id, user.git_user_id, 'master')
                        gitClient.addProjectMember(project_id, 2, 'reporter')
                        ts.git_project_id = project_id
                        ts.git_url = "git@code.goodrain.com:app/" + tenant.tenant_name + "_" + service.service_alias + ".git"
                        gitClient.createWebHook(project_id)
                    ts.code_from = service_code_from
                    ts.code_version = "master"
                    ts.save()
                    self.codeCheck(ts)
        elif service_code_from == "gitlab_exit" or service_code_from == "gitlab_manual":
            ts = TenantServiceInfo.objects.get(service_id=service.service_id)
            ts.git_project_id = code_id
            ts.git_url = code_url
            ts.code_from = service_code_from
            ts.code_version = code_version
            ts.save()
            self.codeCheck(ts)
        elif service_code_from == "github":
            ts = TenantServiceInfo.objects.get(service_id=service.service_id)
            ts.git_project_id = code_id
            ts.git_url = code_url
            ts.code_from = service_code_from
            ts.code_version = code_version
            ts.save()
            code_user = code_url.split("/")[3]
            code_project_name = code_url.split("/")[4].split(".")[0]
            gitHubClient.createReposHook(code_user, code_project_name, user.github_token)
            self.codeCheck(ts)

    def codeCheck(self, service, check_type="first_check", event_id=None):
        data = {}
        data["tenant_id"] = service.tenant_id
        data["service_id"] = service.service_id
        data["git_url"] = "--branch " + service.code_version + " --depth 1 " + service.git_url
        data["check_type"] = check_type
        data["url_repos"] = service.git_url
        data['code_version'] = service.code_version
        data['git_project_id'] = int(service.git_project_id)
        data['code_from'] = service.code_from
        if event_id:
            data['event_id'] = event_id
        parsed_git_url = git_url_parse(service.git_url)
        if parsed_git_url.host == "code.goodrain.com" and service.code_from == "gitlab_new":
            gitUrl = "--branch " + service.code_version + " --depth 1 " + parsed_git_url.url2ssh
        elif parsed_git_url.host == 'github.com':
            createUser = Users.objects.get(user_id=service.creater)
            if settings.MODULES.get('Privite_Github', True):
                gitUrl = "--branch " + service.code_version + " --depth 1 " + service.git_url
            else:
                gitUrl = "--branch " + service.code_version + " --depth 1 " + parsed_git_url.url2https_token(
                    createUser.github_token)
        else:
            gitUrl = "--branch " + service.code_version + " --depth 1 " + service.git_url
        data["git_url"] = gitUrl

        task = {}
        task["tube"] = "code_check"
        task["service_id"] = service.service_id
        # task["data"] = data
        task.update(data)
        logger.debug(json.dumps(task))
        tenant = Tenants.objects.get(tenant_id=service.tenant_id)
        task["enterprise_id"] = tenant.enterprise_id
        region_api.code_check(service.service_region, tenant.tenant_name, task)

    def showGitUrl(self, service):
        httpGitUrl = service.git_url
        if service.code_from == "gitlab_new" or service.code_from == "gitlab_exit":
            cur_git_url = service.git_url.split(":")
            httpGitUrl = "http://code.goodrain.com/" + cur_git_url[1]
        elif service.code_from == "gitlab_manual":
            httpGitUrl = service.git_url
        return httpGitUrl

    def deleteProject(self, service):
        if custom_config.GITLAB_SERVICE_API:
            if service.code_from == "gitlab_new" and service.git_project_id > 0:
                gitClient.deleteProject(service.git_project_id)

    def getProjectBranches(self, project_id):
        if custom_config.GITLAB_SERVICE_API:
            return gitClient.getProjectBranches(project_id)
        return ""

    def createUser(self, user, email, password, username, name):
        if custom_config.GITLAB_SERVICE_API:
            if user.git_user_id == 0:
                logger.info("account.login",
                            "user {0} didn't owned a gitlab user_id, will create it".format(user.nick_name))
                git_user_id = gitClient.createUser(email, password, username, name)
                if git_user_id == 0:
                    logger.info("account.gituser",
                                "create gitlab user for {0} failed, reason: got uid 0".format(user.nick_name))
                else:
                    user.git_user_id = git_user_id
                    user.save()
                    logger.info("account.gituser", "user {0} set git_user_id = {1}".format(user.nick_name, git_user_id))
                monitorhook.gitUserMonitor(user, git_user_id)

    def modifyUser(self, user, password):
        if custom_config.GITLAB_SERVICE_API:
            gitClient.modifyUser(user.git_user_id, password=password)

    # def addProjectMember(self, git_project_id, git_user_id, level):
    #     if custom_config.GITLAB_SERVICE_API:
    #         gitClient.addProjectMember(git_project_id, git_user_id, level)

    def listProjectMembers(self, git_project_id):
        if custom_config.GITLAB_SERVICE_API:
            return gitClient.listProjectMembers(git_project_id)
        return ""

    def deleteProjectMember(self, project_id, git_user_id):
        if custom_config.GITLAB_SERVICE_API:
            gitClient.deleteProjectMember(project_id, git_user_id)

    def addProjectMember(self, project_id, git_user_id, gitlab_identity):
        if custom_config.GITLAB_SERVICE_API:
            gitClient.addProjectMember(project_id, git_user_id, gitlab_identity)

    def editMemberIdentity(self, project_id, git_user_id, gitlab_identity):
        if custom_config.GITLAB_SERVICE_API:
            gitClient.editMemberIdentity(project_id, git_user_id, gitlab_identity)

    def get_gitHub_access_token(self, code):
        if custom_config.GITHUB_SERVICE_API:
            return gitHubClient.get_access_token(code)
        return ""

    def getgGitHubAllRepos(self, token):
        if custom_config.GITHUB_SERVICE_API:
            return gitHubClient.getAllRepos(token)
        return ""

    def gitHub_authorize_url(self, user):
        if custom_config.GITHUB_SERVICE_API:
            return gitHubClient.authorize_url(user.pk)
        return ""

    def gitHub_ReposRefs(self, user, repos, token):
        if custom_config.GITHUB_SERVICE_API:
            return gitHubClient.getReposRefs(user, repos, token)
        return ""


class AppCreateService(object):
    def get_estimate_service_fee(self, service_attach_info, region_name):
        """根据附加信息获取服务的预估价格"""
        total_price = 0.00
        regionBo = rpmManager.get_work_region_by_name(region_name)
        pre_paid_memory_price = float(regionBo.memory_package_price)
        pre_paid_disk_price = float(regionBo.disk_package_price)
        if service_attach_info.memory_pay_method == "prepaid":
            total_price += service_attach_info.min_node * service_attach_info.min_memory / 1024.0 * pre_paid_memory_price
        if service_attach_info.disk_pay_method == "prepaid":
            total_price += service_attach_info.disk / 1024.0 * pre_paid_disk_price
        total_price = total_price * service_attach_info.pre_paid_period * 30 * 24
        if service_attach_info.pre_paid_period >= 12:
            total_price *= 0.9
        if service_attach_info.pre_paid_period >= 24:
            total_price *= 0.8
        return round(Decimal(total_price), 2)


class ServiceAttachInfoManage(object):
    def is_during_monthly_payment(self, service_attach_info):
        flag = False
        if service_attach_info.memory_pay_method == "prepaid" or service_attach_info.disk_pay_method == "prepaid":
            if datetime.datetime.now() < service_attach_info.buy_end_time:
                flag = True
        return flag

    def is_need_to_update(self, service_attach_info, min_memory, min_node):
        flag = False
        if service_attach_info.min_node != min_node or service_attach_info.min_memory != min_memory:
            flag = True

        return flag

    def create_service_attach_info(self, service, memory, disk, memory_pay_method="postpaid",
                                   disk_pay_method="postpaid",
                                   pre_paid_period=0,
                                   ):
        appCreateService = AppCreateService()
        sai = ServiceAttachInfo()
        sai.tenant_id = service.tenant_id
        sai.service_id = service.service_id
        sai.memory_pay_method = memory_pay_method
        sai.disk_pay_method = disk_pay_method
        if not memory:
            sai.min_memory = service.min_memory * service.min_node
        else:
            sai.min_memory = memory
        # node 去掉了,默认都是1
        sai.min_node = 1
        sai.disk = disk
        sai.pre_paid_period = pre_paid_period
        create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        startTime = datetime.datetime.now() + datetime.timedelta(hours=1)
        endTime = startTime + relativedelta(months=int(pre_paid_period))

        sai.buy_start_time = startTime
        sai.buy_end_time = endTime
        sai.create_time = create_time
        sai.pre_paid_money = appCreateService.get_estimate_service_fee(sai, service.service_region)
        sai.region = service.service_region
        sai.save()
        return sai

    def update_attach_info_by_tenant(self, tenant, service):
        attach_info = ServiceAttachInfo.objects.get(tenant_id=tenant.tenant_id, service_id=service.service_id)
        pre_paid_period = attach_info.pre_paid_period

        if tenant.pay_type == "free":
            # 免费租户的应用过期时间为7天
            startTime = datetime.datetime.now() + datetime.timedelta(days=7) + datetime.timedelta(hours=1)
            startTime = startTime.strftime("%Y-%m-%d %H:00:00")
            startTime = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")

            service.expired_time = startTime
            # 临时将应用的过期时间保持跟租户的过期时间一致
            # service.expired_time = tenant.expired_time
            service.save()
            endTime = startTime + relativedelta(months=int(pre_paid_period))
            attach_info.buy_start_time = startTime
            attach_info.buy_end_time = endTime
        else:
            # 付费用户一个小时调试
            startTime = datetime.datetime.now() + datetime.timedelta(hours=2)
            startTime = startTime.strftime("%Y-%m-%d %H:00:00")
            startTime = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
            endTime = startTime + relativedelta(months=int(pre_paid_period))
            attach_info.buy_start_time = startTime
            attach_info.buy_end_time = endTime
        attach_info.min_memory = service.min_memory * service.min_node
        attach_info.save()
