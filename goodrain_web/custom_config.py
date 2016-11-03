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
    
    def configs(self):
        return self.objects

    def reload(self):
        configs = ConsoleSysConfig.objects.all()
        for config in configs:
            if config.type == "int":
                c_value = int(config.value)
            elif config.type == "list":
                c_value = eval(config.value)
            elif config.type == "bool":
                if config.value == "0":
                    c_value = False
                else:
                    c_value = True
            elif config.type == "json":
                c_value = json.loads(json_value)
            else:
                c_value = config.value
            self.objects[config.key] = array_value

custom_config = ConfigCenter()

