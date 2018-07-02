# -*- coding: utf8 -*-
"""
  Created on 18/5/23.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.views.base import RegionTenantHeaderView
from goodrain_web.tools import JuncheePaginator
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.backup_service import groupapp_backup_service

logger = logging.getLogger('default')


class GroupAppsBackupView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def post(self, request, *args, **kwargs):
        """
        应用备份
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
            - name: note
              description: 备份说明
              required: true
              type: file
              paramType: form
            - name: mode
              description: 备份模式（full-online|full-offline）
              required: true
              type: file
              paramType: form
        """
        try:
            group_id = int(kwargs.get("group_id", None))
            if not group_id:
                return Response(general_message(400, "group id is null", "请选择需要备份的组"), status=400)
            note = request.data.get("note", None)
            mode = request.data.get("mode", None)
            if not note:
                return Response(general_message(400, "note is null", "请填写备份信息"), status=400)
            if not mode:
                return Response(general_message(400, "mode is null", "请选择备份模式"), status=400)

            code, running_state_services = groupapp_backup_service.check_backup_condition(self.tenant,
                                                                                          self.response_region,
                                                                                          group_id)
            if running_state_services:
                return Response(general_message(412, "state service is not closed",
                                                "您有有状态服务未关闭,应用如下 {0}".format(",".join(running_state_services))),
                                status=412)
            back_up_record = groupapp_backup_service.back_up_group_apps(self.tenant, self.user, self.response_region,
                                                                        group_id,
                                                                        mode, note)

            bean = back_up_record.to_dict()
            bean.pop("backup_server_info")
            result = general_message(200, "success", "操作成功，正在备份中", bean=bean)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required("import_and_export_service")
    def get(self, request, *args, **kwargs):
        """
        根据应用备份ID查询备份状态
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
            - name: backup_id
              description: 备份id
              required: true
              type: string
              paramType: query
        """
        try:
            group_id = int(kwargs.get("group_id", None))
            if not group_id:
                return Response(general_message(400, "group id is null", "请选择需要备份的组"), status=400)
            backup_id = request.GET.get("backup_id", None)
            if not backup_id:
                return Response(general_message(400, "backup id is null", "请指明当前组的具体备份项"), status=400)
            code, msg, backup_record = groupapp_backup_service.get_groupapp_backup_status_by_backup_id(self.tenant,
                                                                                                       self.response_region,
                                                                                                       backup_id)
            if code != 200:
                return Response(general_message(code, "get backup status error", msg), status=code)
            bean = backup_record.to_dict()
            bean.pop("backup_server_info")

            result = general_message(200, "success", "查询成功", bean=bean)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class GroupAppsBackupStatusView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def get(self, request, *args, **kwargs):
        """
        一个组的备份状态查询
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
        """
        try:
            group_id = int(kwargs.get("group_id", None))
            if not group_id:
                return Response(general_message(400, "group id is null", "请选择需要备份的组"), status=400)
            code, msg, backup_records = groupapp_backup_service.get_group_backup_status_by_group_id(self.tenant,
                                                                                                    self.response_region,
                                                                                                    group_id)
            if code == 404:
                return Response(general_message(200, "success", "查询成功"), status=200)

            rt_list = []
            for backup_record in backup_records:
                rt_list.append(backup_record.to_dict().pop("backup_server_info"))

            result = general_message(200, "success", "查询成功", list=rt_list)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class TeamGroupAppsBackupView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def get(self, request, *args, **kwargs):
        """
        查询备份信息
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: page
              description: 页码
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页数量
              required: false
              type: string
              paramType: query
            - name: group_id
              description: 组ID
              required: true
              type: string
              paramType: query
        """
        try:
            group_id = request.GET.get("group_id", None)
            if not group_id:
                return Response(general_message(400, "group id is not found", "请指定需要查询的组"), status=400)
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))
            backups = groupapp_backup_service.get_group_back_up_info(self.tenant, self.response_region, group_id)
            paginator = JuncheePaginator(backups, int(page_size))
            backup_records = paginator.page(int(page))
            result = general_message(200, "success", "查询成功", list=[backup.to_dict() for backup in backup_records], total=paginator.count)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
