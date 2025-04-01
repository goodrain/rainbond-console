# -*- coding: utf8 -*-
"""
  Created on 18/5/23.
"""
import json
import logging
import io
import urllib

from django.http import StreamingHttpResponse
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.constants import StorageUnit
from console.repositories.group import group_repo
from console.services.backup_service import groupapp_backup_service
from console.services.config_service import EnterpriseConfigService
from console.services.operation_log import operation_log_service, OperationType
from console.services.team_services import team_services
from console.views.base import AlowAnyApiView
from console.views.base import RegionTenantHeaderView
from goodrain_web.tools import JuncheePaginator
from www.utils.return_message import error_message
from www.utils.return_message import general_message

logger = logging.getLogger('default')


class GroupAppsBackupView(RegionTenantHeaderView):
    @never_cache
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
              type: string
              paramType: form
            - name: mode
              description: 备份模式（full-online|full-offline）
              required: true
              type: string
              paramType: form
        """
        group_id = int(kwargs.get("group_id", None))
        if not group_id:
            return Response(general_message(400, "group id is null", "请选择需要备份的组"), status=400)
        note = request.data.get("note", None)
        if not note:
            return Response(general_message(400, "note is null", "请填写备份信息"), status=400)
        mode = request.data.get("mode", None)
        if not mode:
            return Response(general_message(400, "mode is null", "请选择备份模式"), status=400)

        force = request.data.get("force", False)
        if not force:
            # state service can't backup while it is running
            code, running_state_services = groupapp_backup_service.check_backup_condition(
                self.tenant, self.region_name, group_id)
            if running_state_services:
                return Response(
                    general_message(
                        code=4121, msg="state service is running", msg_show="有状态组件未关闭", list=running_state_services),
                    status=412)
            # if service use custom service, can't backup
            use_custom_svc = groupapp_backup_service.check_backup_app_used_custom_volume(group_id)
            if use_custom_svc:
                logger.info("use custom volume: {}".format(use_custom_svc))
                return Response(
                    general_message(code=4122, msg="use custom volume", msg_show="组件使用了自定义存储", list=use_custom_svc), status=412)

        back_up_record = groupapp_backup_service.backup_group_apps(self.tenant, self.user, self.region_name, group_id, mode,
                                                                   note, force)

        bean = back_up_record.to_dict()
        result = general_message(200, "success", "操作成功，正在备份中", bean=bean)
        new_information = json.dumps({"备份类型": "本地备份" if mode == "full-offline" else "云端备份", "备份说明": note},
                                     ensure_ascii=False)
        operation_log_service.create_app_log(self, "备份了应用{app}", new_information=new_information)
        return Response(result, status=result["code"])

    @never_cache
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
            code, msg, backup_record = groupapp_backup_service.get_groupapp_backup_status_by_backup_id(
                self.tenant, self.response_region, backup_id)
            if code != 200:
                return Response(general_message(code, "get backup status error", msg), status=code)
            bean = backup_record.to_dict()
            bean.pop("backup_server_info")

            result = general_message(200, "success", "查询成功", bean=bean)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        根据应用备份ID删除备份
        """
        backup_id = request.data.get("backup_id", None)

        code, msg, backup_record = groupapp_backup_service.get_groupapp_backup_status_by_backup_id(
            self.tenant, self.response_region, backup_id)
        old_information = json.dumps({
            "备份类型": "本地备份" if backup_record.mode == "full-offline" else "云端备份",
            "备份说明": backup_record.note
        },
            ensure_ascii=False)

        if not backup_id:
            return Response(general_message(400, "backup id is null", "请指明当前组的具体备份项"), status=400)
        groupapp_backup_service.delete_group_backup_by_backup_id(self.tenant, self.response_region, backup_id)
        operation_log_service.create_app_log(self, "删除了应用{app}的备份", old_information=old_information)

        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])


