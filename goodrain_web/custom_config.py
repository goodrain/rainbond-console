# -*- coding: utf8 -*-
import json
import logging

from django.conf import settings as base_settings

from goodrain_web.memcachedclient import MemcachedCli

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
        mcli.setKey(configKey, json.dumps(objects))
        return objects


custom_config = ConfigCenter()
