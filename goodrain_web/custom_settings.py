import time
import random
import json
from addict import Dict
from django.conf import settings as base_settings
from cadmin.models.main import ConsoleSysConfig


class ConfigCenter(object):
    objects = {}

    def __init__(self):
        configs = ConsoleSysConfig.objects.all()
        for config in configs:
            if config.type == "json":
                self.objects[config.key] = json.loads(config.value)
            elif config.type == "list":
                self.objects[config.key] = json.loads(config.value)
            else:
                self.objects[config.key] = config.value

    def __getattr__(self, name):
        if name in self.objects:
            return self.objects[name]
        else:
            if hasattr(base_settings, name):
                return getattr(base_settings, name)
            else:
                return None

settings = ConfigCenter()
