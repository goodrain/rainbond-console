# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import datetime
import logging
from typing import Optional, Tuple

from django.db.models import QuerySet
from django.forms import model_to_dict

from console.repositories.plugin import plugin_version_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants
from www.models.plugin import PluginBuildVersion

logger = logging.getLogger("default")
region_api = RegionInvokeApi()

REGION_BUILD_STATUS_MAP = {
    "failure": "build_fail",
    "complete": "build_success",
    "building": "building",
    "timeout": "time_out",
}


class PluginBuildVersionService(object):
    def create_build_version(self,
                             region: str,
                             plugin_id: str,
                             tenant_id: str,
                             user_id: str,
                             update_info: str,
                             build_status: str,
                             min_memory: int,
                             build_cmd: str = "",
                             image_tag: str = "latest",
                             code_version: str = "master",
                             build_version: Optional[str] = None,
                             min_cpu: Optional[int] = None) -> PluginBuildVersion:
        """创建插件版本信息"""
        if min_cpu is None or type(min_cpu) != int:
            min_cpu = 0
        if not build_version:
            build_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        build_version_params = {
            "plugin_id": plugin_id,
            "tenant_id": tenant_id,
            "region": region,
            "user_id": user_id,
            "update_info": update_info,
            "build_version": build_version,
            "build_status": build_status,
            "min_memory": min_memory,
            "min_cpu": min_cpu,
            "build_cmd": build_cmd,
            "image_tag": image_tag,
            "code_version": code_version,
        }
        return plugin_version_repo.create_plugin_build_version(**build_version_params)

    def delete_build_version_by_id_and_version(self, tenant_id: str, plugin_id: str, build_version: str,
                                               force: bool = False) -> Tuple[int, str]:
        plugin_build_version = plugin_version_repo.get_by_id_and_version(tenant_id, plugin_id, build_version)
        if not plugin_build_version:
            return 404, "插件不存在"
        if not force:
            count_of_version = plugin_version_repo.get_plugin_versions(tenant_id, plugin_id).count()
            if count_of_version == 1:
                return 409, "至少保留插件的一个版本"
        plugin_version_repo.delete_build_version(tenant_id, plugin_id, build_version)
        return 200, "删除成功"

    def get_plugin_versions(self, tenant_id: str, plugin_id: str) -> QuerySet:
        return plugin_version_repo.get_plugin_versions(tenant_id, plugin_id)

    def get_newest_plugin_version(self, tenant_id: str, plugin_id: str) -> Optional[PluginBuildVersion]:
        pbvs = plugin_version_repo.get_plugin_versions(tenant_id, plugin_id)
        if pbvs:
            return pbvs[0]
        return None

    def get_newest_usable_plugin_version(self, tenant_id: str, plugin_id: str) -> Optional[PluginBuildVersion]:
        pbvs = plugin_version_repo.get_plugin_versions(tenant_id, plugin_id).filter(build_status="build_success")
        if pbvs:
            return pbvs[0]
        return None

    def update_plugin_build_status(self, region: str, tenant: Tenants) -> None:
        logger.debug("start thread to update build status")
        pbvs = plugin_version_repo.get_plugin_build_version_by_tenant_and_region(
            tenant.tenant_id, region).filter(build_status__in=["building", "timeout", "time_out"])
        for pbv in pbvs:
            status = self.get_region_plugin_build_status(region, tenant.tenant_name, pbv.plugin_id, pbv.build_version)
            pbv.build_status = status
            pbv.save()

    def get_region_plugin_build_status(self, region: str, tenant_name: str, plugin_id: str, build_version: str) -> str:
        try:
            body = region_api.get_build_status(region, tenant_name, plugin_id, build_version)
            status = body["bean"]["status"]  # type: ignore[index]  # NOTE: body may be None if region API returns unexpected format
            rt_status = REGION_BUILD_STATUS_MAP[status]
        except region_api.CallApiError as e:
            if e.status == 404:
                rt_status = "unbuild"
            else:
                rt_status = "unknown"
        return rt_status

    def copy_build_version_info(self, tenant_id: str, plugin_id: str, old_version: str,
                                new_version: str) -> PluginBuildVersion:
        old_build_version = plugin_version_repo.get_by_id_and_version(tenant_id, plugin_id, old_version)
        old_dict = model_to_dict(old_build_version)  # type: ignore[arg-type]  # NOTE: old_build_version may be None if version missing
        old_dict["build_status"] = "unbuild"
        old_dict["event_id"] = ""
        old_dict["plugin_version_status"] = "unfixed"
        # 剔除主键
        old_dict.pop("ID")
        old_dict["build_version"] = new_version
        return plugin_version_repo.create_plugin_build_version(**old_dict)

    def get_plugin_build_status(self, region: str, tenant: Tenants, plugin_id: str,
                                build_version: str) -> Optional[PluginBuildVersion]:
        pbv = plugin_version_repo.get_by_id_and_version(tenant.tenant_id, plugin_id, build_version)

        if pbv.build_status == "building":  # type: ignore[union-attr]  # NOTE: pbv may be None if version not found
            status = self.get_region_plugin_build_status(region, tenant.tenant_name, pbv.plugin_id, pbv.build_version)  # type: ignore[union-attr]
            pbv.build_status = status  # type: ignore[union-attr]
            pbv.save()  # type: ignore[union-attr]
        return pbv

    def get_by_id_and_version(self, tenant_id: str, plugin_id: str, plugin_version: str) -> Optional[PluginBuildVersion]:
        return plugin_version_repo.get_by_id_and_version(tenant_id, plugin_id, plugin_version)
