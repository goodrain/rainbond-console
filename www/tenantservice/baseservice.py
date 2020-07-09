# -*- coding: utf8 -*-
import datetime
import json
import logging

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.forms import model_to_dict

from goodrain_web.custom_config import custom_config
from www.apiclient.regionapi import RegionInvokeApi
from www.db.base import BaseConnection
from www.github_http import GitHubApi
from www.gitlab_http import GitlabApi
from www.models.main import PermRelTenant
from www.models.main import ServiceAttachInfo
from www.models.main import ServiceEvent
from www.models.main import ServiceProbe
from www.models.main import TenantRegionInfo
from www.models.main import TenantRegionPayModel
from www.models.main import TenantRegionResource
from www.models.main import Tenants
from www.models.main import TenantServiceAuth
from www.models.main import TenantServiceEnvVar
from www.models.main import TenantServiceInfo
from www.models.main import TenantServiceMountRelation
from www.models.main import TenantServiceRelation
from www.models.main import TenantServicesPort
from www.models.main import TenantServiceVolume
from www.models.main import Users
from www.models.plugin import PluginBuildVersion
from www.models.plugin import TenantServicePluginRelation
from www.utils.crypt import make_uuid
from www.utils.giturlparse import parse as git_url_parse

logger = logging.getLogger('default')

