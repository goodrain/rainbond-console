# -*- coding: utf8 -*-
"""
  Created on 18/3/4.
"""
from typing import Any, List, Optional

from django.core.exceptions import MultipleObjectsReturned
from django.db.models import QuerySet

from www.models.plugin import PluginConfigGroup
from www.models.plugin import PluginConfigItems


class PluginConfigGroupRepository(object):
    def get_config_group_by_id_and_version(self, plugin_id: str, build_version: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version)  # type: ignore[attr-defined]

    def get_config_group_by_pk(self, pk: str) -> Optional[PluginConfigGroup]:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        pcg = PluginConfigGroup.objects.filter(ID=pk)  # type: ignore[attr-defined]
        if pcg:
            return pcg[0]
        return None

    def bulk_create_plugin_config_group(self, plugin_config_meta_list: List[PluginConfigGroup]) -> List[PluginConfigGroup]:
        """批量创建插件配置组信息"""
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        config = PluginConfigGroup.objects.bulk_create(plugin_config_meta_list)  # type: ignore[attr-defined]
        return config

    def delete_config_group_by_meta_type(self, plugin_id: str, build_version: str, service_meta_type: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigGroup.objects.filter(  # type: ignore[attr-defined]
            plugin_id=plugin_id, build_version=build_version, service_meta_type=service_meta_type).delete()

    def delete_config_group_by_id_and_version(self, plugin_id: str, build_version: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()  # type: ignore[attr-defined]

    def create_plugin_config_group(self, **params: Any) -> PluginConfigGroup:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginConfigGroup.objects.create(**params)  # type: ignore[attr-defined]

    def delete_config_group_by_plugin_id(self, plugin_id: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigGroup.objects.filter(plugin_id=plugin_id).delete()  # type: ignore[attr-defined]

    def delete_config_group_by_plugin_ids(self, plugin_ids: Any) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigGroup.objects.filter(plugin_id__in=plugin_ids).delete()  # type: ignore[attr-defined]

    def list_by_plugin_id(self, plugin_id: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginConfigGroup.objects.filter(plugin_id=plugin_id)  # type: ignore[attr-defined]

    def create_if_not_exist(self, **plugin_config_group: Any) -> None:
        try:
            # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
            PluginConfigGroup.objects.get(  # type: ignore[attr-defined]
                plugin_id=plugin_config_group["plugin_id"],
                build_version=plugin_config_group["build_version"],
                config_name=plugin_config_group["config_name"])
        except MultipleObjectsReturned:
            pass
        except PluginConfigGroup.DoesNotExist:
            PluginConfigGroup.objects.create(**plugin_config_group)  # type: ignore[attr-defined]


class PluginConfigItemsRepository(object):
    def get_config_items_by_unique_key(self, plugin_id: str, build_version: str, service_meta_type: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginConfigItems.objects.filter(  # type: ignore[attr-defined]
            plugin_id=plugin_id, build_version=build_version, service_meta_type=service_meta_type)

    def delete_config_items(self, plugin_id: str, build_version: str, service_meta_type: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigItems.objects.filter(  # type: ignore[attr-defined]
            plugin_id=plugin_id, build_version=build_version, service_meta_type=service_meta_type).delete()

    def bulk_create_items(self, config_items_list: List[PluginConfigItems]) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigItems.objects.bulk_create(config_items_list)  # type: ignore[attr-defined]

    def delete_config_items_by_id_and_version(self, plugin_id: str, build_version: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()  # type: ignore[attr-defined]

    def get_config_items_by_id_and_version(self, plugin_id: str, build_version: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version)  # type: ignore[attr-defined]

    def create_plugin_config_items(self, **params: Any) -> PluginConfigItems:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginConfigItems.objects.create(**params)  # type: ignore[attr-defined]

    def delete_config_items_by_plugin_id(self, plugin_id: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigItems.objects.filter(plugin_id=plugin_id).delete()  # type: ignore[attr-defined]

    def delete_config_items_by_plugin_ids(self, plugin_ids: Any) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        PluginConfigItems.objects.filter(plugin_id__in=plugin_ids).delete()  # type: ignore[attr-defined]

    def list_by_plugin_id(self, plugin_id: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return PluginConfigItems.objects.filter(plugin_id=plugin_id)  # type: ignore[attr-defined]

    def create_if_not_exist(self, **plugin_config_item: Any) -> None:
        try:
            # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
            PluginConfigItems.objects.get(  # type: ignore[attr-defined]
                plugin_id=plugin_config_item["plugin_id"],
                build_version=plugin_config_item["build_version"],
                attr_name=plugin_config_item["attr_name"])
        except MultipleObjectsReturned:
            pass
        except PluginConfigItems.DoesNotExist:
            PluginConfigItems.objects.create(**plugin_config_item)  # type: ignore[attr-defined]


plugin_config_group_repo = PluginConfigGroupRepository()
plugin_config_items_repo = PluginConfigItemsRepository()
