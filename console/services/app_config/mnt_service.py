# -*- coding: utf8 -*-
"""
  Created on 18/1/19.
"""
from console.repositories.app import service_repo
from console.repositories.group import group_service_relation_repo, group_repo
from goodrain_web.tools import JuncheePaginator
from console.repositories.app_config import volume_repo, mnt_repo
from console.services.app_config.volume_service import AppVolumeService

import logging

from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
volume_service = AppVolumeService()
region_api = RegionInvokeApi()


class AppMntService(object):
    SHARE = 'share-file'
    LOCAL = 'local'
    TMPFS = 'memoryfs'

    def get_service_mnt_details(self, tenant, service, page=1, page_size=20):

        all_mnt_relations = mnt_repo.get_service_mnts(tenant.tenant_id, service.service_id)
        total = len(all_mnt_relations)
        mnt_paginator = JuncheePaginator(all_mnt_relations, int(page_size))
        mnt_relations = mnt_paginator.page(page)
        mounted_dependencies = []
        if mnt_relations:
            for mount in mnt_relations:
                dep_service = service_repo.get_service_by_service_id(mount.dep_service_id)
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

    def get_service_unmnt_details(self, tenant, service, service_ids, page, page_size):

        services = service_repo.get_services_by_service_ids(*service_ids)
        current_tenant_services_id = service_ids
        # 已挂载的服务路径
        dep_mnt_names = mnt_repo.get_service_mnts(tenant.tenant_id, service.service_id).values_list('mnt_name',
                                                                                                    flat=True)
        # 当前未被挂载的共享路径
        volumes = volume_repo.get_services_volumes(current_tenant_services_id).filter(volume_type=self.SHARE).exclude(
            service_id=service.service_id).exclude(volume_name__in=dep_mnt_names)
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
        for dep_vol in dep_vol_data:
            code, msg = volume_service.check_volume_path(service, dep_vol["path"])
            if code != 200:
                return code, msg
        for dep_vol in dep_vol_data:
            dep_vol_id = dep_vol['id']
            source_path = dep_vol['path']
            dep_volume = volume_repo.get_service_volume_by_pk(dep_vol_id)
            try:
                code, msg = self.add_service_mnt_relation(tenant, service, source_path, dep_volume)
            except Exception as e:
                logger.exception(e)
                code, msg = 500, "添加异常"
            if code != 200:
                return code, msg
        return 200, "success"

    def add_service_mnt_relation(self, tenant, service, source_path, dep_volume):
        if service.create_status == "complete":
            data = {
                "depend_service_id": dep_volume.service_id,
                "volume_name": dep_volume.volume_name,
                "volume_path": source_path,
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
