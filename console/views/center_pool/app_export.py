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

from console.exception.main import ResourceNotEnoughException, AccountOverdueException
from console.services.app_import_and_export_service import export_service
from console.services.market_app_service import market_app_service
from console.views.base import RegionTenantHeaderView, AlowAnyApiView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message

logger = logging.getLogger('default')


class CenterAppExportView(RegionTenantHeaderView):
    @never_cache
    @perm_required("tenant_access")
    def get(self, request, *args, **kwargs):
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
        try:
            group_key = request.GET.get("group_key", None)
            group_version = request.GET.get("group_version", None)
            if not group_key or not group_version:
                return Response(general_message(400, "app id is null", "请指明需要查询的应用"), status=400)

            result_list = []
            group_version_list = group_version.split("#")
            for version in group_version_list:
                code, app = market_app_service.get_rain_bond_app_by_key_and_version(group_key, version)
                if not app:
                    return Response(general_message(404, "not found", "云市应用不存在"), status=404)
                code, msg, result = export_service.get_export_status(self.tenant, app)
                if code != 200:
                    return Response(general_message(code, "get export info error ", msg), status=code)
                result_list.append(result)

            result = general_message(200, "success", "查询成功", list=result_list)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required("import_and_export_service")
    def post(self, request, *args, **kwargs):
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
        try:
            group_key = request.data.get("group_key", None)
            group_version = request.data.get("group_version", [])
            export_format = request.data.get("format", None)
            if not group_key or not group_version:
                return Response(general_message(400, "app id is null", "请指明需要导出的应用"), status=400)
            if not export_format or export_format not in ("rainbond-app", "docker-compose",):
                return Response(general_message(400, "export format is illegal", "请指明导出格式"), status=400)
            new_export_record_list = []
            for version in group_version:
                code, app = market_app_service.get_rain_bond_app_by_key_and_version(group_key, version)
                if not app:
                    return Response(general_message(404, "not found", "云市应用不存在"), status=404)

                code, msg, new_export_record = export_service.export_current_app(self.tenant, export_format, app)
                if code != 200:
                    return Response(general_message(code, "export error", msg), status=code)

                new_export_record_list.append(new_export_record.to_dict())

            result = general_message(200, "success", "操作成功，正在导出", list=new_export_record_list)
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
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
        try:
            app_id = request.GET.get("app_id", None)
            export_format = request.GET.get("format", None)
            if not app_id:
                return Response(general_message(400, "app id is null", "请指明需要下载的应用"), status=400)
            if not export_format or export_format not in ("rainbond-app", "docker-compose",):
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
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])

    def file_iterator(self, r, chunk_size=2048):
        with contextlib.closing(urllib2.urlopen(r)) as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break
