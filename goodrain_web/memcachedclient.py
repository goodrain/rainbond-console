# -*- coding: utf8 -*-
import os
import logging
import pylibmc

logger = logging.getLogger('default')


class MemcachedCli(object):

    def __init__(self):
        try:
            if os.environ.get('MEMCACHED_HOST') and os.environ.get('MEMCACHED_PORT'):
                self.mc = pylibmc.Client([os.environ.get('MEMCACHED_HOST') + ":" + os.environ.get('MEMCACHED_PORT')],
                                         binary=True, behaviors={"tcp_nodelay": True, "ketama": True})
        except Exception as e:
            logger.exception(e)
    
    def getKey(self, key):
        try:
            if self.mc:
                return self.mc.get(key)
        except Exception:
            pass
        return None

    def setKey(self, key, value):
        try:
            if self.mc:
                self.mc.set(key, value)
        except Exception:
            pass
