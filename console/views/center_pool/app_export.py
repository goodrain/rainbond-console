# -*- coding: utf8 -*-
"""
  Created on 18/5/5.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app_import_and_export_service import export_service
from console.services.market_app_service import market_app_service
from console.services.operation_log import operation_log_service, Operation, OperationModule
from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message

logger = logging.getLogger('default')


class CenterAppExportView(JWTAuthApiView):
    @never_cache
    def get(self, request, enterprise_id, *args, **kwargs):
        """
        获取应用导出状态
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
        """
        app_id = request.GET.get("app_id", None)
        app_version = request.GET.get("app_version", None)
        if not app_id or not app_version:
            return Response(general_message(400, "app id is null", "请指明需要查询的应用"), status=400)

        result_list = []
        app_version_list = app_version.split("#")
        for version in app_version_list:
            app, app_version = market_app_service.get_rainbond_app_and_version(self.user.enterprise_id, app_id, version)
            if not app or not app_version:
                return Response(general_message(404, "not found", "云市应用不存在"), status=404)
            result = export_service.get_export_status(enterprise_id, app, app_version)
            result_list.append(result)

        result = general_message(200, "success", "查询成功", list=result_list)
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, enterprise_id, *args, **kwargs):
        """
        导出应用市场应用
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: format
              description: 导出类型 rainbond-app | docker-compose | slug
              required: true
              type: string
              paramType: form
        """
        app_id = request.data.get("app_id", None)
        app_versions = request.data.get("app_versions", [])
        export_format = request.data.get("format", None)
        image_handle = request.data.get("image_handle", "")
        if not app_id or not app_versions:
            return Response(general_message(400, "app id is null", "请指明需要导出的应用"), status=400)
        if not export_format or export_format not in ("rainbond-app", "docker-compose", "slug", "helm-chart"):
            return Response(general_message(400, "export format is illegal", "请指明导出格式"), status=400)
        helm_chart_parameter = {"image_handle": image_handle}
        new_export_record_list = []
        record = export_service.export_app(enterprise_id, app_id, app_versions[0], export_format, helm_chart_parameter)
        new_export_record_list.append(record.to_dict())

        result = general_message(200, "success", "操作成功，正在导出", list=new_export_record_list)
        app, app_version = market_app_service.get_rainbond_app_and_version(enterprise_id, app_id, app_versions[0])
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.EXPORT,
            module=OperationModule.APPMODEL,
            module_name="{} 的 {} 版本".format(app.app_name, app_version.version))
        operation_log_service.create_component_library_log(
            user=self.user, comment=comment, enterprise_id=self.user.enterprise_id)
        return Response(result, status=result["code"])
