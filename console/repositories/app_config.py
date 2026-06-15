# -*- coding: utf8 -*-
"""
  Created on 18/1/12.
"""
import datetime
import json
import logging
import os
from typing import Any, List, Optional, Tuple

from console.exception.main import AbortRequest
from console.utils.shortcuts import get_object_or_404
from django.db.models import Q, QuerySet
from www.db.base import BaseConnection
from www.models.main import (GatewayCustomConfiguration,
                             ServiceDomain, ServiceDomainCertificate, ServiceTcpDomain, TenantServiceAuth,
                             TenantServiceConfigurationFile, TenantServiceEnv, TenantServiceEnvVar, TenantServiceInfo,
                             TenantServiceMountRelation, TenantServiceRelation, Tenants, TenantServicesPort,
                             TenantServiceVolume, ThirdPartyServiceEndpoints)
from www.models.service_publish import ServiceExtendMethod

logger = logging.getLogger("default")


class TenantServiceEnvVarRepository(object):
    def get_service_env(self, tenant_id: str, service_id: str) -> QuerySet[TenantServiceEnvVar]:
        return TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id)

    def get_service_env_by_scope(self, tenant_id: str, service_id: str, scope: str) -> QuerySet[TenantServiceEnvVar]:
        return TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, scope=scope).all()

    def get_by_attr_name_and_scope(self, tenant_id: str, service_id: str, attr_name: str,
                                   scope: str) -> Optional[TenantServiceEnvVar]:
        envs = TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, attr_name=attr_name, scope=scope)
        if envs:
            return envs[0]
        return None

    def get_service_env_by_attr_name(self, tenant_id: str, service_id: str,
                                     attr_name: str) -> Optional[TenantServiceEnvVar]:
        envs = TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, attr_name=attr_name)
        if envs:
            return envs[0]
        return None

    def get_service_env_or_404_by_env_id(self, tenant_id: str, service_id: str, env_id: str) -> TenantServiceEnvVar:
        return get_object_or_404(
            TenantServiceEnvVar,
            msg="Environment variable with ID {} not found".format(env_id),
            msg_show="环境变量`{}`不存在".format(env_id),
            tenant_id=tenant_id,
            service_id=service_id,
            ID=env_id)

    def get_env_by_ids_and_attr_names(self, tenant_id: str, service_ids: Any,
                                      attr_names: Any) -> QuerySet[TenantServiceEnvVar]:
        envs = TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id__in=service_ids, attr_name__in=attr_names)
        return envs

    def get_depend_outer_envs_by_ids(self, tenant_id: str, service_ids: Any) -> QuerySet[TenantServiceEnvVar]:
        envs = TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id__in=service_ids, scope="outer")
        return envs

    def get_env_by_ids_and_env_id(self, tenant_id: str, service_id: str, env_id: str) -> TenantServiceEnvVar:
        envs = TenantServiceEnvVar.objects.get(tenant_id=tenant_id, service_id=service_id, ID=env_id)
        return envs

    def get_service_env_by_port(self, tenant_id: str, service_id: str, port: int) -> QuerySet[TenantServiceEnvVar]:
        return TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, container_port=port)

    def get_service_host_env(self, tenant_id: str, service_id: str, port: int) -> TenantServiceEnvVar:
        return TenantServiceEnvVar.objects.get(
            tenant_id=tenant_id, service_id=service_id, container_port=port, attr_name__contains="HOST")

    @staticmethod
    def list_envs_by_component_ids(tenant_id: str, component_ids: Any) -> QuerySet[TenantServiceEnvVar]:
        return TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id__in=component_ids)

    def add_service_env(self, **tenant_service_env_var: Any) -> TenantServiceEnvVar:
        env = TenantServiceEnvVar.objects.create(**tenant_service_env_var)
        return env

    def bulk_create_component_env(self, envs: Any) -> None:
        TenantServiceEnvVar.objects.bulk_create(envs)

    def delete_service_env(self, tenant_id: str, service_id: str) -> None:
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id).delete()

    def delete_service_build_env(self, tenant_id: str, service_id: str) -> None:
        # 排除 CNB_* 和 BUILD_TYPE 变量，避免重新检测时误删用户设置的 CNB 构建参数
        # BUILD_TYPE 由 change_lang_and_package_tool 设置，检测不产生此变量
        TenantServiceEnvVar.objects.filter(
            tenant_id=tenant_id, service_id=service_id, scope="build"
        ).exclude(
            attr_name__startswith="CNB_"
        ).exclude(
            attr_name="BUILD_TYPE"
        ).delete()

    def delete_service_env_by_attr_name(self, tenant_id: str, service_id: str, attr_name: str) -> None:
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, attr_name=attr_name).delete()

    def delete_service_env_by_pk(self, pk: int) -> None:
        TenantServiceEnvVar.objects.filter(pk=pk).delete()

    def delete_service_env_by_port(self, tenant_id: str, service_id: str, container_port: int) -> None:
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, container_port=container_port).delete()

    def update_env_var(self, tenant_id: str, service_id: str, old_attr_name: str, **update_params: Any) -> None:
        TenantServiceEnvVar.objects.filter(
            tenant_id=tenant_id, service_id=service_id, attr_name=old_attr_name).update(**update_params)

    def update_or_create_env_var(self, tenant_id: str, service_id: str, attr_name: str, attr_value: Any) -> None:
        """
        创建或更新构建时环境变量。
        注意：此方法专用于构建变量，始终确保 scope 为 build。
        """
        try:
            obj = TenantServiceEnvVar.objects.get(tenant_id=tenant_id, service_id=service_id, attr_name=attr_name)
            obj.attr_value = attr_value
            obj.scope = "build"  # 确保更新时也设置为构建时变量
            obj.save()
        except TenantServiceEnvVar.DoesNotExist:
            TenantServiceEnvVar.objects.create(
                tenant_id=tenant_id,
                service_id=service_id,
                attr_name=attr_name,
                attr_value=attr_value,
                name=attr_name,
                scope="build",
                create_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def get_build_envs(self, tenant_id: str, service_id: str) -> dict:
        envs: dict = {}
        default_envs = Q(attr_name__in=("COMPILE_ENV", "NO_CACHE", "DEBUG", "PROXY", "SBT_EXTRAS_OPTS"))
        prefix_start_env = Q(attr_name__startswith="BUILD_")
        cnb_prefix_env = Q(attr_name__startswith="CNB_")  # CNB 构建参数
        build_start_env = Q(scope="build")
        build_envs = self.get_service_env(tenant_id, service_id).filter(default_envs | prefix_start_env | cnb_prefix_env | build_start_env)
        for benv in build_envs:
            envs[benv.attr_name] = benv.attr_value
        compile_env = compile_env_repo.get_service_compile_env(service_id)
        if compile_env:
            envs["PROC_ENV"] = compile_env.user_dependency
        return envs

    def change_service_env_scope(self, env: TenantServiceEnvVar, scope: str) -> None:
        """变更环境变量范围"""
        scope = self._check_service_env_scope(scope)
        env.scope = scope
        env.save()

    @staticmethod
    def _check_service_env_scope(scope: str) -> Any:
        try:
            return TenantServiceEnvVar.ScopeType(scope).value
        except ValueError:
            raise AbortRequest(msg="the value of scope is outer or inner")

    def bulk_create(self, envs: Any) -> None:
        TenantServiceEnvVar.objects.bulk_create(envs)

    @staticmethod
    def overwrite_by_component_ids(component_ids: Any, envs: Any) -> None:
        TenantServiceEnvVar.objects.filter(service_id__in=component_ids).delete()
        TenantServiceEnvVar.objects.bulk_create(envs)

    @staticmethod
    def create_or_update(env: TenantServiceEnvVar) -> None:
        try:
            old_env = TenantServiceEnvVar.objects.get(
                tenant_id=env.tenant_id, service_id=env.service_id, attr_name=env.attr_name)
            env.ID = old_env.ID
            env.save()
        except TenantServiceEnvVar.DoesNotExist:
            env.save()

    @staticmethod
    def bulk_update(envs: Any) -> None:
        TenantServiceEnvVar.objects.filter(pk__in=[env.ID for env in envs]).delete()
        TenantServiceEnvVar.objects.bulk_create(envs)


class TenantServicePortRepository(object):
    def list_inner_ports(self, tenant_id: str, service_id: str) -> QuerySet[TenantServicesPort]:
        return TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id, is_inner_service=True)

    def get_service_ports(self, tenant_id: str, service_id: str) -> QuerySet[TenantServicesPort]:
        return TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id)

    def get_service_port_by_port(self, tenant_id: str, service_id: str,
                                 container_port: int) -> Optional[TenantServicesPort]:
        ports = TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id, container_port=container_port)
        if ports:
            return ports[0]
        return None

    def add_service_port(self, **tenant_service_port: Any) -> TenantServicesPort:
        service_port = TenantServicesPort.objects.create(**tenant_service_port)
        return service_port

    def get_tenant_services(self, tenant_id: str) -> QuerySet[TenantServicesPort]:
        return TenantServicesPort.objects.filter(tenant_id=tenant_id, is_inner_service=True)

    def delete_service_port(self, tenant_id: str, service_id: str) -> None:
        TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id).delete()

    def delete_serivce_port_by_port(self, tenant_id: str, service_id: str, container_port: int) -> None:
        TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id, container_port=container_port).delete()

    def delete_service_port_by_pk(self, pk: int) -> None:
        TenantServicesPort.objects.filter(pk=pk).delete()

    def get_service_port_by_alias(self, service_id: str, alias: str) -> TenantServicesPort:
        return TenantServicesPort.objects.get(service_id=service_id, port_alias=alias)

    def update_port(self, tenant_id: str, service_id: str, container_port: int, **update_params: Any) -> None:
        TenantServicesPort.objects.filter(
            tenant_id=tenant_id, service_id=service_id, container_port=container_port).update(**update_params)

    def get_http_opend_services_ports(self, tenant_id: str, service_ids: Any) -> QuerySet[TenantServicesPort]:
        return TenantServicesPort.objects.filter(
            tenant_id=tenant_id, service_id__in=service_ids, is_outer_service=True, protocol__in=("http", "https"))

    def get_tcp_outer_opend_ports(self, service_ids: Any) -> QuerySet[TenantServicesPort]:
        return TenantServicesPort.objects.filter(
            service_id__in=service_ids, is_outer_service=True).exclude(protocol__in=("http", "https"))

    def get_service_port_by_lb_mapping_port(self, service_id: str, lb_mapping_port: int) -> Optional[TenantServicesPort]:
        return TenantServicesPort.objects.filter(service_id=service_id, lb_mapping_port=lb_mapping_port).first()

    def bulk_create(self, ports: Any) -> None:
        TenantServicesPort.objects.bulk_create(ports)

    def update(self, **param: Any) -> None:
        TenantServicesPort.objects.filter(
            tenant_id=param["tenant_id"], service_id=param["service_id"],
            container_port=param["container_port"]).update(**param)

    @staticmethod
    def bulk_create_or_update(ports: Any) -> None:
        TenantServicesPort.objects.filter(pk__in=[port.ID for port in ports]).delete()
        TenantServicesPort.objects.bulk_create(ports)

    @staticmethod
    def overwrite_by_component_ids(component_ids: Any, ports: Any) -> None:
        TenantServicesPort.objects.filter(service_id__in=component_ids).delete()
        TenantServicesPort.objects.bulk_create(ports)

    @staticmethod
    def list_by_service_ids(tenant_id: str, service_ids: Any) -> QuerySet[TenantServicesPort]:
        return TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id__in=service_ids)

    @staticmethod
    def list_inner_ports_by_service_ids(tenant_id: str, service_ids: Any) -> Any:
        if not service_ids:
            return []
        return TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id__in=service_ids, is_inner_service=True)

    @staticmethod
    def list_by_k8s_service_names(tenant_id: str, k8s_service_names: Any) -> QuerySet[TenantServicesPort]:
        return TenantServicesPort.objects.filter(tenant_id=tenant_id, k8s_service_name__in=k8s_service_names)

    @staticmethod
    def get_by_k8s_service_name(tenant_id: str, k8s_service_name: str) -> Optional[TenantServicesPort]:
        if not k8s_service_name:
            return None
        ports = TenantServicesPort.objects.filter(tenant_id=tenant_id, k8s_service_name=k8s_service_name)
        if ports:
            return ports[0]
        return None

    @staticmethod
    def check_k8s_service_name(tenant_id: str, service_id: str, port: int,
                               k8s_service_names: Any) -> TenantServicesPort:
        return TenantServicesPort.objects.get(
            tenant_id=tenant_id, service_id=service_id, container_port=port, k8s_service_name__in=k8s_service_names)


