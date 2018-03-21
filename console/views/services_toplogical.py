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
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView, JWTAuthApiView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message, error_message
from console.services.team_services import team_services
from rest_framework.exceptions import NotFound
from console.services.app import service_repo

event_service = AppEventService()

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class ToplogicalBaseView(JWTAuthApiView):
    def __init__(self, *args, **kwargs):
        super(ToplogicalBaseView, self).__init__(*args, **kwargs)
        self.response_region = None
        self.tenant_name = None
        self.team_name = None
        self.tenant = None
        self.team = None
        self.user = None
        self.service = None

    def initial(self, request, *args, **kwargs):

        super(ToplogicalBaseView, self).initial(request, *args, **kwargs)
        self.tenant_name = kwargs.get("tenantName", None)
        service_alias = kwargs.get("serviceAlias", None)
        self.user = request.user
        if kwargs.get("team_name", None):
            self.tenant_name = kwargs.get("team_name", None)
            self.team_name = self.tenant_name
        if not self.response_region:
            self.response_region = request.GET.get('region', None)

        if not self.response_region:
            raise ImportError("region_name not found !")
        if not self.tenant_name:
            raise ImportError("team_name not found !")
        if self.tenant_name:
            tenant = team_services.get_tenant_by_tenant_name(self.tenant_name)
            if tenant:
                self.tenant = tenant
                self.team = tenant
            else:
                raise NotFound("tenant {0} not found".format(self.tenant_name))

        if service_alias:
            self.service = service_repo.get_service_by_tenant_and_alias(self.tenant.tenant_id, service_alias)

        self.initial_header_info(request)

    def initial_header_info(self, request):
        pass


class TopologicalGraphView(ToplogicalBaseView):
    def get(self, request, *args, **kwargs):
        """
        应用组拓扑图(未分组应用无拓扑图, 直接返回列表展示)
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用组id
              required: true
              type: string
              paramType: query
        """
        try:
            group_id = request.GET.get("group_id", None)
            code = 200
            if group_id == "-1":
                code = 200
                no_service_list = service_repo.get_no_group_service_status_by_group_id(team_name=self.team_name,
                                                                                       region_name=self.response_region)
                result = general_message(200, "query success", "应用组查询成功", list=no_service_list)
            else:
                if group_id is None or not group_id.isdigit():
                    code = 400
                    result = general_message(code, "group_id is missing or not digit!", "group_id缺失或非数字")
                    return Response(result, status=code)
                team_id = self.team.tenant_id
                group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
                if group_count == 0:
                    code = 400
                    result = general_message(code, "group is not yours!", "这个组不是你的!")
                    return Response(result, status=502)
                topological_info = topological_service.get_group_topological_graph(group_id=group_id,
                                                                                   region=self.response_region,
                                                                                   team_name=self.team_name,
                                                                                   enterprise_id=self.team.enterprise_id)
                result = general_message(code, "Obtain topology success.", "获取拓扑图成功", bean=topological_info)
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class GroupServiceDetView(ToplogicalBaseView):
    def get(self, request, *args, **kwargs):
        """
        拓扑图中应用详情
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 应用别名
              required: true
              type: string
              paramType: path
        """
        try:
            if not self.service:
                return Response(general_message(400, "service not found", "参数错误"), status=400)
            result = topological_service.get_group_topological_graph_details(team=self.team,
                                                                             team_id=self.team.tenant_id,
                                                                             team_name=self.team_name,
                                                                             service=self.service,
                                                                             region_name=self.service.service_region)
            result = general_message(200, "success", "成功", bean=result)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TopologicalInternetView(ToplogicalBaseView):
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
              description: 应用组id
              required: true
              type: string
              paramType: path
        """
        logger.debug("query topological graph from:{0}".format(group_id))
        try:
            if group_id == "-1":
                code = 200
                no_service_list = service_repo.get_no_group_service_status_by_group_id(team_name=self.team_name,
                                                                                       region_name=self.response_region)
                result = general_message(200, "query success", "应用组获取成功", list=no_service_list)
            else:
                code = 200
                if group_id is None or not group_id.isdigit():
                    code = 400
                    result = general_message(code, "group_id is missing or not digit!", "group_id缺失或非数字")
                    return Response(result, status=code)
                team_id = self.team.tenant_id
                group_count = group_repo.get_group_count_by_team_id_and_group_id(team_id=team_id, group_id=group_id)
                if group_count == 0:
                    code = 400
                    result = general_message(code, "group is not yours!", "这个组不是你的!")
                    return Response(result, status=502)
                else:
                    data = topological_service.get_internet_topological_graph(group_id=group_id, team_name=team_name)
                    result = general_message(code, "Obtain topology internet success.", "获取拓扑图Internet成功", bean=data)
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)
