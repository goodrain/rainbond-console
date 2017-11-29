# -*- coding: utf8 -*-

from www.models import *
from www.monitorservice.monitorhook import MonitorHook
from www.region import RegionInfo

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


class ApplicationService(object):
    """
    应用服务接口，提供应用生命周期的所有操作
    """

    def get_service_by_id(self, service_id):
        try:
            return TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            return None


class ApplicationGroupService(object):
    def get_app_service_group_by_unique(self, group_key, group_version):
        try:
            return AppServiceGroup.objects.get(group_share_id=group_key, group_version=group_version)
        except AppServiceGroup.DoesNotExist:
            return None

    def get_service_by_id(self, service_id):
        try:
            return TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            return None

    def install_app_group(self, user, tenant, region_name, app_service_group):
        group = None
        installed_services = []
        try:
            # 根据分享组模板生成团队自己的应用组信息
            group = self.__create_group(tenant.tenant_id, region_name, app_service_group.group_share_alias)

            # 查询分享组中的服务ID
            service_id_list = ServiceGroupRelation.objects.filter(group_id=app_service_group.group_id).values_list(
                "service_id", flat=True)
            app_service_list = self.__get_published_service_info(app_service_group.ID)
            published_service_list = self.__getServiceModel(app_service_list, service_id_list)
            sorted_service = self.__sort_service(published_service_list)

            # 先生成服务的service_id
            key_id_map = {}
            for service_info in sorted_service:
                service_key = service_info.service_key
                service_id = make_uuid(service_key)
                key_id_map[service_key] = service_id

            for service_info in sorted_service:
                logger.debug("service_info.service_key: {}".format(service_info.service_key))
                service_id = key_id_map.get(service_info.service_key)
                service_alias = "gr" + service_id[-6:]

                new_tenant_service = baseService.create_service(service_id, tenant.tenant_id, service_alias,
                                                                service_info.service_name,
                                                                service_info,
                                                                user.user_id, region=region_name)
                ServiceGroupRelation.objects.create(service_id=service_id, group_id=group.pk,
                                                    tenant_id=tenant.tenant_id,
                                                    region_name=region_name)
                monitorhook.serviceMonitor(tenant.tenant_name, new_tenant_service, 'create_service', True)

                # 创建服务依赖
                logger.debug("===> create service dependency!")
                self.__create_dep_service(service_info, service_id, key_id_map, tenant.tenant_id, region_name)
                # 环境变量
                logger.debug("===> create service env!")
                self.__copy_envs(service_info, new_tenant_service, region_name, tenant.tenant_name)
                # 端口信息
                logger.debug("===> create service port!")
                self.__copy_ports(service_info, new_tenant_service)
                # 持久化目录
                logger.debug("===> create service volumn!")
                self.__copy_volumes(service_info, new_tenant_service)

                dep_sids = [tsr.dep_service_id for tsr in
                            TenantServiceRelation.objects.filter(service_id=new_tenant_service.service_id)]
                baseService.create_region_service(new_tenant_service, tenant.tenant_name, region_name, user.nick_name,
                                                  dep_sids=json.dumps(dep_sids))
                monitorhook.serviceMonitor(user.nick_name, new_tenant_service, 'init_region_service', True)
                installed_services.append(new_tenant_service)

            url_map = self.__get_service_preview_urls(installed_services, tenant.tenant_name, region_name)
            logger.debug("===> url_map:{} ".format(url_map))

            logger.info('install app [{0}-{1}] to group [{2}] succeed!'.format(app_service_group.group_share_alias,
                                                                               app_service_group.group_version,
                                                                               group.group_name))
            return group, installed_services, url_map
        except Exception as e:
            logger.error('install app [{0}-{1}] failed!'.format(app_service_group.group_share_alias,
                                                                app_service_group.group_version))
            logger.exception(e)
            self.__clear_install_context(group, installed_services, region_name, tenant.tenant_id)
            raise e

    def __clear_install_context(self, group, installed_services, region_name, tenant_id):
        if group:
            group.delete()

        installed_service_ids = [s.service_id for s in installed_services]
        try:
            for service_id in installed_services:
                regionClient.delete(region_name, service_id)
        except Exception as e:
            logger.exception(e)
            pass
        TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_id__in=installed_service_ids).delete()
        TenantServiceAuth.objects.filter(service_id__in=installed_service_ids).delete()
        ServiceDomain.objects.filter(service_id__in=installed_service_ids).delete()
        TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id__in=installed_service_ids).delete()
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id__in=installed_service_ids).delete()
        TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id__in=installed_service_ids).delete()
        TenantServiceVolume.objects.filter(service_id__in=installed_service_ids).delete()

    def __generator_group_name(self, group_name):
        return '_'.join([group_name, make_uuid()[-4:]])

    def __is_group_name_exist(self, group_name, tenant_id, region_name):
        return ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name,
                                           group_name=group_name).exists()

    def __create_group(self, tenant_id, region_name, group_name):
        """
        在指定团队数据中心生成应用组，如果组名存在则自动生成新组
        :return: 组ID
        """
        while True:
            if self.__is_group_name_exist(group_name, tenant_id, region_name):
                group_name = self.__generator_group_name(group_name)
            else:
                group = ServiceGroup.objects.create(tenant_id=tenant_id, region_name=region_name,
                                                    group_name=group_name)
                return group

    def __get_published_service_info(self, group_id):
        result = []
        pgsr_list = PublishedGroupServiceRelation.objects.filter(group_pk=group_id)
        for pgsr in pgsr_list:
            apps = AppService.objects.filter(service_key=pgsr.service_key, app_version=pgsr.version).order_by("-ID")
            if apps:
                result.append(apps[0])
            else:
                apps = AppService.objects.filter(service_key=pgsr.service_key).order_by("-ID")
                if apps:
                    result.append(apps[0])
        return result

    def __getServiceModel(self, app_service_list, service_id_list):
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

    def __topological_sort(self, graph):
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

    def __sort_service(self, publish_service_list):
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
        service_keys = self.__topological_sort(key_app_map)

        for key in service_keys:
            result.append(service_map.get(key))
        return result

    def __create_dep_service(self, service_info, service_id, key_id_map, tenant_id, region_name):
        app_relations = AppServiceRelation.objects.filter(service_key=service_info.service_key,
                                                          app_version=service_info.version)
        dep_service_ids = []
        for dep_app in app_relations:
            dep_service_id = key_id_map.get(dep_app.dep_service_key)
            dep_service_ids.append(dep_service_id)

        for dep_id in dep_service_ids:
            baseService.create_service_dependency(tenant_id, service_id, dep_id, region_name)
        logger.info("create service info for service_id{0} ".format(service_id))

    def __copy_ports(self, source_service, current_service):
        AppPorts = AppServicePort.objects.filter(service_key=current_service.service_key,
                                                 app_version=current_service.version)
        for port in AppPorts:
            baseService.addServicePort(current_service, source_service.is_init_accout,
                                       container_port=port.container_port, protocol=port.protocol,
                                       port_alias=port.port_alias,
                                       is_inner_service=port.is_inner_service, is_outer_service=port.is_outer_service)

    def __copy_envs(self, service_info, current_service, region_name, tenant_name):
        s = current_service
        envs = AppServiceEnv.objects.filter(service_key=service_info.service_key, app_version=service_info.version)
        outer_ports = AppServicePort.objects.filter(service_key=service_info.service_key,
                                                    app_version=service_info.version,
                                                    is_outer_service=True,
                                                    protocol='http')
        for env in envs:
            # 对需要特殊处理的应用增加额外的环境变量
            if env.attr_name in ('SITE_URL', 'TRUSTED_DOMAIN'):
                port = RegionInfo.region_port(region_name)
                domain = RegionInfo.region_domain(region_name)
                env.options = "direct_copy"
                if len(outer_ports) > 0:
                    env.attr_value = '{}.{}.{}{}:{}'.format(outer_ports[0].container_port,
                                                            current_service.serviceAlias, tenant_name,
                                                            domain, port)
                logger.debug("{} = {} options = {}".format(env.attr_name, env.attr_value, env.options))

            baseService.saveServiceEnvVar(s.tenant_id, s.service_id, env.container_port, env.name,
                                          env.attr_name, env.attr_value, env.is_change, env.scope)

    def __copy_volumes(self, source_service, tenant_service):
        volumes = AppServiceVolume.objects.filter(service_key=source_service.service_key,
                                                  app_version=source_service.version)
        for volume in volumes:
            baseService.add_volume_list(tenant_service, volume.volume_path)

    def __get_service_preview_urls(self, current_services, tenant_name, region_name):
        """
        获取grdemo的预览url
        :param current_services:
        :return:
        {"service_id":{"port":url}}
        """
        url_map = {}
        wild_domain = settings.WILD_DOMAINS[region_name]
        http_port_str = settings.WILD_PORTS[region_name]
        for service in current_services:
            logger.debug("====> service_id:{}".format(service.service_id))
            out_service_port_list = TenantServicesPort.objects.filter(service_id=service.service_id,
                                                                      is_outer_service=True, protocol='http')
            port_map = {}
            for ts_port in out_service_port_list:
                port = ts_port.container_port
                preview_url = "http://{0}.{1}.{2}{3}:{4}".format(port, service.service_alias, tenant_name,
                                                                 wild_domain, http_port_str)
                port_map[str(port)] = preview_url
            url_map[service.service_cname] = port_map
        return url_map

    def __deleteService(self, service):
        try:
            logger.debug("service_id - {0} - service_name {1} ".format(service.service_id, service.service_cname))
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