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
            json_value = config.value
            array_value = json.loads(json_value)
            self.objects[config.key] = array_value

    def __getattr__(self, name):
        if name in self.objects:
            return self.objects[name]
        else:
            if hasattr(base_settings, name):
                return getattr(base_settings, name)
            else:
                return None

    def get_item(self, key):
        return self.objects.get(key)

    def reload(self):
        configs = ConsoleSysConfig.objects.all()
        for config in configs:
            json_value = config.value
            array_value = json.loads(json_value)
            self.objects[config.key] = array_value


settings = ConfigCenter()