gitClient = GitlabApi()
gitHubClient = GitHubApi()
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
                    services = TenantServiceInfo.objects.filter(
                        tenant_id=tenant_id, service_region=region).order_by('service_alias')
                else:
                    dsn = BaseConnection()
                    add_sql = ''
                    query_sql = '''
                        select s.* from tenant_service s, service_perms sp where s.tenant_id = "{tenant_id}"
                        and sp.user_id = {user_id} and sp.service_id = s.ID and s.service_region = "{region}" \
                            {add_sql} order by s.service_alias
                        '''.format(
                        tenant_id=tenant_id, user_id=user_pk, region=region, add_sql=add_sql)
                    services = dsn.query(query_sql)
            except PermRelTenant.DoesNotExist:
                if tenant_pk == 5073:
                    services = TenantServiceInfo.objects.filter(
                        tenant_id=tenant_id, service_region=region).order_by('service_alias')

        return services

    def getMaxPort(self, tenant_id, service_key, service_alias):
        cur_service_port = 0
        dsn = BaseConnection()
        query_sql = '''select max(service_port) as service_port from tenant_service where tenant_id="{tenant_id}" and \
            service_key="{service_key}" and service_alias !="{service_alias}";
            '''.format(
            tenant_id=tenant_id, service_key=service_key, service_alias=service_alias)
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
        query_sql = '''select max(service_port) as service_port from tenant_service where tenant_id="{tenant_id}" \
            and service_key="{service_key}";
            '''.format(
            tenant_id=tenant_id, service_key=service_key)
        data = dsn.query(query_sql)
        logger.debug(data)
        if data is not None:
            temp = data[0]["service_port"]
            if temp is not None:
                cur_service_port = int(temp)
        return cur_service_port

    def prepare_mapping_port(self, service, container_port):
        port_list = TenantServicesPort.objects.filter(
            tenant_id=service.tenant_id, mapping_port__gt=container_port).values_list(
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

    def create_service(self,
                       service_id,
                       tenant_id,
                       service_alias,
                       service_cname,
                       service,
                       creater,
                       region,
                       tenant_service_group_id=0,
                       service_origin='assistant'):
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

        logger.debug(newTenantService.tenant_id + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))

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
        """处理组件端口"""
        for port in ports_info:
            # 如果对外访问为打开,则调用api 打开数据
            if port.is_outer_service:
                if port.protocol != "http":
                    stream_outer_num = TenantServicesPort.objects.filter(
                        service_id=port.service_id, is_outer_service=True).exclude(
                            container_port=port.container_port, protocol="http").count()
                    if stream_outer_num > 0:
                        logger.error("stream协议族外部访问只能开启一个")
                        continue
                try:
                    body = region_api.manage_outer_port(service.service_region, tenant.tenant_name, service.service_alias,
                                                        port.container_port, {
                                                            "operation": "open",
                                                            "enterprise_id": tenant.enterprise_id
                                                        })
                    logger.debug("open outer port body {}".format(body))
                    mapping_port = body["bean"]["port"]
                    port.mapping_port = port.container_port
                    port.lb_mapping_port = mapping_port
                    port.save()
                except Exception as e:
                    logger.exception(e)
                    port.is_outer_service = False
                    port.save()
            # 打开对内组件
            if port.is_inner_service:
                mapping_port = port.container_port
                try:
                    port.save(update_fields=['mapping_port'])

                    TenantServiceEnvVar.objects.filter(service_id=port.service_id, container_port=port.container_port).delete()
                    self.saveServiceEnvVar(
                        port.tenant_id,
                        port.service_id,
                        port.container_port,
                        u"连接地址",
                        port.port_alias + "_HOST",
                        "127.0.0.1",
                        False,
                        scope="outer")
                    self.saveServiceEnvVar(
                        port.tenant_id,
                        port.service_id,
                        port.container_port,
                        u"端口",
                        port.port_alias + "_PORT",
                        mapping_port,
                        False,
                        scope="outer")
                    port_envs = TenantServiceEnvVar.objects.filter(
                        service_id=port.service_id, container_port=port.container_port)

                    for env in port_envs:
                        region_api.delete_service_env(service.service_region, tenant.tenant_name, service.service_alias, {
                            "env_name": env.attr_name,
                            "enterprise_id": tenant.enterprise_id
                        })
                        add_attr = {
                            "container_port": env.container_port,
                            "env_name": env.attr_name,
                            "env_value": env.attr_value,
                            "is_change": env.is_change,
                            "name": env.name,
                            "scope": env.scope,
                            "enterprise_id": tenant.enterprise_id
                        }
                        region_api.add_service_env(service.service_region, tenant.tenant_name, service.service_alias, add_attr)
                    region_api.manage_inner_port(service.service_region, tenant.tenant_name, service.service_alias,
                                                 port.container_port, {
                                                     "operation": "open",
                                                     "enterprise_id": tenant.enterprise_id
                                                 })
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
        for tenantServiceEnv in tenantServiceEnvList:
            service = TenantServiceInfo.objects.get(service_id=service_id)
            attr = {
                "tenant_id": tenant.tenant_id,
                "name": tenantServiceEnv.attr_name,
                "env_name": tenantServiceEnv.attr_name,
                "env_value": tenantServiceEnv.attr_value,
                "is_change": False,
                "scope": "outer",
                "container_port": service.inner_port,
                "enterprise_id": tenant.enterprise_id
            }
            region_api.add_service_env(region, tenant.tenant_name, service.service_alias, attr)

    def cancel_service_env(self, tenant_id, service_id, region):
        task = {}
        task["tenant_id"] = tenant_id
        task["attr"] = {}

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

    def addServicePort(self,
                       service,
                       is_init_account,
                       container_port=0,
                       protocol='',
                       port_alias='',
                       is_inner_service=False,
                       is_outer_service=False):
        port = TenantServicesPort(
            tenant_id=service.tenant_id,
            service_id=service.service_id,
            container_port=container_port,
            protocol=protocol,
            port_alias=port_alias,
            is_inner_service=is_inner_service,
            is_outer_service=is_outer_service)
        try:
            env_prefix = port_alias.upper() if bool(port_alias) else service.service_key.upper()
            if is_inner_service:
                # 取消mapping端口
                mapping_port = container_port
                port.mapping_port = mapping_port
                if service.language == "docker-compose":
                    self.saveServiceEnvVar(
                        service.tenant_id,
                        service.service_id,
                        container_port,
                        u"连接地址",
                        env_prefix + "_PORT_" + str(container_port) + "_TCP_ADDR",
                        "127.0.0.1",
                        False,
                        scope="outer")
                    self.saveServiceEnvVar(
                        service.tenant_id,
                        service.service_id,
                        container_port,
                        u"端口",
                        env_prefix + "_PORT_" + str(container_port) + "_TCP_PORT",
                        mapping_port,
                        False,
                        scope="outer")
                else:
                    self.saveServiceEnvVar(
                        service.tenant_id,
                        service.service_id,
                        container_port,
                        u"连接地址",
                        env_prefix + "_HOST",
                        "127.0.0.1",
                        False,
                        scope="outer")
                    self.saveServiceEnvVar(
                        service.tenant_id,
                        service.service_id,
                        container_port,
                        u"端口",
                        env_prefix + "_PORT",
                        mapping_port,
                        False,
                        scope="outer")
            if is_init_account:
                password = service.service_id[:8]
                TenantServiceAuth.objects.create(service_id=service.service_id, user="admin", password=password)
                self.saveServiceEnvVar(
                    service.tenant_id, service.service_id, -1, u"用户名", env_prefix + "_USER", "admin", False, scope="both")
                self.saveServiceEnvVar(
                    service.tenant_id, service.service_id, -1, u"密码", env_prefix + "_PASS", password, False, scope="both")
            port.save()
        except Exception as e:
            logger.exception(e)

    # 检查事件是否超时，组件起停操作30s超时，其他操作3m超时
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
        TenantServiceMountRelation.objects.get(service_id=service.service_id, dep_service_id=dependS.service_id).delete()

    def create_service_volume(self, service, volume_path):
        category = service.category
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

        res, body = region_api.add_service_volume(service.service_region, tenant.tenant_name, service.service_alias, json_data)
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
        res, body = region_api.delete_service_volume(region, tenant.tenant_name, service.service_alias, json_data)
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
            if TenantServiceVolume.objects.filter(service_id=service.service_id, volume_path=path).count() > 0:
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
                    service.service_region, tenant.tenant_name, service.service_alias, json.dumps(data)))
                res, body = region_api.add_service_dep_volumes(service.service_region, tenant.tenant_name,
                                                               service.service_alias, data)
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
            res, body = region_api.delete_service_dep_volumes(service.service_region, tenant.tenant_name, service.service_alias,
                                                              data)
            if res.status == 200:
                TenantServiceMountRelation.objects.get(
                    service_id=service.service_id, dep_service_id=dep_volume.service_id).delete()
                return True
            return False
        except region_api.CallApiError as e:
            if e.status == 404:
                logger.debug('service mnt relation not in region then delete rel directly in console')
                TenantServiceMountRelation.objects.get(
                    service_id=service.service_id, dep_service_id=dep_volume.service_id).delete()
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
            res, body = region_api.add_service_volumes(service.service_region, tenant.tenant_name, service.service_alias, data)
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
                    return False, '有依赖的组件'
            try:
                res, body = region_api.delete_service_volumes(service.service_region, tenant.tenant_name, service.service_alias,
                                                              volume.volume_name, tenant.enterprise_id)
                if res.status == 200:
                    volume.delete()
                    return True, None
                return False, 'api delete failed'
            except region_api.CallApiError as e:
                if e.status == 404:
                    logger.debug('service {0} volume {1} not found in region'.format(service.service_alias, volume.volume_name))
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
            tenant_id = service.tenant_id
            service_id = service.service_id
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

    # 获取组件类型
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
            event = ServiceEvent(
                event_id=make_uuid(),
                service_id=service.service_id,
                tenant_id=tenant.tenant_id,
                type="{0}".format(action),
                deploy_version=service.deploy_version,
                old_deploy_version=service.deploy_version,
                user_name=user.nick_name,
                start_time=datetime.datetime.now())
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
                    initial_delay_second=4,
                    period_second=3,
                    timeout_second=5,
                    failure_threshold=3,
                    success_threshold=1,
                    is_used=True,
                    probe_id=make_uuid(),
                    mode="readiness")
                json_data = model_to_dict(service_probe)
                is_used = 1 if json_data["is_used"] else 0
                json_data.update({"is_used": is_used})
                json_data["enterprise_id"] = tenant.enterprise_id
                res, body = region_api.add_service_probe(service.service_region, tenant.tenant_name, service.service_alias,
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
            except Exception:
                pass
        return memory

    def get_services_plugin_resource_map(self, service_ids):
        tprs = TenantServicePluginRelation.objects.filter(service_id__in=service_ids, plugin_status=True)
        service_plugin_map = {}
        for tpr in tprs:
            pbv = PluginBuildVersion.objects.filter(
                plugin_id=tpr.plugin_id, build_version=tpr.build_version).values("min_memory")
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
            tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True, is_init=True)
        else:
            tenant_region_list = TenantRegionInfo.objects.filter(
                tenant_id=tenant.tenant_id, region_name=region, is_active=True, is_init=True)
        for tenant_region in tenant_region_list:
            res = region_api.get_tenant_resources(tenant_region.region_name, tenant.tenant_name, tenant.enterprise_id)
            bean = res["bean"]
            memory = int(bean["memory"])
            totalMemory += memory
        return totalMemory

    def calculate_guarantee_resource(self, tenant):
        memory = 0
        if tenant.pay_type == "company":
            cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            dsn = BaseConnection()
            query_sql = "select region_name,sum(buy_memory) as buy_memory,sum(buy_disk) as buy_disk, sum(buy_net) as buy_net \
                 from tenant_region_pay_model where tenant_id='"\
                        + tenant.tenant_id + "' and buy_end_time <='" + cur_time + "' group by region_name"
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

    def curServiceMemory(self, tenant, cur_service):
        memory = 0
        try:
            body = region_api.check_service_status(cur_service.service_region, tenant.tenant_name, cur_service.service_alias,
                                                   tenant.enterprise_id)
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

        logger.debug('[{}:{}-{}] package:{}, expire:{}, memory:{}'.format(tenant.tenant_name, tenant.pay_type, region, pkg_tag,
                                                                          expire, memory))
        return memory