class TenantServiceVolumnRepository(object):
    def get_service_volume_by_id(self, id: int) -> Optional[TenantServiceVolume]:
        volumes = TenantServiceVolume.objects.get(ID=id)
        if volumes:
            return volumes
        return None

    def list_custom_volumes(self, service_ids: Any) -> QuerySet[TenantServiceVolume]:
        return TenantServiceVolume.objects.filter(service_id__in=service_ids).exclude(
            volume_type__in=[
                "config-file",
                TenantServiceVolume.SHARE,
                TenantServiceVolume.LOCAL,
                TenantServiceVolume.TMPFS,
                "local-path",
            ])

    def get_service_volumes_with_config_file(self, service_id: str) -> QuerySet[TenantServiceVolume]:
        return TenantServiceVolume.objects.filter(service_id=service_id)

    def get_service_volumes(self, service_id: str) -> QuerySet[TenantServiceVolume]:
        return TenantServiceVolume.objects.filter(service_id=service_id).exclude(volume_type="config-file")

    def get_service_volumes_about_config_file(self, service_id: str) -> QuerySet[TenantServiceVolume]:
        return TenantServiceVolume.objects.filter(service_id=service_id, volume_type="config-file")

    def get_service_volume_by_name(self, service_id: str, volume_name: str) -> Optional[TenantServiceVolume]:
        volumes = TenantServiceVolume.objects.filter(service_id=service_id, volume_name=volume_name)
        if volumes:
            return volumes[0]
        return None

    def get_service_volume_by_path(self, service_id: str, volume_path: str) -> Optional[TenantServiceVolume]:
        volumes = TenantServiceVolume.objects.filter(service_id=service_id, volume_path=volume_path)
        if volumes:
            return volumes[0]
        return None

    def get_service_volume_by_pk(self, volume_id: int) -> Optional[TenantServiceVolume]:
        try:
            return TenantServiceVolume.objects.get(pk=volume_id)
        except TenantServiceVolume.DoesNotExist:
            return None

    def add_service_volume(self, **tenant_service_volume: Any) -> TenantServiceVolume:
        return TenantServiceVolume.objects.create(**tenant_service_volume)

    def delete_volume_by_id(self, volume_id: int) -> None:
        TenantServiceVolume.objects.filter(ID=volume_id).delete()

    @staticmethod
    def delete_file_by_volume(volume: TenantServiceVolume) -> None:
        TenantServiceConfigurationFile.objects.filter(service_id=volume.service_id)\
            .filter(Q(volume_id=volume.ID) | Q(volume_name=volume.volume_name)).delete()

    def add_service_config_file(self, **service_config_file: Any) -> TenantServiceConfigurationFile:
        return TenantServiceConfigurationFile.objects.create(**service_config_file)

    def get_service_config_files(self, service_id: str) -> QuerySet[TenantServiceConfigurationFile]:
        return TenantServiceConfigurationFile.objects.filter(service_id=service_id)

    @staticmethod
    def get_service_config_file(volume: TenantServiceVolume) -> Optional[TenantServiceConfigurationFile]:
        return TenantServiceConfigurationFile.objects.filter(service_id=volume.service_id)\
            .filter(Q(volume_id=volume.ID) | Q(volume_name=volume.volume_name)).first()

    def get_services_volumes(self, service_ids: Any) -> QuerySet[TenantServiceVolume]:
        return TenantServiceVolume.objects.filter(service_id__in=service_ids)

    def delete_service_volumes(self, service_id: str) -> None:
        TenantServiceVolume.objects.filter(service_id=service_id).delete()

    def get_by_sid_name(self, service_id: str, volume_name: str) -> Optional[TenantServiceVolume]:
        return TenantServiceVolume.objects.filter(service_id=service_id, volume_name=volume_name).first()

    def delete_config_files(self, sid: str) -> None:
        TenantServiceConfigurationFile.objects.filter(service_id=sid).defer()

    @staticmethod
    def bulk_create(volumes: Any) -> None:
        TenantServiceVolume.objects.bulk_create(volumes)

    def bulk_create_or_update(self, volumes: Any) -> None:
        for volume in volumes:
            self.create_or_update(volume)

    def overwrite_by_component_ids(self, component_ids: Any, volumes: Any) -> None:
        TenantServiceVolume.objects.filter(service_id__in=component_ids).delete()
        self.bulk_create(volumes)

    @staticmethod
    def create_or_update(volume: TenantServiceVolume) -> None:
        try:
            old_volume = TenantServiceVolume.objects.get(service_id=volume.service_id, volume_name=volume.volume_name)
            volume.ID = old_volume.ID
        except TenantServiceVolume.DoesNotExist:
            pass
        volume.save()


