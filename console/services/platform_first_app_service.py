# -*- coding: utf-8 -*-
import logging
from typing import Any, Optional

from console.models.main import ConsoleSysConfig
from www.models.main import TenantServiceInfo


FIRST_APP_DEPLOYED_KEY = "FIRST_APP_DEPLOYED"
logger = logging.getLogger("default")


class PlatformFirstAppService(object):
    def __init__(self) -> None:
        self._deployed_cache = False

    def is_deployed(self) -> bool:
        if self._deployed_cache:
            return True
        config = self._get_config()
        if config is None:
            config = self._initialize_config(TenantServiceInfo.objects.exists())
        deployed = config.value == "1"
        if deployed:
            self._deployed_cache = True
        return deployed

    def mark_deployed(self) -> None:
        if self._deployed_cache:
            return
        config = self._get_config()
        if config is None:
            config = self._create_config(True)
        if config.value != "1":
            config.value = "1"
            config.save(update_fields=["value"])
        self._deployed_cache = True

    @staticmethod
    def is_running_status(status_map: Any) -> bool:
        return isinstance(status_map, dict) and status_map.get("status") == "running"

    def safe_mark_if_running(self, status_map: Any) -> None:
        if not self.is_running_status(status_map):
            return
        try:
            self.mark_deployed()
        except Exception:
            logger.exception("failed to mark platform first app as deployed")

    @staticmethod
    def _get_config() -> Optional[ConsoleSysConfig]:
        try:
            return ConsoleSysConfig.objects.get(key=FIRST_APP_DEPLOYED_KEY, enterprise_id="")
        except ConsoleSysConfig.DoesNotExist:
            return None

    def _initialize_config(self, deployed: bool) -> ConsoleSysConfig:
        return self._create_config(deployed)

    def _create_config(self, deployed: bool) -> ConsoleSysConfig:
        config, _ = ConsoleSysConfig.objects.get_or_create(
            key=FIRST_APP_DEPLOYED_KEY,
            enterprise_id="",
            defaults={
                "type": "bool",
                "value": "1" if deployed else "0",
                "enable": True,
            },
        )
        return config


platform_first_app_service = PlatformFirstAppService()
