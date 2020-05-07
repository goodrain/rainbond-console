# -*- coding: utf-8 -*-
# creater by: barnett
import logging
import copy

from console.services.service_services import base_service
from console.services.group_service import group_service
from console.services.team_services import team_services
from console.services.app_actions import app_manage_service
from console.repositories.app_config import domain_repo

from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.team_repo import team_repo
from console.repositories.app import service_repo
from console.services.app import app_service as console_app_service

logger = logging.getLogger("default")


class AppService(object):
    def get_app_status(self, app):
        services = group_service.get_group_services(app.ID)
        service_ids = [service.service_id for service in services]
        team = team_services.get_team_by_team_id(app.tenant_id)
        status_list = base_service.status_multi_service(
            region=app.region_name, tenant_name=team.tenant_name, service_ids=service_ids, enterprise_id=team.enterprise_id)
        # As long as there is a service running, the application thinks it is running
        app_status = "closed"
        for status in status_list:
            if status["status"] == "running":
                app_status = "running"
        if not service_ids:
            app_status = "notinstall"
        return app_status, services

    def get_group_services_by_id(self, group_id):
        service_group = group_repo.get_group_by_id(group_id)
        if not service_group:
            return None, None
        tenant = team_repo.get_team_by_team_id(service_group.tenant_id)
        services = group_service_relation_repo.get_services_by_group(group_id)
        if not services:
            return tenant, []
        service_ids = [service.service_id for service in services]
        cp_service_ids = copy.copy(service_ids)
        for service_id in cp_service_ids:
            service_obj = service_repo.get_service_by_service_id(service_id)
            if service_obj:
                if service_obj.service_source == "third_party":
                    service_ids.remove(service_id)
        return tenant, service_ids

    def get_services_by_group_id(self, group_id):
        return group_service_relation_repo.get_services_by_group(group_id)

    def group_services_operation(self, tenant, action, service_ids):
        return app_manage_service.batch_operations(tenant, None, action, service_ids)

    def get_service_by_service_key_and_group_id(self, service_key, group_id):
        rst = None
        services = group_service_relation_repo.get_services_by_group(group_id)
        if not services:
            return rst
        service_ids = [service.service_id for service in services]
        services = service_repo.get_services_by_service_ids(service_ids)
        if not services:
            return rst
        for service in services:
            if service.service_key == service_key:
                rst = service
            break
        return rst

    def get_tenant_by_group_id(self, group_id):
        service_group = group_repo.get_group_by_id(group_id)
        if not service_group:
            return None
        try:
            tenant = team_repo.get_team_by_team_id(service_group.tenant_id)
            return tenant
        except Exception:
            return None

    def check_strategy_exist(self, service, container_port, domain_name, protocol, domain_path, rule_extensions):
        rst = False
        http_exist = False
        add_httptohttps = False
        service_domain = domain_repo.get_domain_by_name_and_port_and_protocol(service.service_id, container_port, domain_name,
                                                                              protocol, domain_path)
        if service_domain:
            rst = True
        domains = domain_repo.get_domain_by_name_and_path(domain_name, domain_path)
        for domain in domains:
            if "http" == domain.protocol:
                http_exist = True
            if "httptohttps" in domain.rule_extensions:
                rst = True
        if rule_extensions:
            for rule in rule_extensions:
                if rule["key"] == "httptohttps":
                    add_httptohttps = True
        if http_exist and add_httptohttps:
            rst = True
        return rst

    def get_app_service_count(self, group_id):
        services = group_service_relation_repo.get_services_by_group(group_id)
        if not services:
            return 0
        return len(services)

    def get_app_running_service_count(self, tenant, services):
        count = 0
        for service in services:
            detail = console_app_service.get_service_status(tenant, service)
            if detail["status"] == "running":
                count += 1
        return count

    def get_app_memory_and_cpu_used(self, services):
        memory = 0
        cpu = 0
        for service in services:
            memory += service.min_memory
            cpu += service.min_memory / 128 * 30
        return cpu, memory


app_service = AppService()
