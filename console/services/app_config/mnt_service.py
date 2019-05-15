# -*- coding: utf8 -*-
"""
  Created on 18/1/19.
"""
import logging

from console.exception.main import ErrDepVolumeNotFound
from console.exception.main import ErrInvalidVolume
from console.repositories.app import service_repo
from console.repositories.app_config import mnt_repo
from console.repositories.app_config import volume_repo
from console.repositories.group import group_repo
from console.repositories.group import group_service_relation_repo
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

    def get_service_mnt_details(self, tenant, service, volume_type, page=1, page_size=20):

        all_mnt_relations = mnt_repo.get_service_mnts_filter_volume_type(
            tenant.tenant_id,
            service.service_id,
            volume_type
        )
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

    def get_service_unmnt_details(self, tenant, service, service_ids, page, page_size, q):

        services = service_repo.get_services_by_service_ids(service_ids)
        current_tenant_services_id = service_ids
        # 已挂载的服务路径
        dep_mnt_names = mnt_repo.get_service_mnts(tenant.tenant_id, service.service_id).values_list('mnt_name',
                                                                                                    flat=True)
        # 当前未被挂载的共享路径
        service_volumes = volume_repo.get_services_volumes(current_tenant_services_id) \
            .filter(volume_type__in=[self.SHARE, self.CONFIG]) \
            .exclude(service_id=service.service_id) \
            .exclude(volume_name__in=dep_mnt_names).filter(q)
        # 只展示无状态的服务组件(有状态服务的存储类型为config-file也可)
        volumes = list(service_volumes)
        for volume in volumes:
            service_obj = service_repo.get_service_by_service_id(volume.service_id)
            if service_obj:
                if service_obj.extend_method != "stateless" and volume.volume_type != "config-file":
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

    def batch_mnt_serivce_volume(self, tenant, service, dep_vol_data):
        local_path = []
        tenant_service_volumes = volume_service.get_service_volumes(tenant=tenant, service=service)
        local_path = [l_path.volume_path for l_path in tenant_service_volumes]
        for dep_vol in dep_vol_data:
            code, msg = volume_service.check_volume_path(service, dep_vol["path"], local_path=local_path)
            if code != 200:
                return code, msg
        for dep_vol in dep_vol_data:
            dep_vol_id = dep_vol['id']
            source_path = dep_vol['path'].strip()
            dep_volume = volume_repo.get_service_volume_by_pk(dep_vol_id)
            try:
                code, msg = self.add_service_mnt_relation(tenant, service, source_path, dep_volume)
            except Exception as e:
                logger.exception(e)
                code, msg = 500, "添加异常"
            if code != 200:
                return code, msg
        return 200, "success"

    def create_service_volume(self, tenant, service, dep_vol):
        """
        raise ErrInvalidVolume
        raise ErrDepVolumeNotFound
        """
        tenant_service_volumes = volume_service.get_service_volumes(tenant, service)
        local_path = [l_path.volume_path for l_path in tenant_service_volumes]
        code, msg = volume_service.check_volume_path(service, dep_vol["path"], local_path=local_path)
        if code != 200:
            logger.debug("Service id: {0}; ingore mnt; msg: {1}".format(service.service_id, msg))
            raise ErrInvalidVolume(msg)

        dep_volume = volume_repo.get_service_volume_by_name(dep_vol["service_id"],
                                                            dep_vol["volume_name"])
        if not dep_volume:
            raise ErrDepVolumeNotFound(dep_vol["service_id"], dep_vol["volume_name"])

        source_path = dep_vol['path'].strip()
        return mnt_repo.add_service_mnt_relation(tenant.tenant_id, service.service_id,
                                                 dep_volume.service_id,
                                                 dep_volume.volume_name, source_path)

    def add_service_mnt_relation(self, tenant, service, source_path, dep_volume):
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
                config_file = volume_repo.get_service_config_file(dep_volume.ID)
                data = {
                    "depend_service_id": dep_volume.service_id,
                    "volume_name": dep_volume.volume_name,
                    "volume_path": source_path,
                    "volume_type": dep_volume.volume_type,
                    "file_content": config_file.file_content,
                    "enterprise_id": tenant.enterprise_id
                }
            res, body = region_api.add_service_dep_volumes(
                service.service_region, tenant.tenant_name, service.service_alias, data
            )
            logger.debug("add service mnt info res: {0}, body:{1}".format(res, body))

        mnt_relation = mnt_repo.add_service_mnt_relation(tenant.tenant_id, service.service_id,
                                                         dep_volume.service_id,
                                                         dep_volume.volume_name, source_path)
        logger.debug(
            "mnt service {0} to service {1} on dir {2}".format(mnt_relation.service_id, mnt_relation.dep_service_id,
                                                               mnt_relation.mnt_dir))
        return 200, "success"

    def delete_service_mnt_relation(self, tenant, service, dep_vol_id):
        dep_volume = volume_repo.get_service_volume_by_pk(dep_vol_id)

        try:
            if service.create_status == "complete":
                data = {
                    "depend_service_id": dep_volume.service_id,
                    "volume_name": dep_volume.volume_name,
                    "enterprise_id": tenant.tenant_name
                }
                res, body = region_api.delete_service_dep_volumes(
                    service.service_region, tenant.tenant_name, service.service_alias, data
                )
                logger.debug("delete service mnt info res:{0}, body {1}".format(res, body))
            mnt_repo.delete_mnt_relation(service.service_id, dep_volume.service_id, dep_volume.volume_name)

        except region_api.CallApiError as e:
            logger.exception(e)
            if e.status == 404:
                logger.debug('service mnt relation not in region then delete rel directly in console')
                mnt_repo.delete_mnt_relation(service.service_id, dep_volume.service_id, dep_volume.volume_name)
        return 200, "success"