class ComponentConfigurationFileRepository(object):
    @staticmethod
    def bulk_create(config_files: Any) -> None:
        TenantServiceConfigurationFile.objects.bulk_create(config_files)

    @staticmethod
    def overwrite_by_component_ids(component_ids: Any, config_files: Any) -> None:
        TenantServiceConfigurationFile.objects.filter(service_id__in=component_ids).delete()
        TenantServiceConfigurationFile.objects.bulk_create(config_files)


def bulk_create_or_update(tenant_id: str, component_deps: Any) -> None:
    TenantServiceRelation.objects.filter(
        tenant_id=tenant_id, service_id__in=[dep.service_id for dep in component_deps]).delete()
    TenantServiceRelation.objects.bulk_create(component_deps)


class TenantServiceRelationRepository(object):
    def get_service_dependencies(self, tenant_id: str, service_id: str) -> QuerySet[TenantServiceRelation]:
        return TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id)

    def get_service_reverse_dependencies(self, tenant_id: str, service_id: str) -> QuerySet[TenantServiceRelation]:
        return TenantServiceRelation.objects.filter(tenant_id=tenant_id, dep_service_id=service_id)

    def get_depency_by_serivce_id_and_dep_service_id(self, tenant_id: str, service_id: str,
                                                     dep_service_id: str) -> Optional[TenantServiceRelation]:
        deps = TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id, dep_service_id=dep_service_id)
        if deps:
            return deps[0]
        return None

    def add_service_dependency(self, **tenant_service_relation: Any) -> TenantServiceRelation:
        return TenantServiceRelation.objects.create(**tenant_service_relation)

    def bulk_add_service_dependency(self, service_dependency_list: Any) -> List[TenantServiceRelation]:
        return TenantServiceRelation.objects.bulk_create([TenantServiceRelation(**data) for data in service_dependency_list])

    def get_dependency_by_dep_service_ids(self, tenant_id: str, service_id: str,
                                          dep_service_ids: Any) -> QuerySet[TenantServiceRelation]:
        return TenantServiceRelation.objects.filter(
            tenant_id=tenant_id, service_id=service_id, dep_service_id__in=dep_service_ids)

    def get_dependency_by_dep_id(self, tenant_id: str, dep_service_id: str) -> QuerySet[TenantServiceRelation]:
        tsr = TenantServiceRelation.objects.filter(tenant_id=tenant_id, dep_service_id=dep_service_id)
        return tsr

    def delete_service_relation(self, tenant_id: str, service_id: str) -> None:
        TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id).delete()

    def get_services_dep_current_service(self, tenant_id: str, dep_service_id: str) -> QuerySet[TenantServiceRelation]:
        return TenantServiceRelation.objects.filter(tenant_id=tenant_id, dep_service_id=dep_service_id)

    def check_db_dep_by_eid(self, eid: str) -> bool:
        """
        check if there is a database installed from the market that is dependent on
        """
        conn = BaseConnection()
        sql = """
            SELECT
                a.service_id, a.dep_service_id
            FROM
                tenant_service_relation a,
                tenant_service b,
                tenant_info c,
                tenant_service d
            WHERE
                b.tenant_id = c.tenant_id
                AND c.enterprise_id = "{eid}"
                AND a.service_id = d.service_id
                AND a.dep_service_id = b.service_id
                AND ( b.image LIKE "%mysql%" OR b.image LIKE "%postgres%" OR b.image LIKE "%mariadb%" )
                AND (b.service_source <> "market" OR d.service_source <> "market")
                limit 1""".format(eid=eid)
        result = conn.query(sql)
        if len(result) > 0:
            return True
        sql2 = """
            SELECT
                a.dep_service_id
            FROM
                tenant_service_relation a,
                tenant_service b,
                tenant_info c,
                tenant_service d,
                service_source e,
                service_source f
            WHERE
                b.tenant_id = c.tenant_id
                AND c.enterprise_id = "{eid}"
                AND a.service_id = d.service_id
                AND a.dep_service_id = b.service_id
                AND ( b.image LIKE "%mysql%" OR b.image LIKE "%postgres%" OR b.image LIKE "%mariadb%" )
                AND ( b.service_source = "market" AND d.service_source = "market" )
                AND e.service_id = b.service_id
                AND f.service_id = d.service_id
                AND e.group_key <> f.group_key
                LIMIT 1""".format(eid=eid)
        result2 = conn.query(sql2)
        return True if len(result2) > 0 else False

    @staticmethod
    def list_by_component_ids(tenant_id: str, component_ids: Any) -> QuerySet[TenantServiceRelation]:
        return TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id__in=component_ids)

    @staticmethod
    def overwrite_by_component_id(component_ids: Any, component_deps: Any) -> None:
        component_deps = [dep for dep in component_deps if dep.service_id in component_ids]
        TenantServiceRelation.objects.filter(service_id__in=component_ids).delete()
        TenantServiceRelation.objects.bulk_create(component_deps)


