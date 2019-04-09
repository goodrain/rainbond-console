# -*- coding: utf8 -*-
import logging
import json

from console.services.service_group_service import service_group_service
from console.services.team_services import team_services
from console.repositories.service_repo import service_repo
from console.repositories.app_config import dep_relation_repo, domain_repo as http_rule_repo
from console.repositories.share_repo import share_repo
from console.repositories.plugin import app_plugin_relation_repo

logger = logging.getLogger("default")


class BaseTaskStatusStrategy(object):
    """Abstract class: confirm the status of the base task"""

    def confirm_status(self, tenants):
        raise NotImplementedError("Doesn't provide a reprØesentation for BaseTaskStatus.")


class DefaultStrategy(BaseTaskStatusStrategy):
    """
    The duty of DefaultStrategy is to avoid the lack of strategy for the instance
    of BaseTaskStatusContext.
    When the BaseTaskStatusContext is initialized, if an unsupported task is entered,
    the above error will be triggered.
    """

    def confirm_status(self, tenants):
        return False


class AppCreationStrategy(BaseTaskStatusStrategy):
    """Task: app creation"""

    def confirm_status(self, tenants):
        return service_group_service.has_created_app(tenants)


class SourceCodeServiceCreationStrategy(BaseTaskStatusStrategy):
    """Task: create a service based on source code"""

    def confirm_status(self, tenants):
        for tenant in tenants:
            if service_repo.count_sourcecode_svc_by_tenant(tenant) > 0:
                return True
        return False


class InstallMysqlFromMarketStrategy(BaseTaskStatusStrategy):
    """Task: install the database based on the application market"""

    def confirm_status(self, tenants):
        for tenant in tenants:
            if len(service_repo.list_db_from_market_by_tenant(tenant)) > 0:
                return True
        return False


class ServiceConnectDBStrategy(BaseTaskStatusStrategy):
    """Task: connect database with service"""

    def confirm_status(self, tenants):
        for tenant in tenants:
            services = service_repo.list_db_from_market_by_tenant(tenant)
            for svc in services:
                dep = dep_relation_repo.get_dependency_by_dep_id(tenant_id=svc["tenant_id"],
                                                                 dep_service_id=svc["service_id"])
                if dep:
                    return True
        return False


class ShareAppStrategy(BaseTaskStatusStrategy):
    """Task: share application to market"""

    def confirm_status(self, tenants):
        for tenant in tenants:
            if share_repo.count_app_by_team_name(tenant.tenant_name) > 0:
                return True
        return False


class CustomGatewayRuleStrategy(BaseTaskStatusStrategy):
    """Task: customize application access rules"""

    def confirm_status(self, tenants):
        for tenant in tenants:
            rules = http_rule_repo.list_rules_by_tenant(tenant)
            for rule in rules:
                if rule.certificate_id != 0:
                    return True
                if rule.domain_path != "/":
                    return True
                if rule.domain_cookie:
                    return True
                if rule.domain_heander:
                    return True
                if rule.the_weight != 100:
                    return True
                # TODO: domain
                # if not rule.domain_name.contains(tenant.tenant_name):
                #     return True
        return False


class InstallPluginStrategy(BaseTaskStatusStrategy):
    """Task: install the performance analysis plugin"""

    def confirm_status(self, tenants):
        for tenant in tenants:
            services = service_repo.list_svc_by_tenant(tenant)
            for svc in services:
                if app_plugin_relation_repo.count_plugins_by_tenant(svc.service_id) > 0:
                    return True
        return False


class BaseTaskStatusContext(object):
    def __init__(self, eid, task):
        self.eid = eid
        if task == 'app_create':
            self.strategy = AppCreationStrategy()
        elif task == 'source_code_service_create':
            self.strategy = SourceCodeServiceCreationStrategy()
        elif task == 'install_mysql_from_market':
            self.strategy = InstallMysqlFromMarketStrategy()
        elif task == 'service_connect_db':
            self.strategy = ServiceConnectDBStrategy()
        elif task == 'share_app':
            self.strategy = ShareAppStrategy()
        elif task == 'custom_gw_rule':
            self.strategy = CustomGatewayRuleStrategy()
        elif task == 'install_plugin':
            self.strategy = InstallPluginStrategy()
        else:
            logger.warning("Task: {}; unsupported task", task)
            self.strategy = DefaultStrategy()

    def confirm_status(self):
        tenants = team_services.get_enterprise_teams(self.eid)
        return self.strategy.confirm_status(tenants)
