# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
import json
import logging
from typing import Any, List, Tuple

from console.exception.main import (InnerPortNotFound, ServiceHandleException, ServiceRelationAlreadyExist)
from console.repositories.app import service_repo
from console.repositories.app_config import (dep_relation_repo, env_var_repo, port_repo)
from console.repositories.k8s_attribute import k8s_attribute_repo
from console.services.app_config.port_service import AppPortService
from console.services.exception import ErrDepServiceNotFound
from console.services.group_service import group_service
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, Tenants

region_api = RegionInvokeApi()
port_service = AppPortService()
logger = logging.getLogger("default")


class AppServiceRelationService(object):
    def __get_dep_service_ids(self, tenant: Tenants, service: TenantServiceInfo) -> Any:
        return dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id).values_list(
            "dep_service_id", flat=True)

    def get_service_dependencies_part(self, dep_ids: Any) -> Any:
        services = service_repo.get_services_by_service_ids(dep_ids)
        return services

    def json_service_dependency(self, dependencies: Any, service_ids: Any) -> str:
        service_dependency_list = list()
        service_group_map = group_service.get_services_group_name(service_ids)
        for dependencie in dependencies:
            service_dependency_dict = dict()
            service_dependency_dict["所属应用"] = service_group_map[dependencie.service_id]["group_name"]
            service_dependency_dict["组件名"] = dependencie.service_cname
            service_dependency_list.append(service_dependency_dict)
        return json.dumps(service_dependency_list, ensure_ascii=False)


    def get_dep_service_ids(self, service: TenantServiceInfo) -> Any:
        return dep_relation_repo.get_service_dependencies(service.tenant_id, service.service_id).values_list(
            "dep_service_id", flat=True)

    def get_service_dependencies(self, tenant: Tenants, service: TenantServiceInfo) -> Any:
        dep_ids = self.__get_dep_service_ids(tenant, service)
        services = service_repo.get_services_by_service_ids(dep_ids)
        return services

    def get_service_dependencies_reverse(self, service: TenantServiceInfo) -> Any:
        dep_ids = dep_relation_repo.get_service_reverse_dependencies(service.tenant_id, service.service_id).values_list(
            "service_id", flat=True)
        services = service_repo.get_services_by_service_ids(dep_ids)
        return services

    def get_undependencies(self, tenant: Tenants, service: TenantServiceInfo) -> List[Any]:

        # 打开对内端口才能被依赖
        services = service_repo.get_tenant_region_services(service.service_region,
                                                           tenant.tenant_id).exclude(service_id=service.service_id)
        not_dependencies = []
        dep_services = dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id)
        dep_service_ids = [dep.dep_service_id for dep in dep_services]
        for s in services:
            # 查找打开内部访问的组件
            open_inner_services = port_repo.get_service_ports(tenant.tenant_id, s.service_id).filter(is_inner_service=True)
            if open_inner_services:
                if s.service_id not in dep_service_ids:
                    not_dependencies.append(s)
        return not_dependencies

    # 查找所有的组件，看谁能依赖自己，要排除掉已经依赖自己的组件
    def get_reverse_undependencies(self, tenant: Tenants, service: TenantServiceInfo) -> List[Any]:
        # 查找到所有的组件信息
        services = service_repo.get_tenant_region_services(service.service_region,
                                                           tenant.tenant_id).exclude(service_id=service.service_id)
        not_dependencies = []
        dep_services = dep_relation_repo.get_service_reverse_dependencies(tenant.tenant_id, service.service_id)
        dep_service_ids = [dep.service_id for dep in dep_services]
        for s in services:
            if s.service_id not in dep_service_ids:
                not_dependencies.append(s)
        return not_dependencies

    def __is_env_duplicate(self, tenant: Tenants, service: TenantServiceInfo, dep_service: TenantServiceInfo) -> bool:
        dep_ids = self.__get_dep_service_ids(tenant, service)
        attr_names = env_var_repo.get_service_env(tenant.tenant_id, dep_service.service_id).filter(scope="outer").values_list(
            "attr_name", flat=True)
        envs = env_var_repo.get_env_by_ids_and_attr_names(dep_service.tenant_id, dep_ids, attr_names).filter(scope="outer")
        if envs:
            return True
        return False

    def check_relation(self, tenant_id: str, service_id: str, dep_service_id: str) -> None:
        """
        when creating service dependency, the dependent service needs to have an inner port.
        """
        dep_service = service_repo.get_service_by_service_id(dep_service_id)
        if dep_service is None:
            raise ErrDepServiceNotFound(dep_service_id)
        dep_service_relation = dep_relation_repo.get_depency_by_serivce_id_and_dep_service_id(
            tenant_id, service_id, dep_service_id)
        if dep_service_relation:
            raise ServiceRelationAlreadyExist()
        open_inner_services = port_repo.list_inner_ports(tenant_id, dep_service_id)
        if not open_inner_services:
            raise InnerPortNotFound()

    def create_service_relation(self, tenant: Tenants, service: TenantServiceInfo, dep_service_id: str) -> Any:
        """
        raise ErrDepServiceNotFound
        raise ServiceRelationAlreadyExist
        raise InnerPortNotFound
        """
        self.check_relation(service.tenant_id, service.service_id, dep_service_id)
        dep_service = service_repo.get_service_by_tenant_and_id(tenant.tenant_id, dep_service_id)
        tenant_service_relation = {
            "tenant_id": tenant.tenant_id,
            "service_id": service.service_id,
            "dep_service_id": dep_service_id,
            # NOTE: get_service_by_tenant_and_id may return None; unguarded deref (potential latent None-bug).
            "dep_service_type": dep_service.service_type,  # type: ignore[union-attr]
            "dep_order": 0,
        }
        return dep_relation_repo.add_service_dependency(**tenant_service_relation)

    def __open_port(self, tenant: Tenants, dep_service: TenantServiceInfo, container_port: Any,
                    user_name: str = '') -> None:
        open_service_ports = []
        if container_port:
            tenant_service_port = port_service.get_service_port_by_port(dep_service, int(container_port))
            if not tenant_service_port:
                raise ServiceHandleException(
                    msg="invalid dependency container port",
                    msg_show="container_port 必须是被依赖组件的实际端口",
                    status_code=400,
                    details={
                        "field": "container_port",
                        "reason": "not_found_on_dependency_service",
                        "provided_value": int(container_port),
                        "dep_service_id": dep_service.service_id,
                        "suggestion": "请先查看被依赖组件的端口列表，再传该组件真实存在的 container_port。",
                        "retryable": False,
                    },
                )
            open_service_ports.append(tenant_service_port)
        else:
            # dep component not have inner port, will open all port
            ports = port_service.get_service_ports(dep_service)
            if ports:
                have_inner_port = False
                for port in ports:
                    if port.is_inner_service:
                        have_inner_port = True
                        break
                if not have_inner_port:
                    open_service_ports.extend(ports)

        for tenant_service_port in open_service_ports:
            try:
                code, msg, data = port_service.manage_port(tenant, dep_service, dep_service.service_region,
                                                           int(tenant_service_port.container_port), "open_inner",
                                                           tenant_service_port.protocol, tenant_service_port.port_alias,
                                                           user_name)
                if code != 200:
                    logger.warning("auto open depend service inner port faliure {}".format(msg))
                else:
                    logger.debug("auto open depend service inner port success ")
            except ServiceHandleException as e:
                logger.exception(e)
                if e.status_code != 404:
                    raise e

    def patch_add_service_reverse_dependency(self, tenant: Tenants, service: TenantServiceInfo, be_dep_service_ids: str,
                                             user_name: str = '') -> List[dict]:
        # NOTE: dict holds Optional[str] model fields (service_type/enterprise_id); untyped values.
        task: dict = dict()
        task["be_dep_service_ids"] = be_dep_service_ids
        task["tenant_id"] = tenant.tenant_id
        task["dep_service_type"] = service.service_type
        task["enterprise_id"] = tenant.enterprise_id
        task["operator"] = user_name
        region_api.add_service_dependencys(service.service_region, tenant.tenant_name, service.service_alias, task)
        res = []
        for be_dep_service_id in be_dep_service_ids.split(','):
            tenant_service_relation = {
                "tenant_id": tenant.tenant_id,
                "service_id": be_dep_service_id,
                "dep_service_id": service.service_id,
                "dep_service_type": service.service_type,
                "dep_order": 0,
            }
            res.append(tenant_service_relation)
        data = dep_relation_repo.bulk_add_service_dependency(res)
        return [item.to_dict() for item in data]

    def add_service_dependency(self, tenant: Tenants, service: TenantServiceInfo, dep_service_id: str, open_inner: Any = None,
                               container_port: Any = None, user_name: str = '') -> Tuple[int, str, Any]:
        dep_service_relation = dep_relation_repo.get_depency_by_serivce_id_and_dep_service_id(
            tenant.tenant_id, service.service_id, dep_service_id)
        if dep_service_relation:
            return 212, "当前组件已被关联", None

        dep_service = service_repo.get_service_by_tenant_and_id(tenant.tenant_id, dep_service_id)
        if not dep_service:
            raise ServiceHandleException(
                msg="dependency service not found",
                msg_show="要关联的组件不存在",
                status_code=404,
                details={
                    "field": "dep_service_id",
                    "reason": "not_found",
                    "provided_value": dep_service_id,
                    "retryable": False,
                },
            )
        # 开启对内端口
        if open_inner:
            self.__open_port(tenant, dep_service, container_port, user_name)
        else:
            # 校验要依赖的组件是否开启了对内端口
            open_inner_services = port_repo.get_service_ports(tenant.tenant_id,
                                                              dep_service.service_id).filter(is_inner_service=True)
            if not open_inner_services:
                service_ports = port_repo.get_service_ports(tenant.tenant_id, dep_service.service_id)
                port_list = [service_port.container_port for service_port in service_ports]
                return 201, "要关联的组件暂未开启对内端口，是否打开", port_list

        is_duplicate = self.__is_env_duplicate(tenant, service, dep_service)
        if is_duplicate:
            return 412, "要关联的组件的变量与已关联的组件变量重复，请修改后再试", None
        dep_sa_name = k8s_attribute_repo.get_by_component_id_name(service.service_id, "serviceAccountName")
        if service.create_status == "complete":
            # NOTE: dict holds Optional[str] model fields (service_type/enterprise_id); untyped values.
            task: dict = dict()
            task["dep_service_id"] = dep_service_id
            task["tenant_id"] = tenant.tenant_id
            task["dep_service_type"] = dep_service.service_type
            task["enterprise_id"] = tenant.enterprise_id
            task["operator"] = user_name
            task["namespace"] = tenant.namespace
            task["dep_sa_name"] = dep_sa_name[0].attribute_value if len(dep_sa_name) > 0 else ""
            region_api.add_service_dependency(service.service_region, tenant.tenant_name, service.service_alias, task)
        tenant_service_relation = {
            "tenant_id": tenant.tenant_id,
            "service_id": service.service_id,
            "dep_service_id": dep_service_id,
            "dep_service_type": dep_service.service_type,
            "dep_order": 0,
        }
        dep_relation = dep_relation_repo.add_service_dependency(**tenant_service_relation)
        # component dependency change, will change export network governance plugin configuration
        if service.create_status == "complete":
            from console.services.plugin import app_plugin_service
            app_plugin_service.update_config_if_have_export_plugin(tenant, service)
        return 200, "success", dep_relation

    def patch_add_dependency(self, tenant: Tenants, service: TenantServiceInfo, dep_service_ids: Any,
                             user_name: str = '') -> Tuple[int, str]:
        dep_service_relations = dep_relation_repo.get_dependency_by_dep_service_ids(tenant.tenant_id, service.service_id,
                                                                                    dep_service_ids)
        dep_ids = [dep.dep_service_id for dep in dep_service_relations]
        services = service_repo.get_services_by_service_ids(dep_ids)
        if dep_service_relations:
            service_cnames = [s.service_cname for s in services]
            return 412, "组件{0}已被关联".format(service_cnames)
        for dep_id in dep_service_ids:
            code, msg, relation = self.add_service_dependency(tenant, service, dep_id, user_name=user_name)
            if code != 200:
                return code, msg
        return 200, "success"

    def delete_service_dependency(self, tenant: Tenants, service: TenantServiceInfo, dep_service_id: str,
                                  user_name: str = '') -> Tuple[int, str, Any]:
        dependency = dep_relation_repo.get_depency_by_serivce_id_and_dep_service_id(tenant.tenant_id, service.service_id,
                                                                                    dep_service_id)
        if not dependency:
            return 404, "需要删除的依赖不存在", None
        dep_sa_name = k8s_attribute_repo.get_by_component_id_name(service.service_id, "serviceAccountName")
        if service.create_status == "complete":
            # NOTE: dict holds Optional[str] model fields (enterprise_id/namespace); untyped values.
            task: dict = dict()
            task["dep_service_id"] = dep_service_id
            task["tenant_id"] = tenant.tenant_id
            task["dep_service_type"] = "v"
            task["enterprise_id"] = tenant.enterprise_id
            task["namespace"] = tenant.namespace
            task["dep_sa_name"] = dep_sa_name[0].attribute_value if len(dep_sa_name) > 0 else ""
            task["operator"] = user_name

            region_api.delete_service_dependency(service.service_region, tenant.tenant_name, service.service_alias, task)

        dependency.delete()
        # component dependency change, will change export network governance plugin configuration
        if service.create_status == "complete":
            from console.services.plugin import app_plugin_service
            app_plugin_service.update_config_if_have_export_plugin(tenant, service)
        return 200, "success", dependency

    def delete_region_dependency(self, tenant: Tenants, service: TenantServiceInfo) -> None:
        deps = self.__get_dep_service_ids(tenant, service)
        for dep_id in deps:
            task = {}
            task["dep_service_id"] = dep_id
            task["tenant_id"] = tenant.tenant_id
            task["dep_service_type"] = "v"
            task["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.delete_service_dependency(service.service_region, tenant.tenant_name, service.service_alias, task)
            except Exception as e:
                logger.exception(e)

    def get_services_dependend_on_current_services(self, tenant: Tenants, service: TenantServiceInfo) -> Any:
        relations = dep_relation_repo.get_services_dep_current_service(tenant.tenant_id, service.service_id)
        service_ids = [r.service_id for r in relations]
        return service_repo.get_services_by_service_ids(service_ids)
