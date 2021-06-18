# -*- coding: utf8 -*-
import logging

from django.db import transaction

from .app import MarketApp
# service
from console.services.app_actions import app_manage_service
# exception
from console.exception.main import ServiceHandleException
# model
from www.models.main import ServiceGroup
from www.models.main import TenantServiceGroup

logger = logging.getLogger("default")


class AppInstall(MarketApp):
    def __init__(
            self,
            tenant,
            region_name,
            user,
    ):
        self.tenant = tenant
        self.region_name = region_name
        self.user = user

        original_app = None  # TODO(huangrh)
        super(AppInstall, self).__init__(original_app, self.new_app)

    def install(self):
        # Sync the new application to the data center first
        # TODO(huangrh): rollback on api timeout
        self.sync_new_app()

        try:
            # Save the application to the console
            self.save_new_app()
        except Exception as e:
            logger.exception(e)
            # rollback on failure
            self.rollback()
            raise ServiceHandleException("unexpected error", "升级遇到了故障, 暂无法执行, 请稍后重试")

        self._deploy()

    def _deploy(self):
        component_ids = [cpt.component.component_id for cpt in self.new_app.components()]
        try:
            _ = app_manage_service.batch_operations(self.tenant, self.region_name, self.user, "deploy", component_ids)
        except Exception as e:
            logger.exception(e)
            raise ServiceHandleException(msg="install app failure", msg_show="安装应用发生异常，请稍后重试")
