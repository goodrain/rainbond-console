# -*- coding: utf8 -*-
"""
  Created on 18/5/5.
"""
import contextlib
import logging
import urllib2

from django.http import StreamingHttpResponse
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app_import_and_export_service import export_service
from console.services.market_app_service import market_app_service
from console.views.base import AlowAnyApiView, JWTAuthApiView
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
              description: 导出类型 rainbond-app | docker-compose
              required: true
              type: string
              paramType: form
        """
        app_id = request.data.get("app_id", None)
        app_versions = request.data.get("app_versions", [])
        export_format = request.data.get("format", None)
        if not app_id or not app_versions:
            return Response(general_message(400, "app id is null", "请指明需要导出的应用"), status=400)
        if not export_format or export_format not in ("rainbond-app", "docker-compose"):
            return Response(general_message(400, "export format is illegal", "请指明导出格式"), status=400)

        new_export_record_list = []
        record = export_service.export_app(enterprise_id, app_id, app_versions[0], export_format)
        new_export_record_list.append(record.to_dict())

        result = general_message(200, "success", "操作成功，正在导出", list=new_export_record_list)
        return Response(result, status=result["code"])


class ExportFileDownLoadView(AlowAnyApiView):
    @never_cache
    def get(self, request, tenantName, *args, **kwargs):
        """
        下载应用包
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: format
              description: 导出类型 rainbond-app | docker-compose
              required: true
              type: string
              paramType: form
            - name: app_id
              description: rainbond app id
              required: true
              type: string
              paramType: query

        """
        app_id = request.GET.get("app_id", None)
        export_format = request.GET.get("format", None)
        if not app_id:
            return Response(general_message(400, "app id is null", "请指明需要下载的应用"), status=400)
        if not export_format or export_format not in ("rainbond-app", "docker-compose"):
            return Response(general_message(400, "export format is illegal", "请指明下载的格式"), status=400)

        code, app = market_app_service.get_rain_bond_app_by_pk(app_id)
        if not app:
            return Response(general_message(404, "not found", "云市应用不存在"), status=404)

        export_record = export_service.get_export_record(export_format, app)
        if not export_record:
            return Response(general_message(400, "no export records", "该应用无导出记录，无法下载"), status=400)
        if export_record.status != "success":
            if export_record.status == "failed":
                return Response(general_message(400, "export failed", "应用导出失败，请重试"), status=400)
            if export_record.status == "exporting":
                return Response(general_message(400, "exporting", "应用正在导出中，请稍后重试"), status=400)

        req, file_name = export_service.get_file_down_req(export_format, tenantName, app)

        response = StreamingHttpResponse(self.file_iterator(req))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file_name)
        return response

    def file_iterator(self, r, chunk_size=2048):
        with contextlib.closing(urllib2.urlopen(r)) as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break
