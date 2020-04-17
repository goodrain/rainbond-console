# -*- coding: utf8 -*-
"""
  Created on 18/5/23.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.repositories.group import group_repo
from console.repositories.migration_repo import migrate_repo
from console.services.app_actions import app_manage_service
from console.services.group_service import group_service
from console.services.groupapp_recovery.groupapps_migrate import migrate_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import error_message
from www.utils.return_message import general_message

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
            - name: migrate_type
              description: 操作类型
              required: true
              type: string
              paramType: form
        """
        migrate_region = request.data.get("region", None)
        team = request.data.get("team", None)
        backup_id = request.data.get("backup_id", None)
        migrate_type = request.data.get("migrate_type", "migrate")
        event_id = request.data.get("event_id", None)
        restore_id = request.data.get("restore_id", None)

        if not team:
            return Response(general_message(400, "team is null", "请指明要迁移的团队"), status=400)
        migrate_team = team_services.get_tenant_by_tenant_name(team)
        if not migrate_team:
            return Response(general_message(404, "team is not found", "需要迁移的团队{0}不存在".format(team)), status=404)
        regions = region_services.get_team_usable_regions(migrate_team)
        if migrate_region not in [r.region_name for r in regions]:
            msg_cn = "无法迁移至数据中心{0},请确保该数据中心可用且团队{1}已开通该数据中心权限".format(
                migrate_region, migrate_team.tenant_name)
            return Response(general_message(412, "region is not usable", msg_cn), status=412)

        migrate_record = migrate_service.start_migrate(
            self.user, self.tenant, self.region_name, migrate_team, migrate_region,
            backup_id, migrate_type, event_id, restore_id)
        result = general_message(200, "success", "操作成功，开始迁移应用", bean=migrate_record.to_dict())
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
        restore_id = request.GET.get("restore_id", None)
        if not restore_id:
            return Response(general_message(400, "restore id is null", "请指明查询的备份ID"), status=400)
        migrate_record = migrate_service.get_and_save_migrate_status(self.user, restore_id)
        if not migrate_record:
            return Response(general_message(404, "not found record", "记录不存在"), status=404)
        result = general_message(200, "success", "查询成功", bean=migrate_record.to_dict())
        return Response(result, status=result["code"])


class GroupAppsView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def delete(self, request, *args, **kwargs):
        """
        应用数据删除
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
            - name: new_group_id
              description: 组ID
              required: true
              type: string
              paramType: query

        """
        try:
            group_id = int(kwargs.get("group_id", None))
            if not group_id:
                return Response(general_message(400, "group id is null", "请确认需要删除的组"), status=400)
            new_group_id = request.data.get("new_group_id", None)
            if not new_group_id:
                return Response(general_message(400, "new group id is null", "请确认新恢复的组"), status=400)
            if group_id == new_group_id:
                return Response(general_message(200, "success", "恢复到当前组无需删除"), status=200)
            group = group_repo.get_group_by_id(group_id)
            if not group:
                return Response(general_message(400, "group is delete", "该备份组已删除"), status=400)

            new_group = group_repo.get_group_by_id(new_group_id)
            if not new_group:
                return Response(
                    general_message(400, "new group not exist", "组ID {0} 不存在".format(new_group_id)),
                    status=400)
            services = group_service.get_group_services(group_id)
            for service in services:
                try:
                    app_manage_service.truncate_service(self.tenant, service)
                except Exception as le:
                    logger.exception(le)

            group.delete()

            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class MigrateRecordView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def get(self, request, group_id, *args, **kwargs):
        """
        查询当前用户是否有未完成的恢复和迁移
        ---
            name: group_id
            description: 应用id
            required: true
            type: string
            paramType: path

        """
        group_uuid = request.GET.get("group_uuid", None)
        if not group_uuid:
            return Response(general_message(400, "parameters are missing", "参数缺失"), status=400)
        unfinished_migrate_records = migrate_repo.get_user_unfinished_migrate_record(group_uuid)
        is_finished = True
        data = None
        if unfinished_migrate_records:
            r = unfinished_migrate_records[0]
            data = {
                "status": r.status,
                "event_id": r.event_id,
                "migrate_type": r.migrate_type,
                "restore_id": r.restore_id,
                "backup_id": r.backup_id,
                "group_id": r.group_id,
            }
            is_finished = False

        bean = {"is_finished": is_finished, "data": data}
        return Response(general_message(200, "success", "查询成功", bean=bean), status=200)
