# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
import logging
import json

from rest_framework.response import Response
from rest_framework import status

from console.repositories.app import service_repo
from console.views.base import RegionTenantHeaderView
from console.repositories.team_repo import team_repo
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class AppLView(RegionTenantHeaderView):
    def get(self, request, enterprise_id, team_name, *args, **kwargs):
        name = request.GET.get("name", None)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        team = team_repo.get_enterprise_team_by_name(enterprise_id, team_name)
        if not team:
            result = general_message(404, "no found", "团队不存在")
            return Response(result, status=status.HTTP_200_OK)
        team_id = team.tenant_id
        data = []
        app_list = service_repo.get_app_list(team_id, name, page, page_size)
        app_count = service_repo.get_app_count(team_id, name)
        for app in app_list:
            data.append({
                "ID": app.ID,
                "group_name": app.group_name,
                "tenant_id": app.tenant_id,
                "service_list": json.loads(app.service_list) if app.service_list else []
            })
        result = general_message(200, "success", "获取成功", list=data, total_count=len(app_count), page=page, page_size=page_size)
        return Response(result, status=status.HTTP_200_OK)
