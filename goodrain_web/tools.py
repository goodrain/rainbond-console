# -*- coding: utf8 -*-
import json
import beanstalkc
from django.conf import settings

import logging
logger = logging.getLogger('default')

class BeanStalkClient:
    def __init__(self):
        pass

    def put(self, tube , data):
        try:
            beanstalkd_info = settings.BEANSTALKD
            conn = beanstalkc.Connection(host=beanstalkd_info.get('host'), port=beanstalkd_info.get('port'), parse_yaml=False)
            if tube is None:
                conn.use(beanstalkd_info.get('tube'))
            else:
                conn.use(tube)
                                                
            if isinstance(data, (list, dict, tuple)):
                conn.put(json.dumps(data))
            else:
                conn.put(data)
            conn.close()
        except Exception as e:
            logger.exception(e)
                
        
