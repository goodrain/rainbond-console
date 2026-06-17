# -*- coding: utf8 -*-
"""
  Created on 18/3/4.
"""
from typing import Any, List, Optional

from django.db.models import QuerySet

from www.models.plugin import PluginBuildVersion


class PluginVersionRepository(object):
    def create_plugin_build_version(self, **params: Any) -> PluginBuildVersion:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginBuildVersion.objects.create(**params)  # type: ignore[attr-defined]

    def get_by_id_and_version(self, tenant_id: str, plugin_id: str, build_version: str) -> Optional[PluginBuildVersion]:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        pbvs = PluginBuildVersion.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id, build_version=build_version)  # type: ignore[attr-defined]
        if pbvs:
            return pbvs[0]
        return None

    def get_plugin_versions(self, tenant_id: str, plugin_id: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginBuildVersion.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id).order_by("-ID")  # type: ignore[attr-defined]

    def delete_build_version(self, tenant_id: str, plugin_id: str, build_version: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginBuildVersion.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id, build_version=build_version).delete()  # type: ignore[attr-defined]

    def get_plugin_build_version_by_tenant_and_region(self, tenant_id: str, region: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginBuildVersion.objects.filter(tenant_id=tenant_id, region=region)  # type: ignore[attr-defined]

    def delete_build_version_by_plugin_id(self, tenant_id: str, plugin_id: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginBuildVersion.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id).delete()  # type: ignore[attr-defined]

    def delete_build_version_by_plugin_ids(self, plugin_ids: Any) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginBuildVersion.objects.filter(plugin_id__in=plugin_ids).delete()  # type: ignore[attr-defined]

    def get_last_ok_one(self, plugin_id: str, tenant_id: str) -> Optional[PluginBuildVersion]:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        pbv = PluginBuildVersion.objects.filter(  # type: ignore[attr-defined]
            plugin_id=plugin_id, tenant_id=tenant_id, build_status="build_success").order_by("-build_time")
        if not pbv:
            return None
        return pbv[0]

    def create_if_not_exist(self, **plugin_build_version: Any) -> PluginBuildVersion:
        try:
            # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
            return PluginBuildVersion.objects.get(  # type: ignore[attr-defined]
                plugin_id=plugin_build_version["plugin_id"], tenant_id=plugin_build_version["tenant_id"])
        except PluginBuildVersion.DoesNotExist:
            return PluginBuildVersion.objects.create(**plugin_build_version)  # type: ignore[attr-defined]

    @staticmethod
    def bulk_create(build_versions: List[PluginBuildVersion]) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginBuildVersion.objects.bulk_create(build_versions)  # type: ignore[attr-defined]


build_version_repo = PluginVersionRepository()
