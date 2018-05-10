# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
from console.repositories.app_config import dep_relation_repo, port_repo, env_var_repo
from console.repositories.app import service_repo

from www.apiclient.regionapi import RegionInvokeApi
import logging

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppServiceRelationService(object):
    def __get_dep_service_ids(self, tenant, service):
        return dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id).values_list(
            "dep_service_id", flat=True)

    def get_dep_service_ids(self, service):
        return dep_relation_repo.get_service_dependencies(service.tenant_id, service.service_id).values_list(
            "dep_service_id", flat=True)

    def get_service_dependencies(self, tenant, service):
        dep_ids = self.__get_dep_service_ids(tenant, service)
        services = service_repo.get_services_by_service_ids(*dep_ids)
        return services

    def get_undependencies(self, tenant, service):

        # 打开对内端口才能被依赖
        services = service_repo.get_tenant_region_services(service.service_region, tenant.tenant_id).exclude(
            service_id=service.service_id)
        not_dependencies = []
        dep_services = dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id)
        dep_service_ids = [dep.dep_service_id for dep in dep_services]
        for s in services:
            # 查找打开内部访问的应用
            open_inner_services = port_repo.get_service_ports(tenant.tenant_id, s.service_id).filter(
                is_inner_service=True)
            if open_inner_services:
                if s.service_id not in dep_service_ids:
                    not_dependencies.append(s)
        return not_dependencies

    def __is_env_duplicate(self, tenant, service, dep_service):
        dep_ids = self.__get_dep_service_ids(tenant, service)
        attr_names = env_var_repo.get_service_env(tenant.tenant_id, dep_service.service_id).filter(
            scope="outer").values_list("attr_name",
                                       flat=True)
        envs = env_var_repo.get_env_by_ids_and_attr_names(dep_service.tenant_id, dep_ids, attr_names).filter(
            scope="outer")
        if envs:
            return True
        return False

    def add_service_dependency(self, tenant, service, dep_service_id):
        dep_service_relation = dep_relation_repo.get_depency_by_serivce_id_and_dep_service_id(tenant.tenant_id,
                                                                                              service.service_id,
                                                                                              dep_service_id)
        if dep_service_relation:
            return 412, u"当前应用已被关联", None

        dep_service = service_repo.get_service_by_tenant_and_id(tenant.tenant_id, dep_service_id)

        is_duplicate = self.__is_env_duplicate(tenant, service, dep_service)
        if is_duplicate:
            return 412, u"要关联的应用的变量与已关联的应用变量重复，请修改后再试", None
        if service.create_status == "complete":
            task = {}
            task["dep_service_id"] = dep_service_id
            task["tenant_id"] = tenant.tenant_id
            task["dep_service_type"] = dep_service.service_type
            task["enterprise_id"] = tenant.enterprise_id

            region_api.add_service_dependency(service.service_region, tenant.tenant_name, service.service_alias, task)
        tenant_service_relation = {
            "tenant_id": tenant.tenant_id,
            "service_id": service.service_id,
            "dep_service_id": dep_service_id,
            "dep_service_type": dep_service.service_type,
            "dep_order": 0,
        }
        dep_relation = dep_relation_repo.add_service_dependency(**tenant_service_relation)
        return 200, u"success", dep_relation

    def patch_add_dependency(self, tenant, service, dep_service_ids):
        dep_service_relations = dep_relation_repo.get_dependency_by_dep_service_ids(tenant.tenant_id,
                                                                                    service.service_id, dep_service_ids)
        dep_ids = [dep.dep_service_id for dep in dep_service_relations]
        services = service_repo.get_services_by_service_ids(*dep_ids)
        if dep_service_relations:
            service_cnames = [s.service_cname for s in services]
            return 412, u"应用{0}已被关联".format(service_cnames)
        for dep_id in dep_service_ids:
            code, msg, relation = self.add_service_dependency(tenant, service, dep_id)
            if code != 200:
                return code, msg
        return 200, u"success"

    def delete_service_dependency(self, tenant, service, dep_service_id):
        dependency = dep_relation_repo.get_depency_by_serivce_id_and_dep_service_id(tenant.tenant_id,
                                                                                    service.service_id,
                                                                                    dep_service_id)
        if not dependency:
            return 404, u"需要删除的依赖不存在", None
        if service.create_status == "complete":
            task = {}
            task["dep_service_id"] = dep_service_id
            task["tenant_id"] = tenant.tenant_id
            task["dep_service_type"] = "v"
            task["enterprise_id"] = tenant.enterprise_id

            region_api.delete_service_dependency(service.service_region, tenant.tenant_name, service.service_alias,
                                                 task)

        dependency.delete()
        return 200, u"success", dependency

    def delete_region_dependency(self, tenant, service):
        deps = self.__get_dep_service_ids(tenant, service)
        for dep_id in deps:
            task = {}
            task["dep_service_id"] = dep_id
            task["tenant_id"] = tenant.tenant_id
            task["dep_service_type"] = "v"
            task["enterprise_id"] = tenant.enterprise_id
            try:
                region_api.delete_service_dependency(service.service_region, tenant.tenant_name, service.service_alias,
                                                     task)
            except Exception as e:
                logger.exception(e)

    def get_services_dependend_on_current_services(self, tenant, service):
        relations = dep_relation_repo.get_services_dep_current_service(tenant.tenant_id, service.service_id)
        service_ids = [r.service_id for r in relations]
        return service_repo.get_services_by_service_ids(*service_ids)