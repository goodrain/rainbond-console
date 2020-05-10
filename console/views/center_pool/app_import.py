# -*- coding: utf8 -*-
"""
  Created on 18/5/5.
"""
import logging

from console.exception.main import AbortRequest
from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from console.services.region_services import region_services
from console.services.file_upload_service import upload_service
from console.views.base import RegionTenantHeaderView
from console.views.base import JWTAuthApiView
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


class CenterAppUploadView(JWTAuthApiView):
    @never_cache
    def post(self, request, enterprise_id, *args, **kwargs):
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
            code, msg, import_record = upload_service.upload_file_to_region_center_by_enterprise_id(
                enterprise_id, self.user.nick_name, upload_file)
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


class EnterpriseAppImportInitView(JWTAuthApiView):
    @never_cache
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
        eid = kwargs.get("enterprise_id", "")
        unfinished_records = import_service.get_user_not_finish_import_record_in_enterprise(eid, self.user)
        if unfinished_records:
            r = unfinished_records[0]
        else:
            r = import_service.create_app_import_record_2_enterprise(eid, self.user.nick_name)
        upload_url = import_service.get_upload_url(r.region, r.event_id)
        region = region_services.get_region_by_region_name(r.region)
        data = {
            "status": r.status,
            "source_dir": r.source_dir,
            "event_id": r.event_id,
            "upload_url": upload_url,
            "region_name": region.region_alias,
        }

        return Response(general_message(200, "success", "查询成功", bean=data), status=200)


class CenterAppImportView(JWTAuthApiView):
    @never_cache
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
            team_name = request.data.get("tenant_name", None)
            if not scope:
                raise AbortRequest(msg="select the scope", msg_show="请选择导入应用可见范围")
            if scope == "team" and not team_name:
                raise AbortRequest(msg="select the team", msg_show="请选择要导入的团队")
            if not file_name:
                raise AbortRequest(msg="file name is null", msg_show="请选择要导入的文件")
            if not event_id:
                raise AbortRequest(msg="event is not found", msg_show="参数错误，未提供事件ID")
            files = file_name.split(",")
            import_service.start_import_apps(scope, event_id, files, team_name)
            result = general_message(200, 'success', "操作成功，正在导入")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
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
            record, apps_status = import_service.get_and_update_import_by_event_id(event_id)
            transaction.savepoint_commit(sid)
            result = general_message(200, 'success', "查询成功", bean=record.to_dict(), list=apps_status)
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
            import_service.delete_import_app_dir_by_event_id(event_id)
            result = general_message(200, "success", "操作成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class CenterAppTarballDirView(JWTAuthApiView):
    @never_cache
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
            event_id = kwargs.get("event_id", None)
            if not event_id:
                return Response(general_message(400, "event id is null", "请指明需要查询的event id"), status=400)

            apps = import_service.get_import_app_dir(event_id)
            result = general_message(200, "success", "查询成功", list=apps)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

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