class TenantAccountService(object):
    def __init__(self):
        self.MODULES = settings.MODULES

    def isOwnedMoney(self, tenant, region_name):
        if self.MODULES["Owned_Fee"]:
            if tenant.balance < 0 and tenant.pay_type == "payed":
                return True
        return False

    def isExpired(self, tenant, service):
        if service.expired_time is not None:
            if tenant.pay_type == "free" and service.expired_time < datetime.datetime.now():
                return True
        else:
            # 将原有免费用户的组件设置为7天后
            service.expired_time = datetime.datetime.now() + datetime.timedelta(days=7)
        return False

    def get_monthly_payment(self, tenant, region_name):
        # 0 未包月 1快到期 2 已到期 3离到期时间很长
        flag = 0
        tenant_region_pay_list = TenantRegionPayModel.objects.filter(tenant_id=tenant.tenant_id, region_name=region_name)
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


class CodeRepositoriesService(object):
    def __init__(self):
        self.MODULES = settings.MODULES

    def initRepositories(self, tenant, user, service, service_code_from, code_url, code_id, code_version):
        if service_code_from == "gitlab_new":
            if custom_config.GITLAB:
                project_id = 0
                if user.git_user_id > 0:
                    project_id = gitClient.createProject(tenant.tenant_name + "_" + service.service_alias)
                    logger.debug(project_id)
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
        if custom_config.GITLAB:
            if service.code_from == "gitlab_new" and service.git_project_id > 0:
                gitClient.deleteProject(service.git_project_id)

    def getProjectBranches(self, project_id):
        if custom_config.GITLAB:
            return gitClient.getProjectBranches(project_id)
        return ""

    def createUser(self, user, email, password, username, name):
        if custom_config.GITLAB:
            if user.git_user_id == 0:
                logger.info("account.login", "user {0} didn't owned a gitlab user_id, will create it".format(user.nick_name))
                git_user_id = gitClient.createUser(email, password, username, name)
                if git_user_id == 0:
                    logger.info("account.gituser",
                                "create gitlab user for {0} failed, reason: got uid 0".format(user.nick_name))
                else:
                    user.git_user_id = git_user_id
                    user.save()
                    logger.info("account.gituser", "user {0} set git_user_id = {1}".format(user.nick_name, git_user_id))

    def modifyUser(self, user, password):
        if custom_config.GITLAB:
            gitClient.modifyUser(user.git_user_id, password=password)

    # def addProjectMember(self, git_project_id, git_user_id, level):
    #     if custom_config.GITLAB:
    #         gitClient.addProjectMember(git_project_id, git_user_id, level)

    def listProjectMembers(self, git_project_id):
        if custom_config.GITLAB:
            return gitClient.listProjectMembers(git_project_id)
        return ""

    def deleteProjectMember(self, project_id, git_user_id):
        if custom_config.GITLAB:
            gitClient.deleteProjectMember(project_id, git_user_id)

    def addProjectMember(self, project_id, git_user_id, gitlab_identity):
        if custom_config.GITLAB:
            gitClient.addProjectMember(project_id, git_user_id, gitlab_identity)

    def editMemberIdentity(self, project_id, git_user_id, gitlab_identity):
        if custom_config.GITLAB:
            gitClient.editMemberIdentity(project_id, git_user_id, gitlab_identity)

    def get_gitHub_access_token(self, code):
        if custom_config.GITHUB:
            return gitHubClient.get_access_token(code)
        return ""

    def getgGitHubAllRepos(self, token):
        if custom_config.GITHUB:
            return gitHubClient.getAllRepos(token)
        return ""

    def gitHub_authorize_url(self, user):
        if custom_config.GITHUB:
            return gitHubClient.authorize_url(user.pk)
        return ""

    def gitHub_ReposRefs(self, user, repos, token):
        if custom_config.GITHUB:
            return gitHubClient.getReposRefs(user, repos, token)
        return ""


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

    def update_attach_info_by_tenant(self, tenant, service):
        attach_info = ServiceAttachInfo.objects.get(tenant_id=tenant.tenant_id, service_id=service.service_id)
        pre_paid_period = attach_info.pre_paid_period

        if tenant.pay_type == "free":
            # 免费租户的组件过期时间为7天
            startTime = datetime.datetime.now() + datetime.timedelta(days=7) + datetime.timedelta(hours=1)
            startTime = startTime.strftime("%Y-%m-%d %H:00:00")
            startTime = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")

            service.expired_time = startTime
            # 临时将组件的过期时间保持跟租户的过期时间一致
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
