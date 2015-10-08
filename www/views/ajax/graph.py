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
        'memory': None, 'disk': {'metric': 'service.basic.disk_size', 'unit': 'MB'},
        'bandwidth': {"metric": 'service.basic.net.bytesout', "unit": 'bytes'},
        'response-time': {"metric": 'service.perf.web.response_time', "unit": "ms"},
        'throughput': {"metric": 'service.perf.web.throughput', "unit": "count"},
        'online': {"metric": 'service.analysis.online', "unit": u"人数"},
    }

    downsamples = {
        '1h-ago': '1m-avg', '8h-ago': '2m-avg', '24h-ago': '5m-avg',
        '7d-ago': '1h-avg',
    }

    def init_request(self, *args, **kwargs):
        self.template = {
            "xAxisLabel": u"时间",
            "yAxisLabel": u"单位",
            "yAxisFormat": ',.2f',
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
        metric = self.metric_map.get(graph_key, None).get('metric', None)
        downsample = self.downsamples.get(start)

        if metric is not None:
            query_data = self.tsdb_client.query(
                self.tenant.region, metric, start=start, downsample=downsample, tenant=self.tenant.tenant_name, service=self.service.service_alias)

            if query_data is None:
                return None

            for timestamp, value in sorted(query_data.items()):
                if value.is_integer():
                    data['values'].append([int(timestamp) * 1000, int(value)])
                else:
                    data['values'].append([int(timestamp) * 1000, value])

            return [data]
        else:
            return None

    def add_tags(self, graph_key, result):
        test_value = result['data'][0]['values'][0][1]
        if isinstance(test_value, int):
            result['yAxisFormat'] = ',.0f'

        result['yAxisLabel'] = self.metric_map.get(graph_key, None).get('unit', '')

    @perm_required('view_service')
    def post(self, request, *args, **kwargs):
        graph_id = request.POST.get('graph_id', None)
        start = request.POST.get('start', None)
        if graph_id is None:
            return JsonResponse({"ok": False, "info": "need graph_id filed"}, status=500)

        if start not in self.downsamples:
            return JsonResponse({"ok": False, "info": "reject time period {0}".format(start)}, status=500)

        graph_key = graph_id.replace('-stat', '')
        result = self.template.copy()
        result['data'] = self.random_data(graph_key)
        data = self.get_tsdb_data(graph_key, start)
        if data is not None:
            result['data'] = data
            self.add_tags(graph_key, result)
            return JsonResponse(result, status=200)
        else:
            return JsonResponse({"ok": False}, status=404)
