# -*- coding: utf-8 -*-
# creater by: barnett

from functools import wraps

import logging

logger = logging.getLogger('default')


def method_perf_time(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        ret = func(self, *args, **kwargs)
        return ret

    return wrapper
