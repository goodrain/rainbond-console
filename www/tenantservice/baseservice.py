# -*- coding: utf8 -*-
import datetime
import json

from www.db import BaseConnection
from www.models import Users, TenantServiceInfo, PermRelTenant, Tenants, \
    TenantServiceRelation, TenantServiceAuth, TenantServiceEnvVar, \
    TenantRegionInfo, TenantServicesPort, TenantServiceMountRelation, \
    TenantServiceVolume, ServiceInfo, AppServiceRelation, AppServiceEnv, \
    AppServicePort, ServiceExtendMethod, AppServiceVolume
from www.models.main import TenantRegionPayModel
from www.service_http import RegionServiceApi
from django.conf import settings
from goodrain_web.custom_config import custom_config
from www.monitorservice.monitorhook import MonitorHook
from www.gitlab_http import GitlabApi
from www.github_http import GitHubApi
from www.utils.giturlparse import parse as git_url_parse
from www.utils.sn import instance
from www.app_http import AppServiceApi

import logging
logger = logging.getLogger('default')

monitorhook = MonitorHook()
regionClient = RegionServiceApi()
gitClient = GitlabApi()
gitHubClient = GitHubApi()
appClient = AppServiceApi()


class BaseTenantService(object):

    def get_service_list(self, tenant_pk, user, tenant_id, region):
        user_pk = user.pk
        tmp = TenantServiceInfo()
        if user.is_sys_admin:
            if hasattr(tmp, 'service_origin'):
                services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region, service_origin='assistant')
            else:
                services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region)
        else:
            my_tenant_identity = PermRelTenant.objects.get(tenant_id=tenant_pk, user_id=user_pk).identity
            if my_tenant_identity in ('admin', 'developer', 'viewer', 'gray'):
                if hasattr(tmp, 'service_origin'):
                    services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region, service_origin='assistant').order_by('service_alias')
                else:
                    services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region).order_by('service_alias')
            else:
                dsn = BaseConnection()
                add_sql = ''
                if hasattr(tmp, 'service_origin'):
                    add_sql = """ and service_origin="assistant" """
                query_sql = '''
                    select s.* from tenant_service s, service_perms sp where s.tenant_id = "{tenant_id}"
                    and sp.user_id = {user_id} and sp.service_id = s.ID and s.service_region = "{region}" {add_sql} order by s.service_alias
                    '''.format(tenant_id=tenant_id, user_id=user_pk, region=region, add_sql=add_sql)
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
        port_list = TenantServicesPort.objects.filter(tenant_id=service.tenant_id, mapping_port__gt=container_port).values_list(
            'mapping_port', flat=True).order_by('mapping_port')

        port_list = list(port_list)
        port_list.insert(0, container_port)
        max_port = reduce(lambda x, y: y if (y - x) == 1 else x, port_list)
        return max_port + 1

    def create_service(self, service_id, tenant_id, service_alias, service_cname, service, creater, region):
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
            logger.debug("region:{0} and service_type:{1}".format(region, service.service_type))
            if (region == "ucloud-bj-1" or region == "ali-sh") and service.service_type == "mysql":
                host_path = "/app-data/tenant/" + tenant_id + "/service/" + service_id
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
        data["dep_sids"] = dep_sids

        ports_info = TenantServicesPort.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        if ports_info:
            data["extend_info"]["ports"] = list(ports_info)

        envs_info = TenantServiceEnvVar.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if envs_info:
            data["extend_info"]["envs"] = list(envs_info)

        # 获取数据持久化数据
        volume_info = TenantServiceVolume.objects.filter(service_id=newTenantService.service_id).values(
            'service_id', 'category', 'host_path', 'volume_path')
        if volume_info:
            data["extend_info"]["volume"] = list(volume_info)

        logger.debug(newTenantService.tenant_id + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        regionClient.create_service(region, newTenantService.tenant_id, json.dumps(data))
        logger.debug(newTenantService.tenant_id + " end create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))

    def create_service_dependency(self, tenant_id, service_id, dep_service_id, region):
        dependS = TenantServiceInfo.objects.get(service_id=dep_service_id)
        task = {}
        task["dep_service_id"] = dep_service_id
        task["tenant_id"] = tenant_id
        task["dep_service_type"] = dependS.service_type
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
        task["scope"] = "outer"
        service = TenantServiceInfo.objects.get(service_id=service_id)
        task["container_port"] = service.inner_port
        regionClient.createServiceEnv(region, service_id, json.dumps(task))

    def cancel_service_env(self, tenant_id, service_id, region):
        task = {}
        task["tenant_id"] = tenant_id
        task["attr"] = {}
        regionClient.createServiceEnv(region, service_id, json.dumps(task))

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
        except Exception, e:
            logger.exception(e)

    def is_user_click(self, region, service_id):
        is_ok = True
        data = regionClient.getLatestServiceEvent(region, service_id)
        if data.get("event") is not None:
            event = data.get("event")
            if len(event) > 0:
                lastTime = event.get("time")
                curTime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                diffsec = int(curTime) - int(lastTime)
                if event.status == "start" and diffsec <= 180:
                    is_ok = False
        return is_ok

    def create_service_mnt(self, tenant_id, service_id, dep_service_alias, region):
        dependS = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_alias=dep_service_alias)
        task = {}
        task["dep_service_id"] = dependS.service_id
        task["tenant_id"] = tenant_id
        task["mnt_name"] = "/mnt/" + dependS.service_alias
        task["mnt_dir"] = dependS.host_path
        regionClient.createServiceMnt(region, service_id, json.dumps(task))
        tsr = TenantServiceMountRelation()
        tsr.tenant_id = tenant_id
        tsr.service_id = service_id
        tsr.dep_service_id = dependS.service_id
        tsr.mnt_name = "/mnt/" + dependS.service_alias
        tsr.mnt_dir = dependS.host_path
        tsr.dep_order = 0
        tsr.save()

    def cancel_service_mnt(self, tenant_id, service_id, dep_service_alias, region):
        dependS = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_alias=dep_service_alias)
        task = {}
        task["dep_service_id"] = dependS.service_id
        task["tenant_id"] = tenant_id
        task["mnt_name"] = "v"
        task["mnt_dir"] = "v"
        regionClient.cancelServiceMnt(region, service_id, json.dumps(task))
        TenantServiceMountRelation.objects.get(service_id=service_id, dep_service_id=dependS.service_id).delete()

    def create_service_volume(self, service, volume_path):
        category = service.category
        region = service.service_region
        service_id = service.service_id
        host_path, volume_id = self.add_volume_list(service, volume_path)
        if volume_id is None:
            logger.error("add volume error!")
            return None
        # 发送到region进行处理
        json_data = {
            "service_id": service_id,
            "category": category,
            "host_path": host_path,
            "volume_path": volume_path
        }
        res, body = regionClient.createServiceVolume(region, service_id, json.dumps(json_data))
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
        json_data = {
            "service_id": service_id,
            "category": volume.category,
            "host_path": volume.host_path,
            "volume_path": volume.volume_path
        }
        res, body = regionClient.cancelServiceVolume(region, service_id, json.dumps(json_data))
        if res.status == 200:
            TenantServiceVolume.objects.filter(pk=volume_id).delete()
            return True
        else:
            return False

    def add_volume_list(self, service, volume_path):
        try:
            category = service.category
            region = service.service_region
            tenant_id = service.tenant_id
            service_id = service.service_id
            volume = TenantServiceVolume(service_id=service_id,
                                         category=category)

            # 确定host_path
            if (region == "ucloud-bj-1" or region == "ali-sh") and service.service_type == "mysql":
                host_path = "/app-data/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
            else:
                host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
            volume.host_path = host_path
            volume.volume_path = volume_path
            volume.save()
            return host_path, volume.ID
        except Exception as e:
            logger.exception(e)

    # 服务对外端口类型
    def custom_port_type(self, service, port_type):
        try:
            service_id = service.service_id
            region = service.service_region

            # 发送到region进行处理
            json_data = {
                "service_id": service_id,
                "port_type": port_type
            }
            res, body = regionClient.mutiPortSupport(region, service_id, json.dumps(json_data))
            if res.status == 200:
                return service_id
            else:
                return None
        except Exception as e:
            logger.exception(e)

    # 服务挂载卷类型 设置
    def custom_mnt_shar_type(self,service,volume_type):
        try:
            service_id = service.service_id
            region = service.service_region
            json_data = {
                "service_id":service_id,
                "volume_type":volume_type
            }
            res,body = regionClient.mntShareSupport(region,service_id,json.dumps(json_data))
            if res.status ==200:
                return True
            else:
                return None
        except Exception as e:
            logger.exception(e)

    # 下载服务模版逻辑
    def download_service_info(self, service_key, app_version):
        num = ServiceInfo.objects.filter(service_key=service_key, version=app_version).count()
        if num == 0:
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
            update_version = 1
            try:
                base_info = ServiceInfo.objects.get(service_key=service_key, version=version)
                update_version = base_info.update_version
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
            base_info.update_version = update_version
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
            relation_data = []
            if pre_list:
                for relation in pre_list:
                    app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                      app_version=relation.get("app_version"),
                                                      app_alias=relation.get("app_alias"),
                                                      dep_service_key=relation.get("dep_service_key"),
                                                      dep_app_version=relation.get("dep_app_version"),
                                                      dep_app_alias=relation.get("dep_app_alias"))
                    relation_data.append(app_relation)
            if suf_list:
                for relation in suf_list:
                    app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                      app_version=relation.get("app_version"),
                                                      app_alias=relation.get("app_alias"),
                                                      dep_service_key=relation.get("dep_service_key"),
                                                      dep_app_version=relation.get("dep_app_version"),
                                                      dep_app_alias=relation.get("dep_app_alias"))
                    relation_data.append(app_relation)
            AppServiceRelation.objects.filter(service_key=service_key, app_version=version).delete()
            if len(relation_data) > 0:
                AppServiceRelation.objects.bulk_create(relation_data)
            logger.debug('---add app service relation---ok---')
            # 服务持久化记录
            volume_data = []
            if volume_list:
                for app_volume in volume_list:
                    volume = AppServiceVolume(service_key=app_volume.service_key,
                                              app_version=app_volume.app_version,
                                              category=app_volume.category,
                                              volume_path=app_volume.volume_path);

                    volume_data.append(volume)
            AppServiceVolume.objects.filter(service_key=service_key, app_version=version).delete()
            if len(volume_data) > 0:
                AppServiceVolume.objects.bulk_create(volume_data)
            logger.debug('---add app service volume---ok---')
            return 200, base_info
        else:
            return 501, None


