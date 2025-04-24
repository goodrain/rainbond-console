# -*- coding: utf8 -*-
import json

from rest_framework.response import Response

from console.services.operation_log import operation_log_service, Operation
from console.views.app_config.base import AppBaseView, ComponentGraphBaseView
from console.serializers.component_graph import CreateComponentGraphReq, UpdateComponentGraphReq, ExchangeComponentGraphsReq
from console.services.app_config.component_graph import component_graph_service
from www.utils.return_message import general_message
from console.utils.reqparse import parse_item


class ComponentGraphListView(AppBaseView):
    def post(self, request, *args, **kwargs):
        serializer = CreateComponentGraphReq(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        graph = component_graph_service.create_component_graph(self.service.service_id, data['title'], data['promql'],
                                                               self.service.arch)
        result = general_message(200, "success", "创建成功", bean=graph)
        new_information = json.dumps({"图表标题": request.data["title"], "查询条件": request.data["promql"]},
                                     ensure_ascii=False)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.FOR,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix="添加了监控图{}".format(data['title']))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information,
        )
        return Response(result, status=result["code"])

    def get(self, request, *args, **kwargs):
        graphs = component_graph_service.list_component_graphs(self.service.service_id)
        result = general_message(200, "success", "查询成功", list=graphs)
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        graph_ids = parse_item(request, "graph_ids", required=True)
        graphs = component_graph_service.select_component_graphs(self.service.service_id, graph_ids)
        old_information = component_graph_service.json_component_graphs(graphs)
        component_graph_service.batch_delete(self.service.service_id, graph_ids)
        result = general_message(200, "success", "删除成功")
        comment = operation_log_service.generate_component_comment(
            operation=Operation.BATCH_DELETE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix="的监控图")
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information)
        return Response(result, status=result["code"])


class ComponentGraphView(ComponentGraphBaseView):
    def get(self, request, *args, **kwargs):
        result = general_message(200, "success", "查询成功", bean=self.graph.to_dict())
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        serializer = UpdateComponentGraphReq(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        old_information = json.dumps({"图表标题": self.graph.title, "查询条件": self.graph.promql}, ensure_ascii=False)
        graphs = component_graph_service.update_component_graph(self.graph, data["title"], data["promql"], data["sequence"],
                                                                self.service.arch)
        new_information = json.dumps({"图表标题": self.graph.title, "查询条件": self.graph.promql}, ensure_ascii=False)
        result = general_message(200, "success", "修改成功", list=graphs)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.CHANGE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix="的监控图{}".format(self.graph.title))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information,
            new_information=new_information)
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        old_information = json.dumps({"图表标题": self.graph.title, "查询条件": self.graph.promql}, ensure_ascii=False)
        graphs = component_graph_service.delete_component_graph(self.graph)
        result = general_message(200, "success", "删除成功", list=graphs)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.DELETE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix="的监控图{}".format(self.graph.title))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information)
        return Response(result, status=result["code"])


class ComponentInternalGraphsView(AppBaseView):
    def post(self, request, *args, **kwargs):
        graph_name = parse_item(request, "graph_name", required=True)
        graphs = component_graph_service.create_internal_graphs(self.service.service_id, graph_name, self.service.arch)
        new_information = component_graph_service.json_component_graphs(graphs)
        result = general_message(200, "success", "导入成功")
        comment = operation_log_service.generate_component_comment(
            operation=Operation.FOR,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix="一键导入了{}监控图表".format(graph_name))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information)
        return Response(result, status=result["code"])

    def get(self, request, *args, **kwargs):
        graphs = component_graph_service.list_internal_graphs()
        result = general_message(200, "success", "查询成功", list=graphs)
        return Response(result, status=result["code"])


class ComponentExchangeGraphsView(AppBaseView):
    def put(self, request, *args, **kwargs):
        serializer = ExchangeComponentGraphsReq(data=request.data)
        serializer.is_valid(raise_exception=True)
        graph_ids = serializer.data["graph_ids"]
        component_graph_service.exchange_graphs(self.service.service_id, graph_ids)
        result = general_message(200, "success", "修改成功")
        return Response(result, status=result["code"])
