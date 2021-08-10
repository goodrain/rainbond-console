# -*- coding: utf8 -*-
import os
import time
import redis
import logging

logger = logging.getLogger('default')


class Cache(object):
    def __init__(self, max_cache_size=30):
        self.cache = {}
        self.max_cache_size = max_cache_size
        self.redis = None
        if self.enable_redis:
            self.redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "127.0.0.1"),
                port=os.getenv("REDIS_PORT", 6379),
                db=os.getenv("REDIS_DB", 0),
                password=os.getenv("REDIS_PASSWORD", None))

    def get(self, key):
        if self.enable_redis:
            return self._redis_get(key)
        return self._memory_get(key)

    def _redis_get(self, key):
        try:
            return self.redis.get(key)
        except Exception as e:
            logger.exception(e)

    def _memory_get(self, key):
        if key not in self.cache:
            return None
        if self.cache[key]["expired_time"] < time.time():
            self.cache.pop(key)
            return None
        return self.cache[key]["value"]

    def set(self, key, value, seconds):
        if self.enable_redis:
            return self._redis_set(key, value, seconds)
        self._memory_set(key, value, seconds)

    def _redis_set(self, key, value, seconds):
        try:
            self.redis.set(key, value, seconds)
        except Exception as e:
            logger.exception(e)

    def _memory_set(self, key, value, seconds):
        if key not in self.cache and self.size >= self.max_cache_size:
            remove_num = self._remove_expired_key()
            if remove_num == 0:
                logger.debug("The cache is full and cannot be set")
                return
        self.cache[key] = {"expired_time": time.time() + seconds, "value": value}

    def _remove_expired_key(self):
        remove_keys = []
        for key in self.cache:
            if self.cache[key]["expired_time"] < time.time():
                remove_keys.append(key)
        for remove_key in remove_keys:
            self.cache.pop(remove_key)
        return len(remove_keys)

    @property
    def size(self):
        return len(self.cache)

    @property
    def enable_redis(self):
        if os.getenv("REDIS_HOST"):
            return True
        return False


cache = Cache()
