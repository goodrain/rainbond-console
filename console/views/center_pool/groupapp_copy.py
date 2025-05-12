# -*- coding: utf8 -*-
"""
  Created on 18/5/23.
"""
import logging

from console.exception.main import ServiceHandleException
from console.services.groupcopy_service import groupapp_copy_service
from console.services.operation_log import operation_log_service, OperationType
from console.views.base import RegionTenantHeaderView, ApplicationView
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from www.apiclient.baseclient import HttpClient
from www.utils.return_message import general_message

logger = logging.getLogger('default')


class GroupAppsCopyView(ApplicationView):
    @never_cache
    def get(self, request, tenantName, group_id, **kwargs):
        group_services = groupapp_copy_service.get_group_services_with_build_source(self.tenant, self.region_name, group_id)
        result = general_message(200, "success", "获取成功", list=group_services)
        return Response(result, status=200)

    @never_cache
    def post(self, request, tenantName, group_id, *args, **kwargs):
        """
        应用复制
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用id
              required: true
              type: int
              paramType: path
        """
        services = request.data.get("services", [])
        tar_team_name = request.data.get("tar_team_name")
        tar_region_name = request.data.get("tar_region_name")
        tar_group_id = request.data.get("tar_group_id")
        if not tar_team_name or not tar_region_name or not tar_group_id:
            raise ServiceHandleException(msg_show="缺少复制目标参数", msg="not found copy target parameters", status_code=404)
        if len(services) > 20:
            raise ServiceHandleException(msg_show="单次复制最多20个组件", msg="Copy up to 20 components at a time", status_code=400)
        tar_team, tar_group = groupapp_copy_service.check_and_get_team_group(request.user, tar_team_name, tar_region_name,
                                                                             tar_group_id)
        try:
            services = groupapp_copy_service.copy_group_services(request.user, self.tenant, self.region_name, tar_team, tar_region_name,
                                                      tar_group, group_id, services)
            result = general_message(
                200,
                "success",
                "复制成功",
                bean={
                    "tar_team_name": tar_team_name,
                    "tar_region_name": tar_region_name,
                    "tar_group_id": tar_group_id
                })
            status = 200
            comment = groupapp_copy_service.generate_comment(self.app, self.region_name, self.tenant_name, tar_group,
                                                             tar_region_name, tar_team_name, services)
            operation_log_service.create_log(self.user, OperationType.APPLICATION_MANAGE, comment,
                                             self.user.enterprise_id,
                                             self.tenant_name, self.app.app_id)
        except HttpClient.CallApiError as e:
            logger.exception(e)
            if e.status == 403:
                result = general_message(10407, "no cloud permission", e.message)
                status = e.status
            elif e.status == 400:
                if "is exist" in e.message.get("body", ""):
                    result = general_message(400, "the service is exist in region", "组件名称在数据中心已存在")
                else:
                    result = general_message(400, "call cloud api failure", e.message)
                status = e.status
            else:
                result = general_message(500, "call cloud api failure", e.message)
                status = 500
        return Response(result, status=status)
