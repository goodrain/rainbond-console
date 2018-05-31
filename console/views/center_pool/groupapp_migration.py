# -*- coding: utf8 -*-
"""
  Created on 18/5/23.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.groupapp_recovery.groupapps_migrate import migrate_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message

logger = logging.getLogger('default')


class GroupAppsMigrateView(RegionTenantHeaderView):

    @never_cache
    @perm_required("import_and_export_service")
    def post(self, request, *args, **kwargs):
        """
        应用迁移
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path
            - name: region
              description: 需要备份的数据中心
              required: true
              type: string
              paramType: form
            - name: team
              description: 需要迁移到的团队
              required: true
              type: string
              paramType: form
            - name: backup_id
              description: 备份ID
              required: true
              type: string
              paramType: form

        """
        try:
            migrate_region = request.data.get("region", None)
            team = request.data.get("team", None)
            backup_id = request.data.get("backup_id", None)

            if not team:
                return Response(general_message(400, "team is null", "请指明要迁移的团队"), status=400)
            migrate_team = team_services.get_tenant_by_tenant_name(team)
            if not migrate_team:
                return Response(general_message(404, "team is not found", "需要迁移的团队{0}不存在".format(team)), status=404)
            regions = region_services.get_team_usable_regions(migrate_team)
            if migrate_region not in [r.region_name for r in regions]:
                return Response(general_message(412, "region is not usable",
                                                "无法迁移至数据中心{0},请确保该数据中心可用且团队{1}已开通该数据中心权限".format(migrate_region,
                                                                                                 migrate_team.tenant_name)),
                                status=412)

            code, msg, migrate_record = migrate_service.start_migrate(self.user, self.tenant,
                                                                      self.response_region, migrate_team,
                                                                      migrate_region,
                                                                      backup_id)
            if code != 200:
                return Response(general_message(code, "migrate failed", msg),
                                status=code)
            result = general_message(200, "success", "操作成功，开始迁移应用", bean=migrate_record.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required("import_and_export_service")
    def get(self, request, *args, **kwargs):
        """
        查询迁移状态
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
              paramType: query
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: path
            - name: restore_id
              description: 存储id
              required: true
              type: string
              paramType: query

        """
        try:
            restore_id = request.GET.get("restore_id", None)
            if not restore_id:
                return Response(general_message(400, "restore id is null", "请指明查询的备份ID"), status=400)

            code, msg, migrate_record = migrate_service.get_and_save_migrate_status(self.user, restore_id)
            if code != 200:
                return Response(general_message(code, "get migrate status error", "查询失败"), status=code)
            result = general_message(200, "success", "查询成功", bean=migrate_record.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
