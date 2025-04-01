# -*- coding: utf8 -*-
"""
  Created on 18/5/5.
"""
import json
import logging

from console.exception.main import AbortRequest, RegionNotFound
from console.services.app_import_and_export_service import import_service
from console.services.operation_log import operation_log_service, Operation, OperationModule
from console.services.region_services import region_services
from console.views.base import JWTAuthApiView
from django.db import transaction
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from www.utils.return_message import error_message, general_message

logger = logging.getLogger('default')


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
        new = False
        if unfinished_records:
            r = unfinished_records[len(unfinished_records) - 1]
            region = region_services.get_region_by_region_name(r.region)
            if not region:
                logger.warning("not found region for old import recoder")
                new = True
        else:
            new = True
        if new:
            try:
                r = import_service.create_app_import_record_2_enterprise(eid, self.user.nick_name)
            except RegionNotFound:
                return Response(general_message(200, "success", "查询成功", bean={"region_name": ''}), status=200)
        upload_url = import_service.get_upload_url(r.region, r.event_id)
        region = region_services.get_region_by_region_name(r.region)
        data = {
            "status": r.status,
            "source_dir": r.source_dir,
            "event_id": r.event_id,
            "upload_url": upload_url,
            "region_name": region.region_alias if region else '',
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
        # try:
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
        import_service.start_import_apps(scope, event_id, files, team_name, self.enterprise.enterprise_id)
        result = general_message(200, 'success', "操作成功，正在导入")
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.IMPORT, module=OperationModule.APPMODEL, module_name="")
        new_information = json.dumps({"导入团队": team_name, "导入文件": file_name, "可见范围": scope}, ensure_ascii=False)
        operation_log_service.create_component_library_log(
            user=self.user, comment=comment, enterprise_id=self.user.enterprise_id, new_information=new_information)
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
        arch = request.GET.get("arch")
        try:
            sid = transaction.savepoint()
            record, apps_status = import_service.get_and_update_import_by_event_id(event_id, arch)
            transaction.savepoint_commit(sid)
            result = general_message(200, 'success', "查询成功", bean=record.to_dict(), list=apps_status)
        except Exception as e:
            if sid:
                transaction.savepoint_rollback(sid)
            raise e
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
        event_id = kwargs.get("event_id", None)
        if not event_id:
            return Response(general_message(400, "event id is null", "请指明需要查询的event id"), status=400)

        apps = import_service.get_import_app_dir(event_id)
        result = general_message(200, "success", "查询成功", list=apps)
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
        import_record = import_service.create_import_app_dir(self.tenant, self.user, self.response_region)

        result = general_message(200, "success", "查询成功", bean=import_record.to_dict())
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
        event_id = request.GET.get("event_id", None)
        if not event_id:
            return Response(general_message(400, "event id is null", "请指明需要查询的event id"), status=400)

        import_record = import_service.delete_import_app_dir(self.tenant, self.response_region)

        result = general_message(200, "success", "查询成功", bean=import_record.to_dict())
        return Response(result, status=result["code"])
