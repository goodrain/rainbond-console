# -*- coding: utf-8 -*-
import json

from console.repositories.config_repo import ConfigRepository


class ConfigService(object):
    def __init__(self):
        self.base_cfg_keys = ["REGION_SERVICE_API", "TITLE",
                              "REGISTER_STATUS", "RAINBOND_VERSION", "LOGO"]
        self.feature_cfg_keys = ["GITHUB_SERVICE_API", "GITLAB_SERVICE_API"]

    def list_by_keys(self, keys):
        cfg_repo = ConfigRepository()
        cfgs = cfg_repo.list_by_keys(keys)
        res = {}
        for item in cfgs:
            try:
                value = json.loads(item.value)
            except ValueError:
                value = item.value
            res[item.key] = value
        return res


config_service = ConfigService()
