# -*- coding: utf-8 -*-
import json
from datetime import datetime

from console.repositories.config_repo import cfg_repo
from openapi.models.main import CloundBangImages


class ConfigService(object):
    def __init__(self):
        # TODO: use enum
        self.base_cfg_keys = ["REGION_SERVICE_API", "TITLE", "enterprise_alias",
                              "REGISTER_STATUS", "RAINBOND_VERSION", "LOGO"]
        self.feature_cfg_keys = ["GITHUB", "GITLAB", "APPSTORE_IMAGE_HUB"]
        self.update_or_create_funcs = {
            "LOGO": self._update_or_create_logo,
        }

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
            k = k.upper()
            func = self.update_or_create_funcs.get(k, None)
            if func is None:
                # common way
                if isinstance(v, (dict, list)):
                    value = json.dumps(v)
                    cfg_repo.update_or_create_by_key(k, str(value))
                else:
                    cfg_repo.update_or_create_by_key(k, v)
            else:
                # special way
                func(k, v)

    def _update_or_create_logo(self, key, value):
        identify = "clound_bang_logo"
        try:
            cbi = CloundBangImages.objects.get(identify=identify)
            cbi.logo = value
            cbi.save()
        except CloundBangImages.DoesNotExsit:
            cbi = CloundBangImages(
                identify=identify,
                logo=value,
                create_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
            cbi.save()
        cfg_repo.update_or_create_by_key(key, value)


config_service = ConfigService()
