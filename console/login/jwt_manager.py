# -*- coding: utf-8 -*-
import logging
import os
import threading

import redis

logger = logging.getLogger("default")


class JwtManager(object):
    _instance_lock = threading.Lock()

    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(JwtManager, "_instance"):
            with JwtManager._instance_lock:
                if not hasattr(JwtManager, "_instance"):
                    _instance = object.__new__(cls)
                    JwtManager._instance = _instance

                cls.enable = os.getenv("ENABLE_JWT_MANAGER", False)
                if not cls.enable:
                    return JwtManager._instance

                # create redis
                cls.r = redis.Redis(host=os.getenv("REDIS_HOST", "127.0.0.1"),
                                    port=os.getenv("REDIS_PORT", 6379),
                                    db=os.getenv("REDIS_DB", 0),
                                    password=os.getenv("REDIS_PASSWORD", None))
                cls.cache_time = os.getenv("JWT_CACHE_TIME", 3600)

        return JwtManager._instance

    def exists(self, jwt):
        if not self.enable:
            return True
        try:
            return self.r.exists(jwt)
        except Exception as e:
            logger.exception(e)
            return True

    def set(self, jwt, user_id):
        if not self.enable:
            return
        # expired in 3600s
        # TODO: A rate limiter can reduce the stress of redis server.
        try:
            self.r.set(jwt, user_id, ex=self.cache_time)
            self.r.set(user_id, jwt, ex=self.cache_time)
        except Exception as e:
            logger.exception(e)

    def delete_user_id(self, user_id):
        jwt = self.r.get(user_id)
        if jwt:
            self.r.delete(jwt)
        self.r.delete(user_id)
