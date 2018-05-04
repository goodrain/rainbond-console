# -*- coding: utf8 -*-
"""
  Created on 18/3/4.
"""
from www.models import PluginBuildVersion


class PluginVersionRepository(object):
    def create_plugin_build_version(self, **params):
        return PluginBuildVersion.objects.create(**params)

    def get_by_id_and_version(self, plugin_id, build_version):
        pbvs = PluginBuildVersion.objects.filter(plugin_id=plugin_id, build_version=build_version)
        if pbvs:
            return pbvs[0]
        return None

    def get_plugin_versions(self, plugin_id):
        return PluginBuildVersion.objects.filter(plugin_id=plugin_id).order_by("-ID")

    def delete_build_version(self, plugin_id, build_version):
        PluginBuildVersion.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()

    def get_plugin_build_version_by_tenant_and_region(self, tenant_id, region):
        return PluginBuildVersion.objects.filter(tenant_id=tenant_id, region=region)

    def delete_build_version_by_plugin_id(self, plugin_id):
        PluginBuildVersion.objects.filter(plugin_id=plugin_id).delete()


build_version_repo = PluginVersionRepository()
