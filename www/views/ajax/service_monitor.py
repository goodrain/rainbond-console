# -*- coding: utf8 -*-
import datetime
import json
import re

from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required

from www.service_http import RegionServiceApi
from django.conf import settings
from goodrain_web.decorator import method_perf_time

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()

class ServiceMonitorQuery(AuthedView):
    """
    查询服务容器内存
    """
    def get(self, request, *args, **kwargs):
        """
         查询服务容器内存监控数据，最近一个小时
        """
        data = {}
        try:
            query = request.GET.get("query","")
            if query=="mem":
                data = regionClient.monitoryQueryMem(self.service.service_id) 
            elif query=="cpu":
                data = regionClient.monitoryQueryCPU(self.service.service_id) 
            elif query=="io":
                data = regionClient.monitoryQueryIO(self.service.service_id) 
            elif query=="fs":
                data = regionClient.monitoryQueryFS(self.service.service_id) 
            return JsonResponse(data, status=200)   
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return JsonResponse(data, status=500)