class GroupAppsBackupStatusView(RegionTenantHeaderView):
    @never_cache
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
            code, msg, backup_records = groupapp_backup_service.get_group_backup_status_by_group_id(
                self.tenant, self.response_region, group_id)
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
        group_id = request.GET.get("group_id", None)
        if not group_id:
            return Response(general_message(400, "group id is not found", "请指定需要查询的组"), status=400)
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))

        backups = groupapp_backup_service.get_group_back_up_info(self.tenant, self.region_name, group_id)
        paginator = JuncheePaginator(backups, int(page_size))
        backup_records = paginator.page(int(page))
        obj_storage = EnterpriseConfigService(self.user.enterprise_id, self.user.user_id).get_cloud_obj_storage_info()
        bean = {"is_configed": obj_storage is not None}
        result = general_message(
            200, "success", "查询成功", bean=bean, list=[backup.to_dict() for backup in backup_records], total=paginator.count)
        return Response(result, status=result["code"])


class AllTeamGroupAppsBackupView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        查询当前团队 数据中心下所有备份信息
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
        """
        try:
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))
            backups = groupapp_backup_service.get_all_group_back_up_info(self.tenant, self.response_region)
            paginator = JuncheePaginator(backups, int(page_size))
            backup_records = paginator.page(int(page))
            backup_list = list()
            if backup_records:
                for backup in backup_records:
                    backup_dict = backup.to_dict()
                    group_obj = group_repo.get_group_by_id(backup_dict["group_id"])
                    if group_obj:
                        backup_dict["group_name"] = group_obj.group_name
                        backup_dict["is_delete"] = False
                    else:
                        backup_dict["group_name"] = "应用已删除"
                        backup_dict["is_delete"] = True
                    backup_list.append(backup_dict)
            result = general_message(200, "success", "查询成功", list=backup_list, total=paginator.count)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class GroupAppsBackupExportView(AlowAnyApiView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        一个组的备份导出
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
                return Response(general_message(400, "group id is null", "请选择需要导出备份的组"), status=400)
            team_name = kwargs.get("tenantName", None)
            if not team_name:
                return Response(general_message(400, "group id is null", "请选择需要导出备份的组"), status=400)
            team = team_services.get_tenant_by_tenant_name(team_name)
            if not team:
                return Response(general_message(404, "team not found", "团队{0}不存在".format(team_name)), status=404)
            group = group_repo.get_group_by_id(group_id)
            if not group:
                return Response(general_message(404, "group not found", "组{0}不存在".format(group_id)), status=404)
            backup_id = request.GET.get("backup_id", None)
            if not backup_id:
                return Response(general_message(400, "backup id is null", "请指明当前组的具体备份项"), status=400)

            code, msg, data_str = groupapp_backup_service.export_group_backup(team, backup_id)
            if code != 200:
                return Response(general_message(code, "export backup failed", msg), status=code)
            file_name = group.group_name + ".bak"
            output = io.StringIO()
            output.write(data_str)
            res = StreamingHttpResponse(output.getvalue())
            res['Content-Type'] = 'application/octet-stream'
            res['Content-Disposition'] = "attachment;filename*=UTF-8''" + urllib.parse.quote(file_name)

            app = operation_log_service.process_app_name(group.group_name, group.region_name, team.tenant_name, group.app_id)
            comment = "导出了应用{}的备份".format(app)
            operation_log_service.create_log("", OperationType.APPLICATION_MANAGE, comment, team.enterprise_id,
                                             team.tenant_name, group.app_id)

            return res
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])


class GroupAppsBackupImportView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        导入备份
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: file
              description:
              required: true
              type: file
              paramType: form
        """
        try:
            group_id = int(kwargs.get("group_id", None))
            if not group_id:
                return Response(general_message(400, "group id is null", "请选择需要导出备份的组"), status=400)
            if not request.FILES or not request.FILES.get('file'):
                return Response(general_message(400, "param error", "请指定需要导入的备份信息"), status=400)
            upload_file = request.FILES.get('file')
            if upload_file.size > StorageUnit.ONE_MB * 2:
                return Response(general_message(400, "file is too large", "文件大小不能超过2M"), status=400)
            code, msg, record = groupapp_backup_service.import_group_backup(self.tenant, self.response_region, group_id,
                                                                            upload_file)
            if code != 200:
                return Response(general_message(code, "backup import failed", msg), status=code)
            result = general_message(200, "success", "导入成功", bean=record.to_dict())
            operation_log_service.create_app_log(self, "导入了应用{app}的备份")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
