# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
import datetime
import logging

from django.forms import model_to_dict

from console.repositories.plugin import plugin_version_repo
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
region_api = RegionInvokeApi()

REGION_BUILD_STATUS_MAP = {
    "failure": "build_fail",
    "complete": "build_success",
    "building": "building",
    "timeout": "time_out",

}


class PluginBuildVersionService(object):
    def calculate_cpu(self, region, min_memory):
        min_cpu = int(min_memory) / 128 * 20
        if region == "ali-hz":
            min_cpu *= 2
        return min_cpu

    def create_build_version(self, region, plugin_id, tenant_id, user_id, update_info,
                             build_status,
                             min_memory, build_cmd="", image_tag="latest", code_version="master"):
        """创建插件版本信息"""
        min_cpu = self.calculate_cpu(region, int(min_memory))
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

    def delete_build_version_by_id_and_version(self, plugin_id, build_version, force=False):
        plugin_build_version = plugin_version_repo.get_by_id_and_version(plugin_id, build_version)
        if not plugin_build_version:
            return 404, "插件不存在"
        if not force:
            count_of_version = plugin_version_repo.get_plugin_versions(plugin_id).count()
            if count_of_version == 1:
                return 409, "至少保留插件的一个版本"
        plugin_version_repo.delete_build_version(plugin_id, build_version)
        return 200, "删除成功"

    def get_plugin_versions(self, plugin_id):
        return plugin_version_repo.get_plugin_versions(plugin_id)

    def get_newest_plugin_version(self, plugin_id):
        pbvs = plugin_version_repo.get_plugin_versions(plugin_id)
        if pbvs:
            return pbvs[0]
        return None

    def get_newest_usable_plugin_version(self, plugin_id):
        pbvs = plugin_version_repo.get_plugin_versions(plugin_id).filter(build_status="build_success")
        if pbvs:
            return pbvs[0]
        return None

    def update_plugin_build_status(self, region, tenant):
        logger.debug("start thread to update build status")

        pbvs = plugin_version_repo.get_plugin_build_version_by_tenant_and_region(tenant.tenant_id, region).filter(
            build_status__in=["building", "timeout", "time_out"])
        for pbv in pbvs:
            status = self.get_region_plugin_build_status(region, tenant.tenant_name, pbv.plugin_id, pbv.build_version)
            pbv.build_status = status
            pbv.save()

    def get_region_plugin_build_status(self, region, tenant_name, plugin_id, build_version):
        try:
            body = region_api.get_build_status(region, tenant_name, plugin_id, build_version)
            status = body["bean"]["status"]
            rt_status = REGION_BUILD_STATUS_MAP[status]
        except region_api.CallApiError as e:
            if e.status == 404:
                rt_status = "unbuild"
            else:
                rt_status = "unknown"
        return rt_status

    def copy_build_version_info(self, plugin_id, old_version, new_version):
        old_build_version = plugin_version_repo.get_by_id_and_version(plugin_id, old_version)
        old_dict = model_to_dict(old_build_version)
        old_dict["build_status"] = "unbuild"
        old_dict["event_id"] = ""
        old_dict["plugin_version_status"] = "unfixed"
        # 剔除主键
        old_dict.pop("ID")
        old_dict["build_version"] = new_version
        return plugin_version_repo.create_plugin_build_version(**old_dict)

    def get_plugin_build_status(self, region, tenant, plugin_id, build_version):
        pbv = plugin_version_repo.get_by_id_and_version(plugin_id, build_version)

        if pbv.build_status == "building":
            status = self.get_region_plugin_build_status(region, tenant.tenant_name, pbv.plugin_id, pbv.build_version)
            pbv.build_status = status
            pbv.save()
        return pbv

    def get_by_id_and_version(self, plugin_id, plugin_version):
        return plugin_version_repo.get_by_id_and_version(plugin_id, plugin_version)
