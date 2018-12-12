# -*- coding: utf8 -*-
from www.apiclient.regionapi import RegionInvokeApi
from www.models import ServiceGroup, ServiceInfo, ServiceGroupRelation, \
    AppServiceVolume, TenantServiceRelation, TenantServiceInfo, TenantServiceAuth, \
    ServiceDomain, TenantServiceEnvVar, TenantServicesPort, TenantServiceVolume, BackServiceInstallTemp, \
    TenantServiceEnv, TenantServiceMountRelation, ServiceAttachInfo, ServiceCreateStep, ServiceEvent, \
    Tenants
from www.monitorservice.monitorhook import MonitorHook


import logging
from django.conf import settings

from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid

logger = logging.getLogger('default')
baseService = BaseTenantService()
monitorhook = MonitorHook()
region_api = RegionInvokeApi()


class BackServiceInstall(object):
    def __init__(self):
        # 初始化grdemo的tenant_id
        self.tenant_id = "0622f5b7751f4c3c91f03e60a10a5e85"
        self.tenant_name = "grdemo"
        self.tenant = Tenants.objects.get(tenant_id=self.tenant_id)
        self.region_name = "ali-hz"
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

    def getServiceModel(self, app_service_list):
        published_service_list = []
        for app_service in app_service_list:
            service = ServiceInfo()
            service.service_key = app_service.service_key
            service.version = app_service.app_version
            service.publisher = app_service.publisher
            service.service_name = app_service.app_alias
            service.pic = app_service.logo
            service.info = app_service.info
            service.desc = app_service.desc
            service.status = app_service.status
            service.category = "app_publish"
            service.is_service = app_service.is_service
            service.is_web_service = app_service.is_web_service
            service.version = app_service.app_version
            service.update_version = app_service.update_version
            service.image = app_service.image
            service.slug = app_service.slug
            service.extend_method = app_service.extend_method
            service.cmd = app_service.cmd
            service.setting = ""
            service.env = app_service.env
            service.dependecy = ""
            service.min_node = app_service.min_node
            service.min_cpu = app_service.min_cpu
            service.min_memory = app_service.min_memory
            service.inner_port = app_service.inner_port
            service.volume_mount_path = app_service.volume_mount_path
            service.service_type = app_service.service_type
            service.is_init_accout = app_service.is_init_accout
            service.creater = app_service.creater
            service.namespace = app_service.namespace
            service.publish_type = "group"
            published_service_list.append(service)

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

    def copy_volumes(self, source_service, tenant_service):
        volumes = AppServiceVolume.objects.filter(service_key=source_service.service_key,
                                                  app_version=source_service.version)
        for volume in volumes:
            baseService.add_volume_list(tenant_service, volume.volume_path)

    def get_service_access_url(self, service):
        wild_domain = settings.WILD_DOMAINS[self.region_name]
        http_port_str = settings.WILD_PORTS[self.region_name]
        out_service_port_list = TenantServicesPort.objects.filter(service_id=service.service_id,
                                                                  is_outer_service=True, protocol='http')
        service_key_url_map = {}
        if out_service_port_list:
            ts_port = out_service_port_list[0]
            port = ts_port.container_port
            preview_url = "http://{0}.{1}.{2}{3}:{4}".format(port, service.service_alias, self.tenant_name,
                                                             wild_domain, http_port_str)
            service_key_url_map[service.service_key] = preview_url
        return service_key_url_map

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

    def __deleteService(self, service):
        try:
            logger.debug("service_id - {0} - service_name {1} ".format(service.service_id,service.service_cname))
            try:
                region_api.delete_service(self.region_name, self.tenant_name, service.service_alias,self.tenant.enterprise_id)
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

            ServiceEvent.objects.filter(service_id=service.service_id).delete()

            monitorhook.serviceMonitor(self.nick_name, service, 'app_delete', True)
        except Exception as e:
            logger.error("back service delete error!")
            logger.exception(e)