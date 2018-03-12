# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
import re

from console.constants import AppConstants
from console.repositories.app_config import volume_repo, mnt_repo

from www.apiclient.regionapi import RegionInvokeApi
import logging
from console.utils.urlutil import is_path_legal

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppVolumeService(object):
    SYSDIRS = ["/", "/bin", "/boot", "/dev", "/etc", "/home",
               "/lib", "/lib64", "/opt", "/proc", "/root", "/sbin",
               "/srv", "/sys", "/tmp", "/usr", "/var",
               "/usr/local", "/usr/sbin", "/usr/bin",
               ]

    def get_service_volumes(self, tenant, service):
        return volume_repo.get_service_volumes(service.service_id)

    def check_volume_name(self, service_id, volume_name):

        zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
        match = zhPattern.search(volume_name.decode('utf-8'))
        if match:
            return 400, u"持久化名称不能包含中文"
        
        volume = volume_repo.get_service_volume_by_name(service_id, volume_name)

        if volume:
            return 412, u"持久化名称{0}已存在".format(volume_name)
        else:
            return 200, u"success"

    def check_volume_path(self, service, volume_path):
        volume = volume_repo.get_service_volume_by_path(service.service_id, volume_path)
        if volume:
            return 412, u"持久化路径 {0} 已存在".format(volume_path)
        if service.service_source == AppConstants.SOURCE_CODE:
            if volume_path == "/app" or volume_path.startswith("/app/"):
                return 409, u"源码应用不能挂载/app目录"
        if service.image != "goodrain.me/runner":
            if not volume_path.startswith("/"):
                return 400, u"路径需要以/(斜杠)开头"
            if volume_path in self.SYSDIRS:
                return 412, u"路径{0}为系统路径".format(volume_path)
        else:
            if not is_path_legal(volume_path):
                return 412, u"请输入符合规范的路径（如：/app/volumes ）"
        all_volumes = volume_repo.get_service_volumes(service.service_id).values("volume_path")
        for path in list(all_volumes):
            # volume_path不能重复

            if path["volume_path"].startswith(volume_path + "/"):
                return 412, u"已存在以{0}开头的路径".format(path["volume_path"])
            if volume_path.startswith(path["volume_path"] + "/"):
                return 412, u"已存在以{0}开头的路径".format(volume_path)

        return 200, u"success"

    def add_service_volume(self, tenant, service, volume_path, volume_type, volume_name):
        code, msg = self.check_volume_name(service.service_id, volume_name)
        if code != 200:
            return code, msg, None
        code, msg = self.check_volume_path(service, volume_path)
        if code != 200:
            return code, msg, None
        host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant.tenant_id, service.service_id, volume_path)
        volume_data = {"service_id": service.service_id, "category": service.category, "host_path": host_path,
                       "volume_type": volume_type, "volume_path": volume_path, "volume_name": volume_name}
        # region端添加数据
        if service.create_status == "complete":
            data = {
                "category": service.category,
                "volume_name": volume_name,
                "volume_path": volume_path,
                "volume_type": volume_type,
                "enterprise_id": tenant.enterprise_id
            }
            res, body = region_api.add_service_volumes(
                service.service_region, tenant.tenant_name, service.service_alias, data
            )
            logger.debug(body)

        volume = volume_repo.add_service_volume(**volume_data)
        return 200, "success", volume

    def delete_service_volume_by_id(self, tenant, service, volume_id):
        volume = volume_repo.get_service_volume_by_pk(volume_id)
        if not volume:
            return 404, u"需要删除的路径不存在", None
        if volume.volume_type == volume.SHARE:
            # 判断当前共享目录是否被使用
            mnt = mnt_repo.get_mnt_by_dep_id_and_mntname(service.service_id, volume.volume_name)
            if mnt:
                return 403, u"当前路径被共享,无法上传", None
        if service.create_status == "complete":
            res, body = region_api.delete_service_volumes(
                service.service_region, tenant.tenant_name, service.service_alias, volume.volume_name,
                tenant.enterprise_id
            )
            logger.debug(
                "service {0} delete volume {1}, result {2}".format(service.service_cname, volume.volume_name, body))

        volume_repo.delete_volume_by_id(volume_id)
        return 200, u"success", volume

    def delete_service_volumes(self, service):
        volume_repo.delete_service_volumes(service.service_id)

    def delete_region_volumes(self, tenant, service):
        volumes = volume_repo.get_service_volumes(service.service_id)
        for volume in volumes:
            try:
                res, body = region_api.delete_service_volumes(
                    service.service_region, tenant.tenant_name, service.service_alias, volume.volume_name,
                    tenant.enterprise_id
                )
            except Exception as e:
                logger.exception(e)