class TenantServiceMntRelationRepository(object):
    def get_mnt_by_dep_id_and_mntname(self, dep_service_id: str,
                                      mnt_name: str) -> QuerySet[TenantServiceMountRelation]:
        return TenantServiceMountRelation.objects.filter(dep_service_id=dep_service_id, mnt_name=mnt_name)

    def get_service_mnts(self, tenant_id: str, service_id: str) -> List[TenantServiceMountRelation]:
        return self.get_service_mnts_filter_volume_type(tenant_id=tenant_id, service_id=service_id)

    def get_by_dep_service_id(self, tenant_id: str, dep_service_id: str) -> QuerySet[TenantServiceMountRelation]:
        return TenantServiceMountRelation.objects.filter(tenant_id=tenant_id, dep_service_id=dep_service_id)

    def get_service_mnts_filter_volume_type(self, tenant_id: str, service_id: str,
                                            volume_types: Any = None) -> List[TenantServiceMountRelation]:
        conn = BaseConnection()
        query = "mnt.tenant_id = '%s' and mnt.service_id = '%s'" % (tenant_id, service_id)

        sql = """
        select mnt.mnt_name,
            mnt.mnt_dir,
            mnt.dep_service_id,
            mnt.service_id,
            mnt.tenant_id,
            volume.volume_type,
            volume.ID as volume_id
        from tenant_service_mnt_relation as mnt
                 inner join tenant_service_volume as volume
                            on mnt.dep_service_id = volume.service_id and mnt.mnt_name = volume.volume_name
        where {};
        """.format(query)
        result = conn.query(sql)
        dep_mnts = []
        for real_dep_mnt in result:
            if volume_types and len(volume_types) == 1 and volume_types[0] == "config-file":
                if real_dep_mnt.get("volume_type") != "config-file":
                    continue
            if volume_types and len(volume_types) >= 1 and volume_types[0] != "config-file":
                if real_dep_mnt.get("volume_type") == "config-file":
                    continue
            mnt = TenantServiceMountRelation(
                tenant_id=real_dep_mnt.get("tenant_id"),
                service_id=real_dep_mnt.get("service_id"),
                dep_service_id=real_dep_mnt.get("dep_service_id"),
                mnt_name=real_dep_mnt.get("mnt_name"),
                mnt_dir=real_dep_mnt.get("mnt_dir"))
            # dynamic attrs attached for downstream use; not model fields
            mnt.volume_type = real_dep_mnt.get("volume_type")  # type: ignore[attr-defined]
            mnt.volume_id = real_dep_mnt.get("volume_id")  # type: ignore[attr-defined]

            dep_mnts.append(mnt)
        return dep_mnts

    def get_mnt_relation_by_id(self, service_id: str, dep_service_id: str,
                               mnt_name: str) -> TenantServiceMountRelation:
        return TenantServiceMountRelation.objects.get(service_id=service_id, dep_service_id=dep_service_id, mnt_name=mnt_name)

    def list_mnt_relations_by_service_ids(self, tenant_id: str,
                                          service_ids: Any) -> QuerySet[TenantServiceMountRelation]:
        return TenantServiceMountRelation.objects.filter(tenant_id=tenant_id, service_id__in=service_ids)

    def add_service_mnt_relation(self, tenant_id: str, service_id: str, dep_service_id: str, mnt_name: str,
                                 mnt_dir: str) -> TenantServiceMountRelation:
        tsr = TenantServiceMountRelation.objects.create(
            tenant_id=tenant_id,
            service_id=service_id,
            dep_service_id=dep_service_id,
            mnt_name=mnt_name,
            mnt_dir=mnt_dir  # this dir is source app's volume path
        )
        return tsr

    def delete_mnt_relation(self, service_id: str, dep_service_id: str, mnt_name: str) -> None:
        TenantServiceMountRelation.objects.filter(
            service_id=service_id, dep_service_id=dep_service_id, mnt_name=mnt_name).delete()

    def get_mount_current_service(self, tenant_id: str, service_id: str) -> QuerySet[TenantServiceMountRelation]:
        """查询挂载当前组件的信息"""
        return TenantServiceMountRelation.objects.filter(tenant_id=tenant_id, dep_service_id=service_id)

    def delete_mnt(self, service_id: str) -> None:
        TenantServiceMountRelation.objects.filter(service_id=service_id).delete()

    def bulk_create(self, mnts: Any) -> None:
        TenantServiceMountRelation.objects.bulk_create(mnts)

    def overwrite_by_component_id(self, component_ids: Any, volume_deps: Any) -> None:
        volume_deps = [dep for dep in volume_deps if dep.service_id in component_ids]
        TenantServiceMountRelation.objects.filter(service_id__in=component_ids).delete()
        self.bulk_create(volume_deps)

