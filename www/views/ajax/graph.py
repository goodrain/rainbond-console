# -*- coding: utf8 -*-
import time
from random import randint
from django.http import JsonResponse
from www.views import AuthedView, BaseView
from www.decorator import perm_required
from www.api import OpentsdbApi

import logging
logger = logging.getLogger('default')


class ServiceGraph(AuthedView):

    metric_map = {
        'memory': None, 'disk': 'service.basic.disk_size',
        'bandwidth': 'service.basic.net.bytesout',
        'response-time': 'service.perf.web.response_time',
        'throughput': 'service.perf.web.throughput',
        'online': 'service.analysis.online',
    }

    def init_request(self, *args, **kwargs):
        self.template = {
            "xAxisLabel": u"时间",
            "yAxisLabel": u"单位",
        }
        self.tsdb_client = OpentsdbApi()

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

    def get_tsdb_data(self, graph_key, start):
        data = {"key": graph_key, "values": []}
        metric = self.metric_map.get(graph_key, None)

        if metric is not None:
            query_data = self.tsdb_client.query(
                self.tenant.region, metric, start=start, tenant=self.tenant.tenant_name, service=self.service.service_alias)

            if query_data is None:
                return None

            for timestamp, value in sorted(query_data.items()):
                data['values'].append([int(timestamp) * 1000, float(value)])

            return [data]
        else:
            return None

    @perm_required('view_service')
    def post(self, request, *args, **kwargs):
        graph_id = request.POST.get('graph_id', None)
        start = request.POST.get('start', None)
        if graph_id is None:
            return JsonResponse({"ok": False, "info": "need graph_id filed"}, status=500)
        else:
            graph_key = graph_id.replace('-stat', '')
            result = self.template.copy()
            result['data'] = self.random_data(graph_key)
            data = self.get_tsdb_data(graph_key, start)
            if data is not None:
                result['data'] = data
                return JsonResponse(result, status=200)
            else:
                return JsonResponse({"ok": False}, status=404)
