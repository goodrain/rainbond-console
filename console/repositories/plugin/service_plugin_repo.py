# -*- coding: utf8 -*-
"""
  Created on 18/1/29.
"""
from typing import Any, List, Optional

from django.db.models import QuerySet

from www.db.base import BaseConnection
from www.models.plugin import ServicePluginConfigVar
from www.models.plugin import TenantServicePluginAttr
from www.models.plugin import TenantServicePluginRelation


class AppPluginRelationRepo(object):
    @staticmethod
    def list_by_component_ids(service_ids: Any) -> List[TenantServicePluginRelation]:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        rels = TenantServicePluginRelation.objects.filter(service_id__in=service_ids)  # type: ignore[attr-defined]
        return [rel for rel in rels]

    def get_service_plugin_relation_by_service_id(self, service_id: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantServicePluginRelation.objects.filter(service_id=service_id)  # type: ignore[attr-defined]

    def get_service_plugin_relation_by_plugin_unique_key(self, plugin_id: str, build_version: str) -> Optional[QuerySet]:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        tsprs = TenantServicePluginRelation.objects.filter(plugin_id=plugin_id, build_version=build_version)  # type: ignore[attr-defined]
        if tsprs:
            return tsprs
        return None

    def get_used_plugin_services(self, plugin_id: str) -> QuerySet:
        """获取使用了某个插件的组件"""
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantServicePluginRelation.objects.filter(plugin_id=plugin_id)  # type: ignore[attr-defined]

    def create_service_plugin_relation(self, **params: Any) -> TenantServicePluginRelation:
        """创建组件插件关系"""
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantServicePluginRelation.objects.create(**params)  # type: ignore[attr-defined]

    def update_service_plugin_status(self, service_id: str, plugin_id: str, is_active: Any, cpu: Optional[int],
                                     memory: Optional[int]) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        tspr = TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_id=plugin_id).first()  # type: ignore[attr-defined]
        tspr.plugin_status = is_active
        if cpu is not None and type(cpu) == int and cpu >= 0:
            tspr.min_cpu = cpu
        if memory is not None and type(memory) == int and memory >= 0:
            tspr.min_memory = memory
        tspr.save()

    def get_relation_by_service_and_plugin(self, service_id: str, plugin_id: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_id=plugin_id)  # type: ignore[attr-defined]

    def get_service_plugin_relation_by_plugin_id(self, plugin_id: str, service_ids: Any) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantServicePluginRelation.objects.filter(plugin_id=plugin_id, service_id__in=service_ids)  # type: ignore[attr-defined]

    def delete_service_plugin_relation_by_plugin_id(self, plugin_id: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantServicePluginRelation.objects.filter(plugin_id=plugin_id).delete()  # type: ignore[attr-defined]

    def delete_service_plugin(self, service_id: str, plugin_id: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_id=plugin_id).delete()  # type: ignore[attr-defined]

    def get_service_plugin_relations_by_service_ids(self, service_ids: Any) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return TenantServicePluginRelation.objects.filter(service_id__in=service_ids)  # type: ignore[attr-defined]

    def delete_by_sid(self, sid: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantServicePluginRelation.objects.filter(service_id=sid).delete()  # type: ignore[attr-defined]

    def bulk_create(self, plugin_relations: List[TenantServicePluginRelation]) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantServicePluginRelation.objects.bulk_create(plugin_relations)  # type: ignore[attr-defined]

    @staticmethod
    def overwrite_by_component_ids(component_ids: Any, plugin_deps: List[TenantServicePluginRelation]) -> None:
        plugin_deps = [plugin_dep for plugin_dep in plugin_deps if plugin_dep.service_id in component_ids]
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantServicePluginRelation.objects.filter(service_id__in=component_ids).delete()  # type: ignore[attr-defined]
        TenantServicePluginRelation.objects.bulk_create(plugin_deps)  # type: ignore[attr-defined]

    def check_plugins_by_eid(self, eid: str) -> bool:
        """
        check if an app has been shared
        """
        conn = BaseConnection()
        sql = """
            SELECT
                a.plugin_id
            FROM
                tenant_service_plugin_relation a,
                tenant_service c,
                tenant_info b
            WHERE
                c.tenant_id = b.tenant_id
                AND a.service_id = c.service_id
                AND c.service_source <> "market"
                AND b.enterprise_id = "{eid}"
                LIMIT 1""".format(eid=eid)
        result = conn.query(sql)
        return True if len(result) > 0 else False


class ServicePluginAttrRepository(object):
    def delete_attr_by_plugin_id(self, plugin_id: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        TenantServicePluginAttr.objects.filter(plugin_id=plugin_id).delete()  # type: ignore[attr-defined]


class ServicePluginConfigVarRepository(object):
    def get_service_plugin_config_var(self, service_id: str, plugin_id: str, build_version: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return ServicePluginConfigVar.objects.filter(service_id=service_id, plugin_id=plugin_id, build_version=build_version)  # type: ignore[attr-defined]

    def delete_service_plugin_config_var(self, service_id: str, plugin_id: str) -> None:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        ServicePluginConfigVar.objects.filter(service_id=service_id, plugin_id=plugin_id).delete()  # type: ignore[attr-defined]

    def get_service_plugin_all_config(self, service_id: str) -> QuerySet:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        return ServicePluginConfigVar.objects.filter(service_id=service_id)  # type: ignore[attr-defined]

    @staticmethod
    def list_by_component_ids(component_ids: Any) -> List[ServicePluginConfigVar]:
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        configs = ServicePluginConfigVar.objects.filter(service_id__in=component_ids)  # type: ignore[attr-defined]
        return [config for config in configs]

    @staticmethod
    def overwrite_by_component_ids(component_ids: Any, plugin_configs: List[ServicePluginConfigVar]) -> None:
        plugin_configs = [config for config in plugin_configs if config.service_id in component_ids]
        # .objects exists at runtime via ModelBase metaclass; stub gap (model not in app registry)
        ServicePluginConfigVar.objects.filter(service_id__in=component_ids).delete()  # type: ignore[attr-defined]
        ServicePluginConfigVar.objects.bulk_create(plugin_configs)  # type: ignore[attr-defined]
