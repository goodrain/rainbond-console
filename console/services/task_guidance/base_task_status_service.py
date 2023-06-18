# -*- coding: utf8 -*-
import abc  # Python's built-in abstract class library
import logging

from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import domain_repo as http_rule_repo
from console.repositories.plugin import app_plugin_relation_repo
from console.repositories.service_repo import service_repo
from console.repositories.share_repo import share_repo
from www.db.service_group_repository import svc_grop_repo as svc_group_repo

logger = logging.getLogger("default")


class BaseTaskStatusStrategy(object, metaclass=abc.ABCMeta):
    """Abstract class: confirm the status of the base task"""
    @abc.abstractmethod
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
    def confirm_status(self, eid):
        return svc_group_repo.check_non_default_group_by_eid(eid)


class SourceCodeServiceCreationStrategy(BaseTaskStatusStrategy):
    """Task: create a service based on source code"""
    def confirm_status(self, eid):
        return service_repo.check_sourcecode_svc_by_eid(eid)


class InstallMysqlFromMarketStrategy(BaseTaskStatusStrategy):
    """Task: install the database based on the application market"""
    def confirm_status(self, eid):
        return service_repo.check_db_from_market_by_eid(eid)


class ServiceConnectDBStrategy(BaseTaskStatusStrategy):
    """Task: connect database with service"""
    def confirm_status(self, eid):
        return dep_relation_repo.check_db_dep_by_eid(eid)


class ShareAppStrategy(BaseTaskStatusStrategy):
    """Task: share application to market"""
    def confirm_status(self, eid):
        return share_repo.check_app_by_eid(eid)


class CustomGatewayRuleStrategy(BaseTaskStatusStrategy):
    """Task: customize application access rules"""
    def confirm_status(self, eid):
        return http_rule_repo.check_custom_rule(eid)


class InstallPluginStrategy(BaseTaskStatusStrategy):
    """Task: install the performance analysis plugin"""
    def confirm_status(self, eid):
        return app_plugin_relation_repo.check_plugins_by_eid(eid)


class ImageServiceCreateStrategy(BaseTaskStatusStrategy):
    """Task: install the performance analysis plugin"""
    def confirm_status(self, eid):
        return service_repo.check_image_svc_by_eid(eid)


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
        elif task == "image_service_create":
            self.strategy = ImageServiceCreateStrategy()
        else:
            logger.warning("Task: {task}; unsupported task".format(task=task))
            self.strategy = DefaultStrategy()

    def confirm_status(self):
        return self.strategy.confirm_status(self.eid)