class ServiceDomainRepository(object):
    def get_service_domain_by_container_port(self, service_id: str, container_port: int) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.filter(service_id=service_id, container_port=container_port)

    def get_service_domain_by_container_port_and_protocol(self, service_id: str, container_port: int,
                                                          protocol: str) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.filter(service_id=service_id, container_port=container_port, protocol=protocol)

    def get_service_domain_by_http_rule_id(self, http_rule_id: str) -> Optional[ServiceDomain]:
        domain = ServiceDomain.objects.filter(http_rule_id=http_rule_id).first()
        if domain:
            return domain
        else:
            return None

    def get_domain_by_domain_name(self, domain_name: str) -> Optional[ServiceDomain]:
        domains = ServiceDomain.objects.filter(domain_name=domain_name)
        if domains:
            return domains[0]
        return None

    def get_domains_by_service_ids(self, service_ids: Any) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.filter(service_id__in=service_ids)

    def get_domains_by_tenant_ids(self, tenant_ids: Any, is_auto_ssl: Optional[bool] = None) -> QuerySet[ServiceDomain]:
        if is_auto_ssl is None:
            return ServiceDomain.objects.filter(tenant_id__in=tenant_ids)
        else:
            return ServiceDomain.objects.filter(tenant_id__in=tenant_ids, auto_ssl=is_auto_ssl)

    def get_domain_by_id(self, domain_id: str) -> Optional[ServiceDomain]:
        domains = ServiceDomain.objects.filter(ID=domain_id)
        if domains:
            return domains[0]
        return None

    def get_domain_by_domain_name_or_service_alias_or_group_name(self,
                                                                 search_conditions: str) -> QuerySet[ServiceDomain]:
        domains = ServiceDomain.objects.filter(
            Q(domain_name__contains=search_conditions)
            | Q(service_alias__contains=search_conditions)
            | Q(group_name__contains=search_conditions)).order_by("-type")
        return domains

    def get_all_domain(self) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.all()

    def get_all_domain_count_by_tenant_and_region_id(self, tenant_id: str, region_id: str) -> int:
        return ServiceDomain.objects.filter(tenant_id=tenant_id, region_id=region_id).count()

    def get_domain_by_name_and_port(self, service_id: str, container_port: int,
                                    domain_name: str) -> Optional[QuerySet[ServiceDomain]]:
        try:
            return ServiceDomain.objects.filter(
                service_id=service_id, container_port=container_port, domain_name=domain_name).all()
        except ServiceDomain.DoesNotExist:
            return None

    def get_domain_by_name_and_port_and_protocol(self, service_id: str, container_port: int, domain_name: str,
                                                 protocol: str,
                                                 domain_path: Optional[str] = None) -> Optional[ServiceDomain]:
        if domain_path:
            try:
                return ServiceDomain.objects.get(
                    service_id=service_id,
                    container_port=container_port,
                    domain_name=domain_name,
                    protocol=protocol,
                    domain_path=domain_path)
            except ServiceDomain.DoesNotExist:
                return None
        else:
            try:
                return ServiceDomain.objects.get(
                    service_id=service_id, container_port=container_port, domain_name=domain_name, protocol=protocol)
            except ServiceDomain.DoesNotExist:
                return None

    def get_domain_by_name_and_path(self, domain_name: str,
                                    domain_path: str) -> Optional[QuerySet[ServiceDomain]]:
        if domain_path:
            return ServiceDomain.objects.filter(domain_name=domain_name, domain_path=domain_path).all()
        else:
            return None

    def get_domain_by_name_and_path_and_protocol(self, domain_name: str, domain_path: str,
                                                 protocol: str) -> Optional[QuerySet[ServiceDomain]]:
        if domain_path:
            return ServiceDomain.objects.filter(domain_name=domain_name, domain_path=domain_path, protocol=protocol).all()
        else:
            return None

    def delete_service_domain_by_port(self, service_id: str, container_port: int) -> None:
        ServiceDomain.objects.filter(service_id=service_id, container_port=container_port).delete()

    @staticmethod
    def list_service_domain_by_port(service_id: str, container_port: int) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.filter(service_id=service_id, container_port=container_port)

    def delete_service_domain(self, service_id: str) -> None:
        ServiceDomain.objects.filter(service_id=service_id).delete()

    def delete_service_domain_by_id(self, domain_id: str) -> None:
        ServiceDomain.objects.filter(ID=domain_id).delete()

    def get_tenant_certificate(self, tenant_id: str) -> QuerySet[ServiceDomainCertificate]:
        return ServiceDomainCertificate.objects.filter(tenant_id=tenant_id)

    def get_tenant_certificate_page(self, tenant_id: str, start: int, end: int,
                                    search_key: Optional[str] = None) -> Tuple[QuerySet[ServiceDomainCertificate], int]:
        """提供指定位置和数量的数据"""
        if search_key:
            # 如果有搜索关键字，按证书别名进行模糊搜索
            cert = ServiceDomainCertificate.objects.filter(
                tenant_id=tenant_id,
                alias__icontains=search_key
            )
        else:
            cert = ServiceDomainCertificate.objects.filter(tenant_id=tenant_id)
        
        nums = cert.count()  # 证书数量
        part_cert = cert[start:end + 1]
        return part_cert, nums

    def get_certificate_by_alias(self, tenant_id: str, alias: str) -> Optional[ServiceDomainCertificate]:
        sdc = ServiceDomainCertificate.objects.filter(tenant_id=tenant_id, alias=alias)
        if sdc:
            return sdc[0]
        return None

    def add_service_domain(self, **domain_info: Any) -> ServiceDomain:
        return ServiceDomain.objects.create(**domain_info)

    def get_certificate_by_pk(self, pk: int) -> Optional[ServiceDomainCertificate]:
        try:
            return ServiceDomainCertificate.objects.get(pk=pk)
        except ServiceDomainCertificate.DoesNotExist:
            return None

    def list_all_certificate(self) -> QuerySet[ServiceDomainCertificate]:
        return ServiceDomainCertificate.objects.all()

    def add_certificate(self, tenant_id: str, alias: str, certificate_id: str, certificate: str, private_key: str,
                        certificate_type: str) -> ServiceDomainCertificate:
        service_domain_certificate = dict()
        service_domain_certificate["tenant_id"] = tenant_id
        service_domain_certificate["certificate_id"] = certificate_id
        service_domain_certificate["certificate"] = certificate
        service_domain_certificate["private_key"] = private_key
        service_domain_certificate["alias"] = alias
        service_domain_certificate["certificate_type"] = certificate_type
        service_domain_certificate["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        certificate_info = ServiceDomainCertificate(**service_domain_certificate)
        certificate_info.save()
        return certificate_info

    def delete_certificate_by_alias(self, tenant_id: str, alias: str) -> None:
        ServiceDomainCertificate.objects.filter(tenant_id=tenant_id, alias=alias).delete()

    def delete_certificate_by_pk(self, pk: int) -> None:
        ServiceDomainCertificate.objects.filter(pk=pk).delete()

    def get_service_domains(self, service_id: str) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.filter(service_id=service_id).all()

    def get_service_domain_all(self) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.all()

    def create_service_domains(self, service_id: str, service_name: str, domain_name: str, create_time: Any,
                               container_port: int, protocol: str, http_rule_id: str, tenant_id: str,
                               service_alias: str, region_id: str) -> None:
        ServiceDomain.objects.create(
            service_id=service_id,
            service_name=service_name,
            domain_name=domain_name,
            create_time=create_time,
            container_port=container_port,
            protocol=protocol,
            http_rule_id=http_rule_id,
            tenant_id=tenant_id,
            service_alias=service_alias,
            region_id=region_id)

    def delete_http_domains(self, http_rule_id: str) -> None:
        ServiceDomain.objects.filter(http_rule_id=http_rule_id).delete()

    def check_custom_rule(self, eid: str) -> bool:
        """
        check if there is a custom gateway rule
        """
        conn = BaseConnection()
        team_name_query = "'%' || b.tenant_name || '%'"
        if os.environ.get('DB_TYPE') == 'mysql':
            team_name_query = "concat('%',b.tenant_name,'%')"
        sql = """
            SELECT
                *
            FROM
                service_domain a,
                tenant_info b
            WHERE
                a.tenant_id = b.tenant_id
                AND b.enterprise_id = "{eid}"
                AND (
                    a.certificate_id <> 0
                    OR ( a.domain_path <> "/" AND a.domain_path <> "" )
                    OR a.domain_cookie <> ""
                    OR a.domain_heander <> ""
                    OR a.the_weight <> 100
                    OR a.path_rewrite <> 0
                    OR a.rewrites <> ""
                    OR a.domain_name NOT LIKE {team_name}
                )
                LIMIT 1""".format(
            eid=eid, team_name=team_name_query)
        result = conn.query(sql)
        return True if len(result) > 0 else False

    def list_service_domains_by_cert_id(self, certificate_id: str) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.filter(certificate_id=certificate_id)

    @staticmethod
    def count_by_service_ids(region_id: str, service_ids: Any) -> int:
        return ServiceDomain.objects.filter(region_id=region_id, service_id__in=service_ids).count()

    @staticmethod
    def bulk_create(http_rules: Any) -> None:
        ServiceDomain.objects.bulk_create(http_rules)

    @staticmethod
    def list_by_component_ids(component_ids: Any) -> QuerySet[ServiceDomain]:
        return ServiceDomain.objects.filter(service_id__in=component_ids)


class ServiceExtendRepository(object):
    # only market service return extend_method
    def get_extend_method_by_service(self, service: TenantServiceInfo) -> Optional[ServiceExtendMethod]:
        if service.service_source == "market":
            # ServiceExtendMethod lives in www.models.service_publish (not in app registry seen by plugin)
            return ServiceExtendMethod.objects.filter(  # type: ignore[attr-defined]
                service_key=service.service_key,
                app_version=service.version,
            ).order_by("-ID").first()
        return None

    def create_extend_method(self, **params: Any) -> ServiceExtendMethod:
        service_key = params.get("service_key")
        app_version = params.get("app_version")
        if service_key is not None and app_version is not None:
            ServiceExtendMethod.objects.filter(  # type: ignore[attr-defined]
                service_key=service_key, app_version=app_version).delete()
        return ServiceExtendMethod.objects.create(**params)  # type: ignore[attr-defined]

    @staticmethod
    def bulk_create(extend_infos: Any) -> None:
        ServiceExtendMethod.objects.bulk_create(extend_infos)  # type: ignore[attr-defined]

    @staticmethod
    def _build_extend_method_delete_query(extend_infos: Any) -> Optional[Q]:
        delete_query = None
        ids = [ei.ID for ei in extend_infos if getattr(ei, "ID", None)]
        if ids:
            delete_query = Q(pk__in=ids)
        for extend_info in extend_infos:
            service_key = getattr(extend_info, "service_key", None)
            app_version = getattr(extend_info, "app_version", None)
            if service_key is None or app_version is None:
                continue
            business_query = Q(service_key=service_key, app_version=app_version)
            delete_query = business_query if delete_query is None else delete_query | business_query
        return delete_query

    def bulk_create_or_update(self, extend_infos: Any) -> None:
        delete_query = self._build_extend_method_delete_query(extend_infos)
        if delete_query is not None:
            ServiceExtendMethod.objects.filter(delete_query).delete()  # type: ignore[attr-defined]
        self.bulk_create(extend_infos)


class CompileEnvRepository(object):
    @staticmethod
    def list_by_component_ids(component_ids: Any) -> QuerySet[TenantServiceEnv]:
        return TenantServiceEnv.objects.filter(service_id__in=component_ids)

    def delete_service_compile_env(self, service_id: str) -> None:
        TenantServiceEnv.objects.filter(service_id=service_id).delete()

    def save_service_compile_env(self, **params: Any) -> TenantServiceEnv:
        return TenantServiceEnv.objects.create(**params)

    def get_service_compile_env(self, service_id: str) -> Optional[TenantServiceEnv]:
        tse = TenantServiceEnv.objects.filter(service_id=service_id)
        if tse:
            return tse[0]
        return None

    def update_service_compile_env(self, service_id: str, **update_params: Any) -> None:
        TenantServiceEnv.objects.filter(service_id=service_id).update(**update_params)

    def get_lang_version_in_use(self, lang: str, version: str) -> Optional[QuerySet[TenantServiceEnv]]:
        first_screening = TenantServiceEnv.objects.filter(user_dependency__icontains=version)
        if lang == "golang":
            return first_screening.filter(language="Go")
        if lang == "node":
            return first_screening.filter(language="Node.js")
        if lang == "web_compiler":
            return first_screening.filter(Q(language='Java-maven') | Q(language='Java-war'))
        if lang == "web_runtime":
            return first_screening.filter(Q(language='static') | Q(language='PHP'))
        if lang == "openJDK":
            return first_screening.filter(
                Q(language='Gradle') | Q(language='Java-maven') | Q(language='Java-jar') | Q(language='Java-war'))
        if lang == "maven":
            return first_screening.filter(language="Java-maven")
        if lang == "python":
            return first_screening.filter(language="Python")
        if lang == "net_runtime" or lang == "net_compiler":
            return first_screening.filter(language=".NetCore")
        if lang == "php":
            return first_screening.filter(language="PHP")
        return None


class ServiceAuthRepository(object):
    def delete_service_auth(self, service_id: str) -> None:
        TenantServiceAuth.objects.filter(service_id=service_id).delete()

    def get_service_auth(self, service_id: str) -> QuerySet[TenantServiceAuth]:
        return TenantServiceAuth.objects.filter(service_id=service_id)


class ServiceTcpDomainRepository(object):
    def get_service_tcp_domain_by_service_id(self, service_id: str) -> Optional[ServiceTcpDomain]:

        tcp_domain = ServiceTcpDomain.objects.filter(service_id=service_id).first()
        if tcp_domain:
            return tcp_domain
        else:
            return None

    def get_service_tcp_domain_by_service_id_and_port(self, service_id: str, container_port: int,
                                                      domain_name: str) -> Optional[ServiceTcpDomain]:
        tcp_domain = ServiceTcpDomain.objects.filter(
            service_id=service_id, container_port=container_port, end_point=domain_name).first()
        if tcp_domain:
            return tcp_domain
        else:
            return None

    def get_service_tcp_domains_by_service_id_and_port(self, service_id: str,
                                                       container_port: int) -> QuerySet[ServiceTcpDomain]:

        return ServiceTcpDomain.objects.filter(service_id=service_id, container_port=container_port)

    def get_all_domain_count_by_tenant_and_region(self, tenant_id: str, region_id: str) -> int:
        return ServiceTcpDomain.objects.filter(tenant_id=tenant_id, region_id=region_id).count()

    def delete_tcp_domain(self, tcp_rule_id: str) -> None:
        ServiceTcpDomain.objects.filter(tcp_rule_id=tcp_rule_id).delete()

    def create_service_tcp_domains(self, service_id: str, service_name: str, end_point: str, create_time: Any,
                                   container_port: int, protocol: str, service_alias: str, tcp_rule_id: str,
                                   tenant_id: str, region_id: str) -> None:
        ServiceTcpDomain.objects.create(
            service_id=service_id,
            service_name=service_name,
            end_point=end_point,
            create_time=create_time,
            service_alias=service_alias,
            container_port=container_port,
            protocol=protocol,
            tcp_rule_id=tcp_rule_id,
            tenant_id=tenant_id,
            region_id=region_id)

    def get_tcpdomain_by_name_and_port(self, service_id: str, container_port: int,
                                       end_point: str) -> Optional[ServiceTcpDomain]:
        try:
            return ServiceTcpDomain.objects.get(service_id=service_id, container_port=container_port, end_point=end_point)
        except ServiceTcpDomain.DoesNotExist:
            return None

    def get_tcpdomain_by_end_point(self, region_id: str, end_point: str) -> Optional[QuerySet[ServiceTcpDomain]]:
        try:
            hostport = end_point.split(":")
            if len(hostport) > 1:
                if hostport[0] == "0.0.0.0":
                    query = Q(region_id=region_id, end_point__icontains=":{}".format(hostport[1]))
                    return ServiceTcpDomain.objects.filter(query)
                query_default_endpoint = "0.0.0.0:{0}".format(hostport[1])
                query = Q(region_id=region_id, end_point=end_point) | Q(region_id=region_id, end_point=query_default_endpoint)
                return ServiceTcpDomain.objects.filter(query)
            return None
        except ServiceTcpDomain.DoesNotExist:
            return None

    def add_service_tcpdomain(self, **domain_info: Any) -> ServiceTcpDomain:
        return ServiceTcpDomain.objects.create(**domain_info)

    def get_service_tcpdomains(self, service_id: str) -> QuerySet[ServiceTcpDomain]:
        return ServiceTcpDomain.objects.filter(service_id=service_id).all()

    def get_service_tcpdomain_all(self) -> QuerySet[ServiceTcpDomain]:
        return ServiceTcpDomain.objects.all()

    def get_services_tcpdomains(self, service_ids: Any) -> QuerySet[ServiceTcpDomain]:
        return ServiceTcpDomain.objects.filter(service_id__in=service_ids)

    def get_service_tcpdomain_by_tcp_rule_id(self, tcp_rule_id: str) -> Optional[ServiceTcpDomain]:
        return ServiceTcpDomain.objects.filter(tcp_rule_id=tcp_rule_id).first()

    def delete_service_tcp_domain(self, service_id: str) -> None:
        ServiceTcpDomain.objects.filter(service_id=service_id).delete()

    def get_service_tcpdomain(self, tenant_id: str, region_id: str, service_id: str,
                              container_port: int) -> Optional[ServiceTcpDomain]:
        return ServiceTcpDomain.objects.filter(
            tenant_id=tenant_id, region_id=region_id, service_id=service_id, container_port=container_port).first()

    @staticmethod
    def count_by_service_ids(region_id: str, service_ids: Any) -> int:
        return ServiceTcpDomain.objects.filter(region_id=region_id, service_id__in=service_ids).count()

    @staticmethod
    def delete_by_component_port(component_id: str, port: int) -> None:
        ServiceTcpDomain.objects.filter(service_id=component_id, container_port=port).delete()

    @staticmethod
    def list_by_component_ids(component_ids: Any) -> QuerySet[ServiceTcpDomain]:
        return ServiceTcpDomain.objects.filter(service_id__in=component_ids)


class TenantServiceEndpoints(object):
    def get_service_endpoints_by_service_id(self, service_id: str) -> QuerySet[ThirdPartyServiceEndpoints]:
        return ThirdPartyServiceEndpoints.objects.filter(service_id=service_id)

    def update_or_create_endpoints(self, tenant: Tenants, service: TenantServiceInfo,
                                   service_endpoints: Any) -> Any:
        # reused for both QuerySet and the resolved model instance below
        endpoints: Any = self.get_service_endpoints_by_service_id(service.service_id)
        if not service_endpoints:
            endpoints.delete()
        elif endpoints:
            endpoints = endpoints.first()
            endpoints.endpoints_info = json.dumps(service_endpoints)
            endpoints.save()
        else:
            data = {
                "tenant_id": tenant.tenant_id,
                "service_id": service.service_id,
                "service_cname": service.service_cname,
                "endpoints_info": json.dumps(service_endpoints),
                "endpoints_type": "static"
            }
            endpoints = ThirdPartyServiceEndpoints.objects.create(**data)
        return endpoints

    def create_api_endpoints(self, tenant: Tenants, service: TenantServiceInfo) -> Optional[ThirdPartyServiceEndpoints]:
        endpoints = self.get_service_endpoints_by_service_id(service.service_id)
        if endpoints:
            return None
        data = {
            "tenant_id": tenant.tenant_id,
            "service_id": service.service_id,
            "service_cname": service.service_cname,
            "endpoints_info": "{}",
            "endpoints_type": "api"
        }
        return ThirdPartyServiceEndpoints.objects.create(**data)

    def create_kubernetes_endpoints(self, tenant: Tenants, component: TenantServiceInfo, service_name: str,
                                    namespace: str) -> Optional[ThirdPartyServiceEndpoints]:
        endpoints = self.get_service_endpoints_by_service_id(component.service_id)
        if endpoints:
            return None
        data = {
            "tenant_id": tenant.tenant_id,
            "service_id": component.service_id,
            "service_cname": component.service_cname,
            "endpoints_info": json.dumps({
                'serviceName': service_name,
                'namespace': namespace
            }),
            "endpoints_type": "kubernetes"
        }
        return ThirdPartyServiceEndpoints.objects.create(**data)

    @staticmethod
    def list_by_service_name(tenant_id: str, service_name: str) -> QuerySet[ThirdPartyServiceEndpoints]:
        return ThirdPartyServiceEndpoints.objects.filter(tenant_id=tenant_id, endpoints_info__contains=service_name)

    @staticmethod
    def bulk_create(endpoints: Any) -> None:
        ThirdPartyServiceEndpoints.objects.bulk_create(endpoints)

    @staticmethod
    def list_by_component_ids(component_ids: Any) -> QuerySet[ThirdPartyServiceEndpoints]:
        return ThirdPartyServiceEndpoints.objects.filter(service_id__in=component_ids)


class GatewayCustom(object):
    def get_configuration_by_rule_id(self, rule_id: str) -> Optional[GatewayCustomConfiguration]:
        return GatewayCustomConfiguration.objects.filter(rule_id=rule_id).first()

    def add_configuration(self, **configuration_info: Any) -> GatewayCustomConfiguration:
        return GatewayCustomConfiguration.objects.create(**configuration_info)

    @staticmethod
    def delete_by_rule_ids(rule_ids: Any) -> None:
        GatewayCustomConfiguration.objects.filter(rule_id__in=rule_ids).delete()

    @staticmethod
    def list_by_rule_ids(rule_ids: Any) -> QuerySet[GatewayCustomConfiguration]:
        return GatewayCustomConfiguration.objects.filter(rule_id__in=rule_ids)

    @staticmethod
    def bulk_create(configs: Any) -> None:
        GatewayCustomConfiguration.objects.bulk_create(configs)


tcp_domain = ServiceTcpDomainRepository()
env_var_repo = TenantServiceEnvVarRepository()
port_repo = TenantServicePortRepository()
domain_repo = ServiceDomainRepository()
volume_repo = TenantServiceVolumnRepository()
config_file_repo = ComponentConfigurationFileRepository()
mnt_repo = TenantServiceMntRelationRepository()
dep_relation_repo = TenantServiceRelationRepository()
extend_repo = ServiceExtendRepository()
compile_env_repo = CompileEnvRepository()
# 其他
auth_repo = ServiceAuthRepository()
# endpoints
service_endpoints_repo = TenantServiceEndpoints()
configuration_repo = GatewayCustom()
