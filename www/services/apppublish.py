# -*- coding: utf8 -*-
import json
import logging

from www.apiclient.marketclient import MarketOpenAPI
from www.models.main import TenantServicesPort, TenantServiceRelation, TenantServiceInfo, \
    TenantServiceEnvVar, TenantServiceVolume, ServiceGroupRelation
from www.models.service_publish import ServiceExtendMethod, PublishedGroupServiceRelation

logger = logging.getLogger('default')


class PublishAppService(object):
    """组件发布数据获取接口"""

    def get_service_ports_by_ids(self, service_ids):
        """
        根据多个组件ID查询组件的端口信息
        :param service_ids: 组件ID列表
        :return: {"service_id":TenantServicesPort[object]}
        """
        port_list = TenantServicesPort.objects.filter(service_id__in=service_ids)
        service_port_map = {}
        for port in port_list:
            service_id = port.service_id
            tmp_list = []
            if service_id in list(service_port_map.keys()):
                tmp_list = service_port_map.get(service_id)
            tmp_list.append(port)
            service_port_map[service_id] = tmp_list
        return service_port_map

    def get_service_dependencys_by_ids(self, service_ids):
        """
        根据多个组件ID查询组件的依赖组件信息
        :param service_ids:组件ID列表
        :return: {"service_id":TenantServiceInfo[object]}
        """
        relation_list = TenantServiceRelation.objects.filter(service_id__in=service_ids)
        dep_service_map = {}
        for dep_service in relation_list:
            service_id = dep_service.service_id
            tmp_list = []
            if service_id in list(dep_service_map.keys()):
                tmp_list = dep_service_map.get(service_id)
            dep_service_info = TenantServiceInfo.objects.filter(service_id=dep_service.dep_service_id)[0]
            tmp_list.append(dep_service_info)
            dep_service_map[service_id] = tmp_list
        return dep_service_map

    def get_service_env_by_ids(self, service_ids):
        """
        获取组件env
        :param service_ids: 组件ID列表
        :return: 可修改的环境变量service_env_change_map，不可修改的环境变量service_env_nochange_map
        """
        env_list = TenantServiceEnvVar.objects.filter(service_id__in=service_ids, container_port__lte=0)
        env_change_list = [x for x in env_list if x.is_change]
        env_nochange_list = [x for x in env_list if not x.is_change]
        service_env_change_map = {}
        for env in env_change_list:
            service_id = env.service_id
            tmp_list = []
            if service_id in list(service_env_change_map.keys()):
                tmp_list = service_env_change_map.get(service_id)
            tmp_list.append(env)
            service_env_change_map[service_id] = tmp_list
        service_env_nochange_map = {}
        for env in env_nochange_list:
            service_id = env.service_id
            tmp_list = []
            if service_id in list(service_env_nochange_map.keys()):
                tmp_list = service_env_nochange_map.get(service_id)
            tmp_list.append(env)
            service_env_nochange_map[service_id] = tmp_list
        return service_env_change_map, service_env_nochange_map

    def get_service_volume_by_ids(self, service_ids):
        volume_list = TenantServiceVolume.objects.filter(service_id__in=service_ids)
        service_volume_map = {}
        for volume in volume_list:
            service_id = volume.service_id
            tmp_list = []
            if service_id in list(service_volume_map.keys()):
                tmp_list = service_volume_map.get(service_id)
            tmp_list.append(volume)
            service_volume_map[service_id] = tmp_list
        return service_volume_map

    def add_app_extend_info(self, service, service_key, app_version):

        logger.debug(
            "group.publish",
            'group.share.service. now add group shared service extend method for service {0} ok'.format(service.service_id))
        count = ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version).count()
        if count == 0:
            extend_method = ServiceExtendMethod(
                service_key=service_key,
                app_version=app_version,
                min_node=service.min_node,
                max_node=20,
                step_node=1,
                min_memory=service.min_memory,
                max_memory=65536,
                step_memory=128,
                is_restart=False)
            extend_method.save()
        else:
            ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version) \
                .update(min_node=service.min_node, min_memory=service.min_memory)

    def get_app_service_extend_method(self, service_key, app_version):
        return ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version)

    def update_or_create_group_service_relation(self, app_service_map, app_service_group):
        for s_id, app in list(app_service_map.items()):
            pgsr_list = PublishedGroupServiceRelation.objects.filter(group_pk=app_service_group.ID, service_id=s_id)
            if not pgsr_list:
                PublishedGroupServiceRelation.objects.create(
                    group_pk=app_service_group.ID, service_id=s_id, service_key=app.service_key, version=app.app_version)
            else:
                PublishedGroupServiceRelation.objects.filter(
                    group_pk=app_service_group.ID, service_id=s_id).update(
                        service_key=app.service_key, version=app.app_version)

    def delete_group_service_relation_by_group_pk(self, group_pk):
        PublishedGroupServiceRelation.objects.filter(group_pk=group_pk).delete()

    def __send_all_group_data(self, tenant, data):
        logger.debug("GROUP DATA START".center(90, "-"))
        logger.debug(json.dumps(data))
        logger.debug("GROUP DATA START".center(90, "-"))
        appClient = MarketOpenAPI()
        appClient.publish_all_service_group_data(tenant.tenant_id, data)

    def __get_tenant_group_service_by_group_id(self, tenant, region, group_id):
        """
        获取租户指定的组下的所有组件
        """
        svc_relations = ServiceGroupRelation.objects.filter(tenant_id=tenant.tenant_id, group_id=group_id, region_name=region)
        if not svc_relations:
            return list()

        svc_ids = [svc_rel.service_id for svc_rel in svc_relations]
        return TenantServiceInfo.objects.filter(service_id__in=svc_ids)
