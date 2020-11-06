# -*- coding: utf8 -*-

from rest_framework.response import Response

from console.views.app_config.base import AppBaseView, ComponentGraphBaseView
from console.serializers.component_graph import CreateComponentGraphReq, UpdateComponentGraphReq
from console.services.app_config.component_graph import component_graph_service
from www.utils.return_message import general_message


class ComponentGraphListView(AppBaseView):
    def post(self, request, *args, **kwargs):
        serializer = CreateComponentGraphReq(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        graph = component_graph_service.create_component_graph(self.service.service_id, data['title'],
                                                               data['promql'])
        result = general_message(200, "success", "创建成功", bean=graph)
        return Response(result, status=result["code"])

    def get(self, request, *args, **kwargs):
        graphs = component_graph_service.list_component_graphs(self.service.service_id)
        result = general_message(200, "success", "查询功", list=graphs)
        return Response(result, status=result["code"])


class ComponentGraphView(ComponentGraphBaseView):
    def get(self, request, *args, **kwargs):
        result = general_message(200, "success", "查询功", bean=self.graph.to_dict())
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        serializer = UpdateComponentGraphReq(data=request.data)
        serializer.is_valid(raise_exception=True)
