# -*- coding: utf8 -*-

from rest_framework.response import Response

from console.views.app_config.base import AppBaseView, ComponentGraphBaseView
from console.serializers.component_graph import CreateComponentGraphReq, UpdateComponentGraphReq
from console.services.app_config.component_graph import component_graph_service
from www.utils.return_message import general_message
from console.utils.reqparse import parse_item


class ComponentGraphListView(AppBaseView):
    def post(self, request, *args, **kwargs):
        serializer = CreateComponentGraphReq(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        graph = component_graph_service.create_component_graph(self.service.service_id, data['title'], data['promql'])
        result = general_message(200, "success", "创建成功", bean=graph)
        return Response(result, status=result["code"])

    def get(self, request, *args, **kwargs):
        graphs = component_graph_service.list_component_graphs(self.service.service_id)
        result = general_message(200, "success", "查询成功", list=graphs)
        return Response(result, status=result["code"])


class ComponentGraphView(ComponentGraphBaseView):
    def get(self, request, *args, **kwargs):
        result = general_message(200, "success", "查询成功", bean=self.graph.to_dict())
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        serializer = UpdateComponentGraphReq(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        graphs = component_graph_service.update_component_graph(self.graph, data["title"], data["promql"], data["sequence"])
        result = general_message(200, "success", "修改成功", list=graphs)
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        graphs = component_graph_service.delete_component_graph(self.graph)
        result = general_message(200, "success", "删除成功", list=graphs)
        return Response(result, status=result["code"])


class ComponentInternalGraphsView(AppBaseView):
    def post(self, request, *args, **kwargs):
        graph_name = parse_item(request, "graph_name", required=True)
        component_graph_service.create_internal_graphs(self.service.service_id, graph_name)
        result = general_message(200, "success", "导入成功")
        return Response(result, status=result["code"])

    def get(self, request, *args, **kwargs):
        graphs = component_graph_service.list_internal_graphs()
        result = general_message(200, "success", "查询成功", list=graphs)
        return Response(result, status=result["code"])
