# -*- coding: utf-8 -*-
# creater by: barnett

from functools import wraps

import logging
import datetime

logger = logging.getLogger('default')


def method_perf_time(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start = datetime.datetime.now()
        ret = func(self, *args, **kwargs)
        end = datetime.datetime.now()
        logger.debug("query region api {0} take time {1} retries {2}".format(args,
                                                                             float((end - start).microseconds) / 1000000,
                                                                             kwargs.get("retries", 3)))
        return ret

    return wrapper
