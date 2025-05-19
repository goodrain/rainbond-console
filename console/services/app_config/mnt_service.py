# -*- coding: utf8 -*-
"""
  Created on 18/1/19.
"""
import copy
import logging

from console.enum.component_enum import is_state
from console.exception.main import ErrDepVolumeNotFound
from console.repositories.app import service_repo
from console.repositories.app_config import mnt_repo, volume_repo
from console.repositories.group import group_repo, group_service_relation_repo
from console.services.app_config.volume_service import AppVolumeService
from goodrain_web.tools import JuncheePaginator
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
volume_service = AppVolumeService()
region_api = RegionInvokeApi()


class AppMntService(object):
    SHARE = 'share-file'
    CONFIG = 'config-file'
    LOCAL = 'local'
    TMPFS = 'memoryfs'

    def get_service_mnt_details_byid(self, dep_vol_data):
        dep_vol_list = list()
        for dep_vol in dep_vol_data:
            dep_vol_dict = dict()
            dep_vol_dict["本地挂载配置文件路径"] = dep_vol["path"]
            mnt_list = volume_repo.get_service_volume_by_id(id=dep_vol["id"])
            dep_vol_dict["配置文件名称"] = mnt_list.volume_name
            dep_vol_dict["目标挂载配置文件路径"] = mnt_list.volume_path
            dep_service = service_repo.get_service_by_service_id(mnt_list.service_id)
            dep_vol_dict["所属组件"] = dep_service.service_cname
            gs_rel = group_service_relation_repo.get_group_by_service_id(dep_service.service_id)
            group = None
            if gs_rel:
                group = group_repo.get_group_by_pk(dep_service.tenant_id, dep_service.service_region, gs_rel.group_id)
            dep_vol_dict["组件所属应用"] = group.group_name if group else '未分组'
            dep_vol_list.append(dep_vol_dict)
        return dep_vol_list


    def get_service_mnt_details(self, tenant, service, volume_types, page=1, page_size=20):

        all_mnt_relations = mnt_repo.get_service_mnts_filter_volume_type(tenant.tenant_id, service.service_id, volume_types)
        total = len(all_mnt_relations)
        mnt_paginator = JuncheePaginator(all_mnt_relations, int(page_size))
        mnt_relations = mnt_paginator.page(page)
        mounted_dependencies = []
        if mnt_relations:
            for mount in mnt_relations:
                dep_service = service_repo.get_service_by_service_id(mount.dep_service_id)
                if dep_service:
                    gs_rel = group_service_relation_repo.get_group_by_service_id(dep_service.service_id)
                    group = None
                    if gs_rel:
                        group = group_repo.get_group_by_pk(tenant.tenant_id, service.service_region, gs_rel.group_id)
                    dep_volume = volume_repo.get_service_volume_by_name(dep_service.service_id, mount.mnt_name)
                    if dep_volume:
                        mounted_dependencies.append({
                            "local_vol_path": mount.mnt_dir,
                            "dep_vol_name": dep_volume.volume_name,
                            "dep_vol_path": dep_volume.volume_path,
                            "dep_vol_type": dep_volume.volume_type,
                            "dep_app_name": dep_service.service_cname,
                            "dep_app_group": group.group_name if group else '未分组',
                            "dep_vol_id": dep_volume.ID,
                            "dep_group_id": group.ID if group else -1,
                            "dep_app_alias": dep_service.service_alias
                        })
        return mounted_dependencies, total

    def get_service_unmount_volume_list(self, tenant, service, service_ids, page, page_size, is_config, dep_app_group,
                                        config_name):
        """
        1. 获取租户下其他所有组件列表，方便后续进行名称的冗余
        2. 获取其他组件的所有可共享的存储
        3. 获取已经使用的存储，方便后续过滤
        4. 遍历存储，组装信息
        """

        for serviceID in service_ids:
            if serviceID == service.service_id:
                service_ids.remove(serviceID)
        services = service_repo.get_services_by_service_ids(service_ids)
        state_services = []  # 有状态组件
        for svc in services:
            if is_state(svc.extend_method):
                state_services.append(svc)
        state_service_ids = [svc.service_id for svc in state_services]

        current_tenant_services_id = service_ids
        # 已挂载的组件路径
        mounted = mnt_repo.get_service_mnts(tenant.tenant_id, service.service_id)
        mounted_ids = [mnt.volume_id for mnt in mounted]
        # 当前未被挂载的共享路径
        service_volumes = []
        # 配置文件无论组件是否是共享存储都可以共享，只需过滤掉已经挂载的存储；其他存储类型则需要考虑排除有状态组件的存储
        if is_config:
            service_volumes = volume_repo.get_services_volumes(current_tenant_services_id).filter(
                volume_type=self.CONFIG) \
                .exclude(ID__in=mounted_ids)
        else:
            service_volumes = volume_repo.get_services_volumes(current_tenant_services_id).filter(
                access_mode="RWX") \
                .exclude(ID__in=mounted_ids).exclude(service_id__in=state_service_ids).exclude(volume_type=self.CONFIG).exclude(volume_type="local-path")
        # TODO 使用函数进行存储的排查，确定哪些存储不可以进行共享，哪些存储可以共享，而不是现在这样简单的提供一个self.SHARE

        total = len(service_volumes)
        volume_paginator = JuncheePaginator(service_volumes, int(page_size))
        page_volumes = volume_paginator.page(page)
        un_mount_dependencies = []
        for volume in page_volumes:
            gs_rel = group_service_relation_repo.get_group_by_service_id(volume.service_id)
            group = group_repo.get_group_by_pk(tenant.tenant_id, service.service_region, gs_rel.group_id)
            group_name = group.group_name if group else '未分组'
            if (dep_app_group == "" or dep_app_group == group_name) and (config_name == "" or config_name in volume.volume_name
                                                                         or config_name in volume.volume_path):
                un_mount_dependencies.append({
                    "dep_app_name": services.get(service_id=volume.service_id).service_cname,
                    "dep_app_group": group_name,
                    "dep_vol_name": volume.volume_name,
                    "dep_vol_path": volume.volume_path,
                    "dep_vol_type": volume.volume_type,
                    "dep_vol_id": volume.ID,
                    "dep_group_id": group.ID if group else -1,
                    "dep_app_alias": services.get(service_id=volume.service_id).service_alias
                })
        return un_mount_dependencies, total

    def get_service_unmnt_details(self, tenant, service, service_ids, page, page_size, q):

        services = service_repo.get_services_by_service_ids(service_ids)
        current_tenant_services_id = service_ids
        # 已挂载的组件路径
        dep_mnts = mnt_repo.get_service_mnts(tenant.tenant_id, service.service_id)
        dep_volume_ids = [dep_mnt.volume_id for dep_mnt in dep_mnts]
        # 当前未被挂载的共享路径
        service_volumes = volume_repo.get_services_volumes(current_tenant_services_id) \
            .filter(volume_type__in=[self.SHARE, self.CONFIG]) \
            .exclude(service_id=service.service_id) \
            .exclude(ID__in=dep_volume_ids).filter(q)
        # 只展示无状态的组件(有状态组件的存储类型为config-file也可)
        volumes = list(service_volumes)
        copy_volumes = copy.copy(volumes)
        for volume in copy_volumes:
            service_obj = service_repo.get_service_by_service_id(volume.service_id)
            if service_obj:
                if is_state(service_obj.extend_method):
                    if volume.volume_type != "config-file":
                        volumes.remove(volume)
        total = len(volumes)
        volume_paginator = JuncheePaginator(volumes, int(page_size))
        page_volumes = volume_paginator.page(page)
        un_mount_dependencies = []
        for volume in page_volumes:
            gs_rel = group_service_relation_repo.get_group_by_service_id(volume.service_id)
            group = None
            if gs_rel:
                group = group_repo.get_group_by_pk(tenant.tenant_id, service.service_region, gs_rel.group_id)
            un_mount_dependencies.append({
                "dep_app_name": services.get(service_id=volume.service_id).service_cname,
                "dep_app_group": group.group_name if group else '未分组',
                "dep_vol_name": volume.volume_name,
                "dep_vol_path": volume.volume_path,
                "dep_vol_type": volume.volume_type,
                "dep_vol_id": volume.ID,
                "dep_group_id": group.ID if group else -1,
                "dep_app_alias": services.get(service_id=volume.service_id).service_alias
            })
        return un_mount_dependencies, total

    def batch_mnt_serivce_volume(self, tenant, service, dep_vol_data, user_name=''):
        local_path = []
        tenant_service_volumes = volume_service.get_service_volumes(tenant=tenant, service=service)
        local_path = [l_path["volume_path"] for l_path in tenant_service_volumes]
        for dep_vol in dep_vol_data:
            volume_service.check_volume_path(service, dep_vol["path"], local_path=local_path)
        for dep_vol in dep_vol_data:
            dep_vol_id = dep_vol['id']
            source_path = dep_vol['path'].strip()
            dep_volume = volume_repo.get_service_volume_by_pk(dep_vol_id)
            try:
                self.add_service_mnt_relation(tenant, service, source_path, dep_volume, user_name)
            except Exception as e:
                logger.exception(e)

    def create_service_volume(self, tenant, service, dep_vol):
        """
        raise ErrInvalidVolume
        raise ErrDepVolumeNotFound
        """
        tenant_service_volumes = volume_service.get_service_volumes(tenant, service)
        local_path = [l_path["volume_path"] for l_path in tenant_service_volumes]
        volume_service.check_volume_path(service, dep_vol["path"], local_path=local_path)

        dep_volume = volume_repo.get_service_volume_by_name(dep_vol["service_id"], dep_vol["volume_name"])
        if not dep_volume:
            raise ErrDepVolumeNotFound(dep_vol["service_id"], dep_vol["volume_name"])

        source_path = dep_vol['path'].strip()
        return mnt_repo.add_service_mnt_relation(tenant.tenant_id, service.service_id, dep_volume.service_id,
                                                 dep_volume.volume_name, source_path)

    def add_service_mnt_relation(self, tenant, service, source_path, dep_volume, user_name=''):
        if not dep_volume:
            return
        if service.create_status == "complete":
            if dep_volume.volume_type != "config-file":
                data = {
                    "depend_service_id": dep_volume.service_id,
                    "volume_name": dep_volume.volume_name,
                    "volume_path": source_path,
                    "enterprise_id": tenant.enterprise_id,
                    "volume_type": dep_volume.volume_type
                }
            else:
                config_file = volume_repo.get_service_config_file(dep_volume)
                data = {
                    "depend_service_id": dep_volume.service_id,
                    "volume_name": dep_volume.volume_name,
                    "volume_path": source_path,
                    "volume_type": dep_volume.volume_type,
                    "file_content": config_file.file_content,
                    "enterprise_id": tenant.enterprise_id
                }
            data["operator"] = user_name
            res, body = region_api.add_service_dep_volumes(service.service_region, tenant.tenant_name, service.service_alias,
                                                           data)
            logger.debug("add service mnt info res: {0}, body:{1}".format(res, body))

        mnt_relation = mnt_repo.add_service_mnt_relation(tenant.tenant_id, service.service_id, dep_volume.service_id,
                                                         dep_volume.volume_name, source_path)
        logger.debug("mnt service {0} to service {1} on dir {2}".format(mnt_relation.service_id, mnt_relation.dep_service_id,
                                                                        mnt_relation.mnt_dir))

    def delete_service_mnt_relation(self, tenant, service, dep_vol_id, user_name=''):
        dep_volume = volume_repo.get_service_volume_by_pk(dep_vol_id)

        try:
            if service.create_status == "complete":
                data = {
                    "depend_service_id": dep_volume.service_id,
                    "volume_name": dep_volume.volume_name,
                    "enterprise_id": tenant.tenant_name,
                    "operator": user_name
                }
                res, body = region_api.delete_service_dep_volumes(service.service_region, tenant.tenant_name,
                                                                  service.service_alias, data)
                logger.debug("delete service mnt info res:{0}, body {1}".format(res, body))
            mnt_repo.delete_mnt_relation(service.service_id, dep_volume.service_id, dep_volume.volume_name)

        except region_api.CallApiError as e:
            logger.exception(e)
            if e.status == 404:
                logger.debug('service mnt relation not in region then delete rel directly in console')
                mnt_repo.delete_mnt_relation(service.service_id, dep_volume.service_id, dep_volume.volume_name)
        return 200, "success"

    def get_volume_dependent(self, tenant, service):
        mnts = mnt_repo.get_by_dep_service_id(tenant.tenant_id, service.service_id)
        if not mnts:
            return None

        service_ids = [mnt.service_id for mnt in mnts]
        services = service_repo.get_services_by_service_ids(service_ids)
        # to dict
        id_to_services = {}
        for svc in services:
            if not id_to_services.get(svc.service_id, None):
                id_to_services[svc.service_id] = [svc]
                continue
            id_to_services[svc.service_id].append(svc)

        result = []
        for mnt in mnts:
            # get volume
            vol = volume_repo.get_service_volume_by_name(service.service_id, mnt.mnt_name)
            if not vol:
                continue
            # services that depend on this volume
            services_dep_vol = id_to_services[mnt.service_id]
            for svc in services_dep_vol:
                result.append({
                    "volume_name": vol.volume_name,
                    "service_name": svc.service_cname,
                    "service_alias": svc.service_alias,
                })

        return result
