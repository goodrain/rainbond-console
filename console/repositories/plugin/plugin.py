# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
import logging
from typing import Any, List, Optional

from django.db.models import QuerySet

from www.db.base import BaseConnection
from www.models.plugin import (PluginBuildVersion, PluginConfigGroup, PluginConfigItems, TenantPlugin)

logger = logging.getLogger("default")


class TenantPluginRepository(object):
    @staticmethod
    def list_by_tenant_id(tenant_id: str, region_name: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantPlugin.objects.filter(tenant_id=tenant_id, region=region_name)  # type: ignore[attr-defined]

    def get_plugin_by_plugin_id(self, tenant_id: str, plugin_id: str) -> Optional[TenantPlugin]:
        """
        根据租户和插件id查询插件元信息
        :param tenant: 租户信息
        :param plugin_id: 插件ID列表
        :return: 插件信息
        """
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        tenant_plugins = TenantPlugin.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id)  # type: ignore[attr-defined]
        if tenant_plugins:
            plugin = tenant_plugins[0]
            return plugin
        else:
            return None

    def get_by_plugin_id(self, tenant_id: str, plugin_id: str) -> Optional[TenantPlugin]:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        plugins = TenantPlugin.objects.filter(plugin_id=plugin_id, tenant_id=tenant_id)  # type: ignore[attr-defined]
        if not plugins:
            return None
        return plugins[0]

    def get_plugin_by_plugin_ids(self, plugin_ids: Any) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantPlugin.objects.filter(plugin_id__in=plugin_ids)  # type: ignore[attr-defined]

    def get_plugin_buildversion(self, plugin_id: str, version: str) -> Optional[PluginBuildVersion]:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        build_verison = PluginBuildVersion.objects.filter(plugin_id=plugin_id, build_version=version)  # type: ignore[attr-defined]
        if build_verison:
            return build_verison[0]
        return None

    def get_plugin_config_groups(self, plugin_id: str, version: str) -> Any:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        config_groups = PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=version)  # type: ignore[attr-defined]
        if config_groups:
            return config_groups
        return []

    def get_plugin_config_items(self, plugin_id: str, version: str) -> Any:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        config_items = PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=version)  # type: ignore[attr-defined]
        if config_items:
            return config_items
        return []

    def get_plugins_by_service_ids(self, service_ids: Any) -> Any:
        if not service_ids:
            return []
        ids = ""
        for sid in service_ids:
            ids += "\"{0}\",".format(sid)
        if len(ids) > 1:
            ids = ids[:-1]
        dsn = BaseConnection()
        query_sql = '''
            select t.*,p.build_version from tenant_plugin t,plugin_build_version p,tenant_service_plugin_relation r \
            where r.service_id in({service_ids}) and t.plugin_id=r.plugin_id and p.build_version=r.build_version
            '''.format(service_ids=ids)
        plugins = dsn.query(query_sql)
        return plugins

    def create_plugin(self, **plugin_args: Any) -> TenantPlugin:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantPlugin.objects.create(**plugin_args)  # type: ignore[attr-defined]

    def delete_by_plugin_id(self, tenant_id: str, plugin_id: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantPlugin.objects.filter(tenant_id=tenant_id, plugin_id=plugin_id).delete()  # type: ignore[attr-defined]

    def get_tenant_plugins(self, tenant_id: str, region: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantPlugin.objects.filter(tenant_id=tenant_id, region=region)  # type: ignore[attr-defined]

    def get_plugin_by_origin_share_id(self, tenant_id: str, origin_share_id: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantPlugin.objects.filter(tenant_id=tenant_id, origin_share_id=origin_share_id)  # type: ignore[attr-defined]

    def create_if_not_exist(self, **plugin: Any) -> TenantPlugin:
        try:
            # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
            return TenantPlugin.objects.get(  # type: ignore[attr-defined]
                tenant_id=plugin["tenant_id"], plugin_id=plugin["plugin_id"], region=plugin["region"])
        except TenantPlugin.DoesNotExist:
            return TenantPlugin.objects.create(**plugin)  # type: ignore[attr-defined]
        except TenantPlugin.MultipleObjectsReturned:
            TenantPlugin.objects.filter(  # type: ignore[attr-defined]
                tenant_id=plugin["tenant_id"], plugin_id=plugin["plugin_id"], region=plugin["region"]).delete()
            return TenantPlugin.objects.create(**plugin)  # type: ignore[attr-defined]

    @staticmethod
    def bulk_create(plugins: List[TenantPlugin]) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantPlugin.objects.bulk_create(plugins)  # type: ignore[attr-defined]

    @staticmethod
    def delete_by_plugin_ids(plugin_ids: Any) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantPlugin.objects.filter(plugin_id__in=plugin_ids).delete()  # type: ignore[attr-defined]


class PluginBuildVersionRepository(object):
    @staticmethod
    def list_by_plugin_ids(plugin_ids: Any) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginBuildVersion.objects.filter(plugin_id__in=plugin_ids)  # type: ignore[attr-defined]


plugin_repo = TenantPluginRepository()
plugin_version_repo = PluginBuildVersionRepository()
