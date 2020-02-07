# -*- coding: utf8 -*-
"""
  Created on 18/2/1.
"""
import logging
import json

from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from rest_framework import status

from console.repositories.deploy_repo import deploy_repo
from console.repositories.app import service_repo
from console.services.app import app_service
from console.services.app_actions import app_manage_service
from console.services.app_actions import event_service
from console.services.app_config import dependency_service
from console.services.app_config import env_var_service
from console.services.app_config import label_service
from console.services.app_config import port_service
from console.services.app_config import probe_service
from console.services.app_config import volume_service
from console.services.compose_service import compose_service
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from console.repositories.team_repo import team_repo
from www.decorator import perm_required
from www.utils.return_message import error_message
from www.utils.return_message import general_message
from www.apiclient.baseclient import HttpClient

logger = logging.getLogger("default")


class AppLView(RegionTenantHeaderView):
    def get(self, request, enterprise_id, team_name, *args, **kwargs):
        print enterprise_id, team_name
        name = request.GET.get("name", None)
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        team = team_repo.get_enterprise_team_by_name(enterprise_id, team_name)
        team_id = team.values_list("tenant_id", flat=True)
        if not team:
            result = general_message(404, "no found", "团队不存在")
            return Response(result, status=status.HTTP_200_OK)
        try:
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
            result = general_message(200, "success", "获取成功", list=data,
                                     total_count=len(app_count), page=page, page_size=page_size)
        except Exception as e:
            logger.debug(e)
            result = general_message(400, "fail", "获取失败")
        return Response(result, status=status.HTTP_200_OK)


