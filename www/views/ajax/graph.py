# -*- coding: utf8 -*-
import time
from random import randint
from django.http import JsonResponse
from www.views import AuthedView, BaseView
from www.decorator import perm_required

import logging
logger = logging.getLogger('default')


class ServiceGraph(BaseView):

    def init_request(self, *args, **kwargs):
        self.template = {
            "xAxisLabel": u"时间",
            "yAxisLabel": u"单位: MB",
        }

    def random_data(self, graph_key):
        curr_time = int(time.time())

        def increase_time(step):
            return (curr_time + 30 * step) * 1000

        data = {
            "key": graph_key,
            "values": []
        }

        for i in range(30):
            data['values'].append([increase_time(i), randint(100, 1000)])
        return [data]

    #@perm_required('view_service')
    def post(self, request, *args, **kwargs):
        graph_id = request.POST.get('graph_id', None)
        if graph_id is None:
            return JsonResponse({"ok": False, "info": "need graph_id filed"}, status=500)
        else:
            graph_key = graph_id.replace('-stat', '')
            result = self.template.copy()
            result['data'] = self.random_data(graph_key)
            return JsonResponse(result, status=200)
