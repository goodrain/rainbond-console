# -*- coding: utf8 -*-
import json
import beanstalkc
from django.conf import settings
from django.core.paginator import Paginator

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
                
        
class JuncheePaginator(Paginator):
    def __init__(self, object_list, per_page, range_num=5, orphans=0, allow_empty_first_page=True):
        Paginator.__init__(self, object_list, per_page, orphans, allow_empty_first_page)
        self.range_num = range_num
         
    def page(self, number):
        self.page_num = number
        return super(JuncheePaginator, self).page(number)

    def _page_range_ext(self):
        num_count = 2 * self.range_num + 1
        if self.num_pages <= num_count:
            return range(1, self.num_pages + 1)
        num_list = []
        num_list.append(self.page_num)
        for i in range(1, self.range_num + 1):
            if self.page_num - i <= 0:
                num_list.append(num_count + self.page_num - i)
            else:
                num_list.append(self.page_num - i)
        
            if self.page_num + i <= self.num_pages:
                num_list.append(self.page_num + i)
            else:
                num_list.append(self.page_num + i - num_count)
        num_list.sort()
        return num_list
    page_range_ext = property(_page_range_ext)