class TenantUsedResource(object):

    def __init__(self):
        self.feerule = settings.REGION_RULE
        self.MODULES = settings.MODULES

    def calculate_real_used_resource(self, tenant):
        totalMemory = 0
        tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True, is_init=True)
        running_data = {}
        for tenant_region in tenant_region_list:
            logger.debug(tenant_region.region_name)
            temp_data = regionClient.getTenantRunningServiceId(tenant_region.region_name, tenant_region.tenant_id)
            logger.debug(temp_data)
            if len(temp_data["data"]) > 0:
                running_data.update(temp_data["data"])
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
                disk_storage = total_memory - int(apply_memory)
                if disk_storage < 0:
                    disk_storage = 0
                real_memory = running_data.get(service_id)
                if real_memory is not None and real_memory != "":
                    totalMemory = totalMemory + int(apply_memory) + disk_storage
                else:
                    totalMemory = totalMemory + disk_storage
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
                newAddMemory = newAddMemory + self.curServiceMemory(cur_service)
            if tenant.pay_type == "free":
                tm = self.calculate_real_used_resource(tenant) + newAddMemory
                logger.debug(tenant.tenant_id + " used memory " + str(tm))
                if tm <= tenant.limit_memory:
                    result = True
            elif tenant.pay_type == "payed":
                tm = self.calculate_real_used_resource(tenant) + newAddMemory
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

    def curServiceMemory(self, cur_service):
        memory = 0
        try:
            body = regionClient.check_service_status(cur_service.service_region, cur_service.service_id)
            status = body[cur_service.service_id]
            if status != "running":
                memory = cur_service.min_node * cur_service.min_memory
        except Exception:
            pass
        return memory


