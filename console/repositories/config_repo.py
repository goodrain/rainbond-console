# -*- coding: utf-8 -*-
from console.models.main import ConsoleSysConfig


class ConfigRepository(object):
    def list_by_keys(self, keys):
        return ConsoleSysConfig.objects.filter(enable=True, key__in=keys)

    def update_by_key(self, key, value):
        return ConsoleSysConfig.objects.filter(key=key).update(value=value)


cfg_repo = ConfigRepository()
