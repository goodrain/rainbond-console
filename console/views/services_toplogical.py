# -*- coding: utf8 -*-
"""
  Created on 2018/3/21.
"""
import logging

from rest_framework.response import Response

from console.repositories.group import group_repo
from console.repositories.service_repo import service_repo
from console.services.app_actions.app_log import AppEventService
from console.services.topological_services import topological_service
from console.views.base import RegionTenantHeaderView
from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

event_service = AppEventService()
region_api = RegionInvokeApi()
logger = logging.getLogger('default')


class TopologicalGraphView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        应用拓扑图(未分组应用无拓扑图, 直接返回列表展示)
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用id
              required: true
              type: string
              paramType: query
        """
        group_id = request.GET.get("group_id", None)
        code = 200
        if group_id == "-1":
            code = 200
            no_service_list = service_repo.get_no_group_service_status_by_group_id(team_name=self.team_name,
                                                                                   region_name=self.response_region)
            result = general_message(200, "query success", "应用查询成功", list=no_service_list)
        else:
            if group_id is None or not group_id.isdigit():
                code = 400
                result = general_message(code, "group_id is missing or not digit!", "group_id缺失或非数字")
                return Response(result, status=code)
            team_id = self.team.tenant_id
            group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
            if group_count == 0:
                code = 202
                result = general_message(code, "group is not yours!", "当前组已删除或您无权限查看!", bean={})
                return Response(result, status=200)
            topological_info = topological_service.get_group_topological_graph(group_id=group_id,
                                                                               region=self.response_region,
                                                                               team_name=self.team_name,
                                                                               enterprise_id=self.team.enterprise_id)
            result = general_message(code, "Obtain topology success.", "获取拓扑图成功", bean=topological_info)
        return Response(result, status=code)


class GroupServiceDetView(AppBaseView):
    def get(self, request, *args, **kwargs):
        """
        拓扑图中组件详情
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
        """
        if not self.service:
            return Response(general_message(400, "service not found", "参数错误"), status=400)
        result = topological_service.get_group_topological_graph_details(team=self.team,
                                                                         team_id=self.team.tenant_id,
                                                                         team_name=self.team_name,
                                                                         service=self.service,
                                                                         region_name=self.service.service_region)
        result = general_message(200, "success", "成功", bean=result)
        return Response(result, status=200)


class TopologicalInternetView(RegionTenantHeaderView):
    def get(self, request, team_name, group_id, *args, **kwargs):
        """
        拓扑图中Internet详情
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用id
              required: true
              type: string
              paramType: path
        """
        # logger.debug("query topological graph from:{0}".format(group_id))
        if group_id == "-1":
            code = 200
            no_service_list = service_repo.get_no_group_service_status_by_group_id(team_name=self.team_name,
                                                                                   region_name=self.response_region)
            result = general_message(200, "query success", "应用获取成功", list=no_service_list)
        else:
            code = 200
            if group_id is None or not group_id.isdigit():
                code = 400
                result = general_message(code, "group_id is missing or not digit!", "group_id缺失或非数字")
                return Response(result, status=code)
            team_id = self.team.tenant_id
            group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
            if group_count == 0:
                code = 202
                result = general_message(code, "group is not yours!", "当前组已删除或您无权限查看!", bean={"json_svg": {}, "json_data": {}})
                return Response(result, status=200)
            else:
                data = topological_service.get_internet_topological_graph(group_id=group_id, team_name=team_name)
                result = general_message(code, "Obtain topology internet success.", "获取拓扑图Internet成功", bean=data)
        return Response(result, status=code)