class TenantAccountService(object):
    def __init__(self):
        self.MODULES = settings.MODULES

    def isOwnedMoney(self, tenant, region_name):
        if self.MODULES["Owned_Fee"]:
            tenant_region = TenantRegionInfo.objects.get(tenant_id=tenant.tenant_id, region_name=region_name)
            if tenant_region.service_status == 2 and tenant.pay_type == "payed":
                return True
        return False

    def isExpired(self, tenant):
        if tenant.pay_type == "free" and tenant.expired_time < datetime.datetime.now():
            return True
        return False

    def get_monthly_payment(self, tenant, region_name):
        # 0 未包月 1快到期 2 已到期 3离到期时间很长
        flag = 0;
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

    def isCloseToMonthlyExpired(self, tenant, region_name):
        tenant_region_pay_list = TenantRegionPayModel.objects.filter(tenant_id=tenant.tenant_id,region_name=region_name)
        if len(tenant_region_pay_list) == 0:
            return False
        tag = 1
        for pay_model in tenant_region_pay_list:
            if pay_model.buy_end_time > datetime.datetime.now():
                timedelta = (pay_model.buy_end_time-datetime.datetime.now()).days
                if timedelta > 0 and timedelta < 3:
                    return True
        return False


class TenantRegionService(object):

    def init_for_region(self, region, tenant_name, tenant_id, user):
        success = True
        try:
            tenantRegion = TenantRegionInfo.objects.get(tenant_id=tenant_id, region_name=region)
        except Exception:
            tenantRegion = TenantRegionInfo()
            tenantRegion.tenant_id = tenant_id
            tenantRegion.region_name = region
            tenantRegion.save()

        if not tenantRegion.is_init:
            api = RegionServiceApi()
            logger.info("account.register", "create tenant {0} with tenant_id {1} on region {2}".format(tenant_name, tenant_id, region))
            try:
                res, body = api.create_tenant(region, tenant_name, tenant_id)
            except api.CallApiError, e:
                logger.error("account.register", "create tenant {0} failed".format(tenant_name))
                logger.exception("account.register", e)
                success = False
            if success:
                tenantRegion.is_active = True
                tenantRegion.is_init = True
                tenantRegion.save()
            tenant = Tenants()
            tenant.tenant_id = tenant_id
            tenant.tenant_name = tenant_name
            monitorhook.tenantMonitor(tenant, user, "init_tenant", success)
        return success


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

    def codeCheck(self, service):
        data = {}
        data["tenant_id"] = service.tenant_id
        data["service_id"] = service.service_id
        data["git_url"] = "--branch " + service.code_version + " --depth 1 " + service.git_url

        parsed_git_url = git_url_parse(service.git_url)
        if parsed_git_url.host == "code.goodrain.com" and service.code_from=="gitlab_new":
            gitUrl = "--branch " + service.code_version + " --depth 1 " + parsed_git_url.url2ssh
        elif parsed_git_url.host == 'github.com':
            createUser = Users.objects.get(user_id=service.creater)
            gitUrl = "--branch " + service.code_version + " --depth 1 " + parsed_git_url.url2https_token(createUser.github_token)
        else:
            gitUrl = "--branch " + service.code_version + " --depth 1 " + service.git_url
        data["git_url"] = gitUrl

        task = {}
        task["tube"] = "code_check"
        task["service_id"] = service.service_id
        task["data"] = data
        logger.debug(json.dumps(task))
        regionClient.writeToRegionBeanstalk(service.service_region, service.service_id, json.dumps(task))

    def showGitUrl(self, service):
        httpGitUrl = service.git_url
        if service.code_from == "gitlab_new" or service.code_from == "gitlab_exit":
            cur_git_url = service.git_url.split("/")
            httpGitUrl = "http://code.goodrain.com/app/" + cur_git_url[1]
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
                logger.info("account.login", "user {0} didn't owned a gitlab user_id, will create it".format(user.nick_name))
                git_user_id = gitClient.createUser(email, password, username, name)
                if git_user_id == 0:
                    logger.info("account.gituser", "create gitlab user for {0} failed, reason: got uid 0".format(user.nick_name))
                else:
                    user.git_user_id = git_user_id
                    user.save()
                    logger.info("account.gituser", "user {0} set git_user_id = {1}".format(user.nick_name, git_user_id))
                monitorhook.gitUserMonitor(user, git_user_id)

    def modifyUser(self, user, password):
        if custom_config.GITLAB_SERVICE_API:
            gitClient.modifyUser(user.git_user_id, password=password)

    def addProjectMember(self, git_project_id, git_user_id, level):
        if custom_config.GITLAB_SERVICE_API:
            gitClient.addProjectMember(git_project_id, git_user_id, level)

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
