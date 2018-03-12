# -*- coding: utf8 -*-
import json
from django.conf import settings as base_settings
from cadmin.models.main import ConsoleSysConfig
from goodrain_web.memcachedclient import MemcachedCli

import logging

logger = logging.getLogger('default')

mcli = MemcachedCli()

configKey = "SYS_C_F_K"

class ConfigCenter(object):
        
    def __init__(self):
        self.configs()

    def __getattr__(self, name):
        if name in self.configs():
            return self.configs()[name]
        else:
            if hasattr(base_settings, name):
                return getattr(base_settings, name)
            else:
                return None

    def configs(self):
        result = mcli.getKey(configKey)
        if result is not None:
            # logger.info("from " + result)
            return json.loads(result)
        else:
            return self.loadfromDB()

    def reload(self):
        mcli.setKey(configKey, json.dumps(self.loadfromDB()))

    def loadfromDB(self):

        objects = {}
        # 查询启用的配置
        configs = ConsoleSysConfig.objects.filter(enable=True)
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
                if config.value != "" and config.value is not None:
                    c_value = json.loads(config.value)
            else:
                c_value = config.value
                
            objects[config.key] = c_value
        mcli.setKey(configKey, json.dumps(objects))
        return objects

custom_config = ConfigCenter()
