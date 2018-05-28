# -*- coding: utf8 -*-
"""
  Created on 2018/4/23.
"""
import logging
from rest_framework.response import Response
from backends.views.base import BaseAPIView
from backends.services.resultservice import *

from console.services.team_services import team_services as console_team_service
from console.services.event_services import service_event_dynamic
from console.repositories.app import service_repo
from console.constants import LogConstants
from console.services.app_actions import event_service

logger = logging.getLogger("default")


class ServiceOperateView(BaseAPIView):

    def get(self, request, *args, **kwargs):
        """
        获取用户操作信息
        ---
        parameters:
            - name: page_num
              description: 页码
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页数量(默认20)
              required: false
              type: string
              paramType: query
            - name: team_name
              description: 团队名称
              required: false
              type: string
              paramType: query
            - name: create_time
              description: 创建时间
              required: false
              type: string
              paramType: query
            - name: status
              description: 事件状态（success,failure,timeout）默认 failure
              required: false
              type: string
              paramType: query
        """
        try:
            page = request.GET.get("page_num", 1)
            page_size = request.GET.get("page_size", 20)
            team_name = request.GET.get("team_name", None)
            create_time = request.GET.get("create_time", None)
            status = request.GET.get("status", None)
            team = None
            if team_name:
                team = console_team_service.get_tenant_by_tenant_name(team_name)
                if not team:
                    return Response(generate_result("0404", "team not found", "团队{0}不存在".format(team_name)))

            show_events, total = service_event_dynamic.get_services_events(int(page), int(page_size), create_time, status, team)
            result_list = []
            for e in show_events:
                bean = e.to_dict()
                bean.update({"service_cname": e.service_cname, "service_alias": e.service_alias,
                             "service_region": e.service_region, "team_name": e.team_name})
                result_list.append(bean)
            result = generate_result("0000", "query success", "查询成功", list=result_list,total=total)

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class ServiceOperationDetailView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取服务的event的详细日志
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: query
            - name: service_alias
              description: 服务别名
              required: true
              type: string
              paramType: query
            - name: level
              description: 日志等级
              required: false
              type: string
              paramType: query
            - name: event_id
              description: 事件id
              required: true
              type: string
              paramType: query
        """
        try:
            team_name = request.GET.get("team_name", None)
            service_alias = request.GET.get("service_alias", None)
            level = request.GET.get("level", LogConstants.INFO)
            event_id = request.GET.get("event_id", None)
            if not team_name:
                return Response(generate_result("0400", "team name is null", "团队名称不能为空"))
            if not service_alias:
                return Response(generate_result("0400", "serice alias is null", "服务别名不能为空"))
            if not event_id:
                return Response(generate_result("0400", "event id is null", "请指明事件id"))
            team = console_team_service.get_tenant_by_tenant_name(team_name)
            if not team:
                return Response(generate_result("0404", "team is not found", "团队{0}不存在".format(team_name)))
            service = service_repo.get_service_by_service_alias(service_alias)
            if not service:
                return Response(generate_result("0404", "team is not found", "应用{0}不存在".format(service_alias)))

            log_list = event_service.get_service_event_log(team, service, level, event_id)
            result = generate_result("0000", "success", "查询成功", list=log_list)

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
