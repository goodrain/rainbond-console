# -*- coding: utf8 -*-
"""
  Created on 18/5/5.
"""
import logging

from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.repositories.team_repo import team_repo
from console.services.file_upload_service import upload_service
from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.app_import_and_export_service import import_service

logger = logging.getLogger('default')


class ImportingRecordView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def post(self, request, *args, **kwargs):
        """
        查询导入记录，如果有未完成的记录返回未完成的记录，如果没有，创建新的导入记录
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path

        """
        unfinished_records = import_service.get_user_unfinished_import_record(self.tenant, self.user)
        if unfinished_records:
            r = unfinished_records[0]
        else:
            r = import_service.create_app_import_record(self.tenant.tenant_name, self.user.nick_name, self.response_region)
        upload_url = import_service.get_upload_url(self.response_region, r.event_id)
        data = {"status": r.status, "source_dir": r.source_dir, "event_id": r.event_id, "upload_url": upload_url}

        return Response(general_message(200, "success", "查询成功", bean=data), status=200)


class CenterAppUploadView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def post(self, request, *args, **kwargs):
        """
        上传应用包
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: file
              description: 文件上传
              required: true
              type: file
              paramType: form
        """
        upload_file = None
        try:
            upload_file = request.FILES.get("file")
            if not request.FILES or not upload_file:
                return Response(general_message(400, "param error", "请指定需要导入的应用包"), status=400)
            file_name = upload_file.name
            code, msg, import_record = upload_service.upload_file_to_region_center(self.tenant.tenant_name, self.user.nick_name,
                                                                                   self.response_region, upload_file)
            if code != 200:
                return Response(general_message(code, "upload file faild", msg), status=code)
            bean = import_record.to_dict()
            bean["file_name"] = file_name
            result = general_message(200, 'success', "上传成功", bean=bean)
            upload_file.close()
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            if upload_file:
                upload_file.close()
        return Response(result, status=result["code"])


class CenterAppImportView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def post(self, request, event_id, *args, **kwargs):
        """
        导入应用包
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: event_id
              description: 事件ID
              required: true
              type: string
              paramType: path
            - name: scope
              description: 导入范围
              required: true
              type: string
              paramType: form
            - name: file_name
              description: 导入文件名,多个文件名以英文逗号分隔
              required: true
              type: string
              paramType: form
        """
        try:
            scope = request.data.get("scope", None)
            file_name = request.data.get("file_name", None)
            tenant_name = request.data.get("tenant_name", None)

            if not scope:
                return Response(general_message(400, "param scope is null", "请指定导入应用可见范围"), status=400)
            if not file_name:
                return Response(general_message(400, "file name is null", "文件名称为空"), status=400)
            if not event_id:
                return Response(general_message(400, "event id is not found", "参数错误"), status=400)
            if tenant_name:
                tenant = team_repo.get_team_by_team_name(tenant_name)
            else:
                tenant = self.tenant
            files = file_name.split(",")
            import_service.start_import_apps(tenant, self.response_region, scope, event_id, files)
            result = general_message(200, 'success', "操作成功，正在导入")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required("import_and_export_service")
    @transaction.atomic
    def get(self, request, event_id, *args, **kwargs):
        """
        查询应用包导入状态
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: event_id
              description: 事件ID
              required: true
              type: string
              paramType: path
        """
        sid = None
        try:
            sid = transaction.savepoint()
            import_record, apps_status = import_service.get_and_update_import_status(self.tenant, self.response_region,
                                                                                     event_id)
            transaction.savepoint_commit(sid)
            result = general_message(200, 'success', "查询成功", bean=import_record.to_dict(), list=apps_status)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            if sid:
                transaction.savepoint_rollback(sid)
        return Response(result, status=result["code"])

    def delete(self, request, event_id, *args, **kwargs):
        """
        放弃导入
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: event_id
              description: 事件ID
              required: true
              type: string
              paramType: path
        """
        try:
            import_service.delete_import_app_dir(self.tenant, self.response_region, event_id)
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CenterAppTarballDirView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def get(self, request, *args, **kwargs):
        """
        查询应用包目录
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: event_id
              description: 事件ID
              required: true
              type: string
              paramType: query
        """
        try:
            event_id = request.GET.get("event_id", None)
            if not event_id:
                return Response(general_message(400, "event id is null", "请指明需要查询的event id"), status=400)

            apps = import_service.get_import_app_dir(self.tenant, self.response_region, event_id)
            result = general_message(200, "success", "查询成功", list=apps)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @perm_required("import_and_export_service")
    def post(self, request, *args, **kwargs):
        """
        批量导入时创建一个目录
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
        """
        try:
            import_record = import_service.create_import_app_dir(self.tenant, self.user, self.response_region)

            result = general_message(200, "success", "查询成功", bean=import_record.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @perm_required("import_and_export_service")
    def delete(self, request, *args, **kwargs):
        """
        删除导入
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: event_id
              description: 事件ID
              required: true
              type: string
              paramType: query
        """
        try:
            event_id = request.GET.get("event_id", None)
            if not event_id:
                return Response(general_message(400, "event id is null", "请指明需要查询的event id"), status=400)

            import_record = import_service.delete_import_app_dir(self.tenant, self.response_region)

            result = general_message(200, "success", "查询成功", bean=import_record.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CenterAppImportingAppsView(RegionTenantHeaderView):
    @never_cache
    @perm_required("import_and_export_service")
    def get(self, request, *args, **kwargs):
        """
        查询仍在导入的应用
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
        """
        try:

            apps = import_service.get_importing_apps(self.tenant, self.user, self.response_region)
            result = general_message(200, "success", "查询成功", list=apps)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
