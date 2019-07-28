# -*- coding: utf-8 -*-
import json

from console.repositories.config_repo import cfg_repo


class ConfigService(object):
    def __init__(self):
        self.base_cfg_keys = ["REGION_SERVICE_API", "TITLE",
                              "REGISTER_STATUS", "RAINBOND_VERSION", "LOGO"]
        self.feature_cfg_keys = ["GITHUB_SERVICE_API", "GITLAB_SERVICE_API"]

    def list_by_keys(self, keys):
        cfgs = cfg_repo.list_by_keys(keys)
        res = {}
        for item in cfgs:
            try:
                value = json.loads(item.value)
            except ValueError:
                value = item.value
            res[item.key] = value
        return res

    def update_or_create(self, data):
        for k, v in data.iteritems():
            if isinstance(v, (dict, list)):
                value = json.dumps(v)
                cfg_repo.update_or_create_by_key(k, str(value))
            else:
                cfg_repo.update_or_create_by_key(k, v)


config_service = ConfigService()
