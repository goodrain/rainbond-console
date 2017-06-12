# -*- coding: utf8 -*-
from www.models import AppServiceGroup, ServiceGroup, AppService, ServiceInfo, AppServiceRelation, ServiceGroupRelation, \
    AppServicePort, AppServiceEnv, AppServiceVolume, TenantServiceRelation, TenantServiceInfo, TenantServiceAuth, \
    ServiceDomain, TenantServiceEnvVar, TenantServicesPort, TenantServiceVolume, BackServiceInstallTemp, \
    TenantServiceEnv, TenantServiceMountRelation, ServiceAttachInfo, ServiceCreateStep, ServiceEvent, \
    PublishedGroupServiceRelation
from www.monitorservice.monitorhook import MonitorHook
from www.region import RegionInfo
import random
import logging
import json
from django.conf import settings

from www.service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid

logger = logging.getLogger('default')
baseService = BaseTenantService()
monitorhook = MonitorHook()
regionClient = RegionServiceApi()


class BackServiceInstall(object):
    def __init__(self):
        # 初始化grdemo的tenant_id
        self.tenant_id = "0622f5b7751f4c3c91f03e60a10a5e85"
        self.tenant_name = "grdemo"
        # 随机选择数据中心
        # regions = RegionInfo.register_choices()
        # regions = [(name, display_name) for name, display_name in regions if name != "aws-jp-1"]
        # select_region = regions[random.randint(0, len(regions) - 1)][0]
        self.region_name = "xunda-bj"
        self.user_id = 5178
        self.nick_name = "grdemo"

    def __get_group_id(self, group_alias):
        """
        获取服务所在组ID
        :return: 组ID
        """

        def is_group_exist(group_name):
            return ServiceGroup.objects.filter(tenant_id=self.tenant_id, region_name=self.region_name,
                                               group_name=group_name).exists()

        group_name = group_alias
        while True:
            if is_group_exist(group_name):
                logger.debug(
                    "group name {0} for tenant_id {1} region {2} is already exist ".format(group_alias, self.tenant_id,
                                                                                           self.region_name))
                suffix = make_uuid(self.tenant_id)[-3:]
                group_name = group_alias + "_" + suffix
            else:
                group = ServiceGroup.objects.create(tenant_id=self.tenant_id, region_name=self.region_name,
                                                    group_name=group_name)
                return group.ID

    def get_published_service_info(self, groupId):
        result = []
        pgsr_list = PublishedGroupServiceRelation.objects.filter(group_pk=groupId)
        for pgsr in pgsr_list:
            apps = AppService.objects.filter(service_key=pgsr.service_key,app_version=pgsr.version).order_by("-ID")
            if apps:
                result.append(apps[0])
            else:
                apps = AppService.objects.filter(service_key=pgsr.service_key).order_by("-ID")
                if apps:
                    result.append(apps[0])
        return result

    def getServiceModel(self, app_service_list, service_id_list):
        published_service_list = []
        for app_service in app_service_list:
            services = ServiceInfo.objects.filter(service_key=app_service.service_key, version=app_service.app_version)
            services = list(services)
            # 没有服务模板,需要下载模板
            if len(services) == 0:
                code, base_info, dep_map, error_msg = baseService.download_service_info(app_service.service_key,
                                                                                        app_service.app_version)
                if code == 500:
                    logger.error(error_msg)
                else:
                    services.append(base_info)
            if len(services) > 0:
                published_service_list.append(services[0])
            else:
                logger.error(
                    "service_key {0} version {1} is not found in table service or can be download from market".format(
                        app_service.service_key, app_service.app_version))
        if len(published_service_list) != len(service_id_list):
            logger.debug("published_service_list ===== {0}".format(len(published_service_list)))
            logger.debug("service_id_list ===== {}".format(len(service_id_list)))
            logger.error("publised service is not found in table service")
        return published_service_list

    def topological_sort(self, graph):
        is_visit = dict((node, False) for node in graph)
        li = []

        def dfs(graph, start_node):
            for end_node in graph[start_node]:
                if not is_visit[end_node]:
                    is_visit[end_node] = True
                    dfs(graph, end_node)
            li.append(start_node)

        for start_node in graph:
            if not is_visit[start_node]:
                is_visit[start_node] = True
                dfs(graph, start_node)
        return li

    def sort_service(self, publish_service_list):
        service_map = {s.service_key: s for s in publish_service_list}
        result = []
        key_app_map = {}
        for app in publish_service_list:
            dep_services = AppServiceRelation.objects.filter(service_key=app.service_key, app_version=app.version)
            if dep_services:
                key_app_map[app.service_key] = [ds.dep_service_key for ds in dep_services]
            else:
                key_app_map[app.service_key] = []
        logger.debug(" service_map:{} ".format(service_map))
        service_keys = self.topological_sort(key_app_map)

        for key in service_keys:
            result.append(service_map.get(key))
        return result

    def create_dep_service(self, service_info, service_id, key_id_map):
        app_relations = AppServiceRelation.objects.filter(service_key=service_info.service_key,
                                                          app_version=service_info.version)
        dep_service_ids = []
        if app_relations:
            for dep_app in app_relations:
                dep_service_id = key_id_map.get(dep_app.dep_service_key)
                dep_service_ids.append(dep_service_id)
        for dep_id in dep_service_ids:
            baseService.create_service_dependency(self.tenant_id, service_id, dep_id, self.region_name)
        logger.info("create service info for service_id{0} ".format(service_id))

    def copy_ports(self, source_service, current_service):
        AppPorts = AppServicePort.objects.filter(service_key=current_service.service_key,
                                                 app_version=current_service.version)
        baseService = BaseTenantService()
        for port in AppPorts:
            baseService.addServicePort(current_service, source_service.is_init_accout,
                                       container_port=port.container_port, protocol=port.protocol,
                                       port_alias=port.port_alias,
                                       is_inner_service=port.is_inner_service, is_outer_service=port.is_outer_service)

    def copy_envs(self, service_info, current_service):
        s = current_service
        baseService = BaseTenantService()
        envs = AppServiceEnv.objects.filter(service_key=service_info.service_key, app_version=service_info.version)
        outer_ports = AppServicePort.objects.filter(service_key=service_info.service_key,
                                                    app_version=service_info.version,
                                                    is_outer_service=True,
                                                    protocol='http')
        for env in envs:
            if env.attr_name == 'SITE_URL':
                if self.region_name in RegionInfo.valid_regions():
                    port = RegionInfo.region_port(self.region_name)
                    domain = RegionInfo.region_domain(self.region_name)
                    env.options="direct_copy"
                    if len(outer_ports)>0:
                        env.attr_value = 'http://{}.{}.{}{}:{}'.format(outer_ports[0].container_port, current_service.serviceAlias,self.tenant_name, domain, port)
                    logger.debug("SITE_URL = {} options = {}".format(env.attr_value, env.options))
            elif env.attr_name == "TRUSTED_DOMAIN":
                if self.region_name in RegionInfo.valid_regions():
                    port = RegionInfo.region_port(self.region_name)
                    domain = RegionInfo.region_domain(self.region_name)
                    env.options = 'direct_copy'
                    if len(outer_ports) > 0:
                        env.attr_value = '{}.{}.{}{}:{}'.format(outer_ports[0].container_port, current_service.serviceAlias, self.tenant_name, domain, port)
                    logger.debug("TRUSTED_DOMAIN = {} options = {}".format(env.attr_value, env.options))

            baseService.saveServiceEnvVar(s.tenant_id, s.service_id, env.container_port, env.name,
                                          env.attr_name, env.attr_value, env.is_change, env.scope)

    def copy_volumes(self, source_service, tenant_service):
        volumes = AppServiceVolume.objects.filter(service_key=source_service.service_key,
                                                  app_version=source_service.version)
        for volume in volumes:
            baseService.add_volume_list(tenant_service, volume.volume_path)

    def install_services(self, share_pk):
        current_service_ids = []
        group_id = None
        current_services = []
        url_map = {}
        try:
            app_service_groups = AppServiceGroup.objects.filter(ID=share_pk)
            app_service_group = None
            if app_service_groups:
                app_service_group = app_service_groups[0]

            if not app_service_group:
                logger.debug("cannot find app_service_group for group_share_id {0}".format(share_pk))
                return {"ok": False, "msg": "cannot find app_service_group"}
            group_id = self.__get_group_id(app_service_group.group_share_alias)
            # 查询分享组中的服务ID
            service_id_list = ServiceGroupRelation.objects.filter(group_id=app_service_group.group_id).values_list("service_id", flat=True)
            app_service_list = self.get_published_service_info(app_service_group.ID)
            published_service_list = self.getServiceModel(app_service_list, service_id_list)
            sorted_service = self.sort_service(published_service_list)
            # 先生成服务的service_id
            key_id_map = {}
            for service_info in sorted_service:
                service_key = service_info.service_key
                service_id = make_uuid(service_key)
                current_service_ids.append(service_id)
                key_id_map[service_key] = service_id
            for service_info in sorted_service:
                logger.debug("service_info.service_key: {}".format(service_info.service_key))
                service_id = key_id_map.get(service_info.service_key)
                service_alias = "gr" + service_id[-6:]
                # user_id为grdemo用户的id
                newTenantService = baseService.create_service(service_id, self.tenant_id, service_alias,
                                                              service_info.service_name,
                                                              service_info,
                                                              self.user_id, region=self.region_name)
                if group_id > 0:
                    ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                                                        tenant_id=self.tenant_id,
                                                        region_name=self.region_name)
                monitorhook.serviceMonitor(self.tenant_name, newTenantService, 'create_service', True)

                # 创建服务依赖
                logger.debug("===> create service dependency!")
                self.create_dep_service(service_info, service_id, key_id_map)
                # 环境变量
                logger.debug("===> create service env!")
                self.copy_envs(service_info, newTenantService)
                # 端口信息
                logger.debug("===> create service port!")
                self.copy_ports(service_info, newTenantService)
                # 持久化目录
                logger.debug("===> create service volumn!")
                self.copy_volumes(service_info, newTenantService)

                dep_sids = []
                tsrs = TenantServiceRelation.objects.filter(service_id=newTenantService.service_id)
                for tsr in tsrs:
                    dep_sids.append(tsr.dep_service_id)

                baseService.create_region_service(newTenantService, self.tenant_name, self.region_name, self.nick_name,
                                                  dep_sids=json.dumps(dep_sids))
                monitorhook.serviceMonitor(self.nick_name, newTenantService, 'init_region_service', True)
                current_services.append(newTenantService)
            url_map = self.getServicePreviewUrls(current_services)
            logger.debug("===> url_map:{} ".format(url_map))
            # 处理原来安装的服务
            self.handleInstalledService(share_pk, group_id)

        except Exception as e:
            logger.exception(e)
            try:
                for service_id in current_service_ids:
                    regionClient.delete(self.region_name, service_id)
            except Exception as e:
                logger.exception(e)
                pass
            TenantServiceInfo.objects.filter(tenant_id=self.tenant_id, service_id__in=current_service_ids).delete()
            TenantServiceAuth.objects.filter(service_id__in=current_service_ids).delete()
            ServiceDomain.objects.filter(service_id__in=current_service_ids).delete()
            TenantServiceRelation.objects.filter(tenant_id=self.tenant_id, service_id__in=current_service_ids).delete()
            TenantServiceEnvVar.objects.filter(tenant_id=self.tenant_id, service_id__in=current_service_ids).delete()
            TenantServicesPort.objects.filter(tenant_id=self.tenant_id, service_id__in=current_service_ids).delete()
            TenantServiceVolume.objects.filter(service_id__in=current_service_ids).delete()

        return group_id, current_service_ids, url_map

    def getServicePreviewUrls(self, current_services):
        """
        获取grdemo的预览url
        :param current_services:
        :return:
        {"service_id":{"port":url}}
        """
        url_map = {}
        wild_domain = settings.WILD_DOMAINS[self.region_name]
        http_port_str = settings.WILD_PORTS[self.region_name]
        for service in current_services:
            logger.debug("====> service_id:{}".format(service.service_id))
            out_service_port_list = TenantServicesPort.objects.filter(service_id=service.service_id,
                                                                      is_outer_service=True, protocol='http')
            port_map = {}
            for ts_port in out_service_port_list:
                port = ts_port.container_port
                # preview_url = "http://" + port + ".{{serviceAlias}}.{{tenantName}}{{wild_domain}}{{http_port_str}}"
                preview_url = "http://{0}.{1}.{2}{3}:{4}".format(port, service.service_alias, self.tenant_name,
                                                                 wild_domain, http_port_str)
                port_map[str(port)] = preview_url
            url_map[service.service_cname] = port_map
        return url_map

    def handleInstalledService(self, share_pk, new_group_id):
        bsi_temp_list = BackServiceInstallTemp.objects.filter(share_pk=share_pk)
        try:
            # 如果服务组被安装过
            if bsi_temp_list:
                bsi_temp = bsi_temp_list[0]
                group_pk = bsi_temp.group_pk
                # 查询出原来安装的组
                pre_service_ids = ServiceGroupRelation.objects.filter(group_id=group_pk, tenant_id=self.tenant_id,
                                                                      region_name=self.region_name).values_list(
                    "service_id", flat=True)
                logger.debug("previous service ids {}".format(pre_service_ids))
                # 将服务安照依赖关系排序
                result = []
                service_list = TenantServiceInfo.objects.filter(service_id__in=pre_service_ids, tenant_id=self.tenant_id,
                                                                service_region=self.region_name)
                id_service_map = {}
                service_map = {s.service_id: s for s in service_list}
                for s_id in pre_service_ids:
                    dep_services = TenantServiceRelation.objects.filter(tenant_id=self.tenant_id, service_id=s_id)
                    if dep_services:
                        id_service_map[s_id] = [ds.dep_service_id for ds in dep_services]
                    else:
                        id_service_map[s_id] = []
                logger.debug(" service_map:{} ".format(service_map))
                service_ids = self.topological_sort(id_service_map)
                for id in service_ids:
                    result.append(service_map.get(id))
                result.reverse()
                # 删除服务
                logger.debug("delete previous services !")
                for service in result:
                    self.__deleteService(service)
                # 删除组
                ServiceGroup.objects.filter(ID=group_pk, region_name=self.region_name).delete()
                # 更新新的服务组
                BackServiceInstallTemp.objects.update(group_pk=new_group_id)
            else:
                # 创建grdemo的安装记录
                BackServiceInstallTemp.objects.create(share_pk=share_pk,group_pk=new_group_id,success=True)

        except Exception as e:
            logger.error("handle installed service error !")
            logger.exception(e)

    def __deleteService(self,service):
        try:
            logger.debug("service_id - {0} - service_name {1} ".format(service.service_id,service.service_cname))
            try:
                regionClient.delete(service.service_region, service.service_id)
            except Exception as e:
                success = False
                logger.error("region delete service error! ")
                logger.exception(e)

            TenantServiceInfo.objects.get(service_id=service.service_id).delete()
            # env/auth/domain/relationship/envVar/volume delete
            TenantServiceEnv.objects.filter(service_id=service.service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service.service_id).delete()
            ServiceDomain.objects.filter(service_id=service.service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service.service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service.service_id).delete()
            TenantServiceMountRelation.objects.filter(service_id=service.service_id).delete()
            TenantServicesPort.objects.filter(service_id=service.service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service.service_id).delete()
            ServiceGroupRelation.objects.filter(service_id=service.service_id,
                                                tenant_id=self.tenant_id).delete()
            ServiceAttachInfo.objects.filter(service_id=service.service_id).delete()
            ServiceCreateStep.objects.filter(service_id=service.service_id).delete()
            events = ServiceEvent.objects.filter(service_id=service.service_id)
            deleteEventID = []
            if events:
                for event in events:
                    deleteEventID.append(event.event_id)
            if len(deleteEventID) > 0:
                regionClient.deleteEventLog(service.service_region,
                                            json.dumps({"event_ids": deleteEventID}))

            ServiceEvent.objects.filter(service_id=service.service_id).delete()

            monitorhook.serviceMonitor(self.nick_name, service, 'app_delete', True)
        except Exception as e:
            logger.error("back service delete error!")
            logger.exception(e)