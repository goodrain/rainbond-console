# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, Optional

from django.db.models import QuerySet

from console.models.main import ConsoleSysConfig


class ConfigRepository(object):
    def list_by_keys(self, keys: Any) -> QuerySet:
        return ConsoleSysConfig.objects.filter(enable=True, key__in=keys)

    def delete_by_key(self, key: str) -> None:
        KEYS = [
            "OPEN_DATA_CENTER_STATUS", "NEWBIE_GUIDE", "DOCUMENT", "OFFICIAL_DEMO", "EXPORT_APP", "CLOUD_MARKET",
            "REGISTER_STATUS"
        ]
        cfg = ConsoleSysConfig.objects.get(key=key)
        if key in KEYS:
            cfg.value = "False"
            cfg.save()
        # if cfg.value == "DOCUMENT":
        #     cfg.value = {"enable": False}
        else:
            cfg.delete()

    def update_by_key(self, key: str, value: Any) -> int:
        return ConsoleSysConfig.objects.filter(key=key).update(value=value)

    def update_or_create_by_key(self, key: str, value: Any) -> None:
        ConsoleSysConfig.objects.update_or_create(
            key=key,
            defaults={
                "value": value,
                "type": "json",
                "desc": "git配置",
                "enable": True,
            },
        )

    def get_by_key(self, key: str) -> Optional[ConsoleSysConfig]:
        try:
            return ConsoleSysConfig.objects.get(key=key, enable=True)
        except ConsoleSysConfig.DoesNotExist:
            return None

    def get_by_value_eid(self, value: Any) -> ConsoleSysConfig:
        return ConsoleSysConfig.objects.get(value=value, enable=True)

    def create_token_record(self, key: str, value: Any, eid: str) -> ConsoleSysConfig:
        return ConsoleSysConfig.objects.create(
            key=key,
            value=value,
            type="string",
            desc="helm对接集群唯一标识",
            enable=True,
            enterprise_id=eid,
            create_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


cfg_repo = ConfigRepository()
