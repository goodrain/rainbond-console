# -*- coding: utf8 -*-
"""
  Created on 18/3/4.
"""
from www.models.plugin import PluginBuildVersion


class PluginVersionRepository(object):
    def create_plugin_build_version(self, **params):
        return PluginBuildVersion.objects.create(**params)

    def get_by_id_and_version(self, tenant_id, plugin_id, build_version):
        pbvs = PluginBuildVersion.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id, build_version=build_version)
        if pbvs:
            return pbvs[0]
        return None

    def get_plugin_versions(self, tenant_id, plugin_id):
        return PluginBuildVersion.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id).order_by("-ID")

    def delete_build_version(self, tenant_id, plugin_id, build_version):
        PluginBuildVersion.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id, build_version=build_version).delete()

    def get_plugin_build_version_by_tenant_and_region(self, tenant_id, region):
        return PluginBuildVersion.objects.filter(tenant_id=tenant_id, region=region)

    def delete_build_version_by_plugin_id(self, tenant_id, plugin_id):
        PluginBuildVersion.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id).delete()

    def get_last_ok_one(self, plugin_id, tenant_id):
        pbv = PluginBuildVersion.objects.filter(
            plugin_id=plugin_id, tenant_id=tenant_id, build_status="build_success").order_by("-build_time")
        if not pbv:
            return None
        return pbv[0]

    def create_if_not_exist(self, **plugin_build_version):
        try:
            return PluginBuildVersion.objects.get(
                plugin_id=plugin_build_version["plugin_id"], tenant_id=plugin_build_version["tenant_id"])
        except PluginBuildVersion.DoesNotExist:
            return PluginBuildVersion.objects.create(**plugin_build_version)

    @staticmethod
    def bulk_create(build_versions):
        PluginBuildVersion.objects.bulk_create(build_versions)


build_version_repo = PluginVersionRepository()
