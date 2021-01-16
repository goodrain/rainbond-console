# -*- coding: utf-8 -*-
from rest_framework.response import Response

from console.views.base import JWTAuthApiView
from console.services.data_service import platform_data_services
from www.utils.return_message import general_message


class PlatDataCView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        data_path = platform_data_services.get_or_create_path()
        file_path = platform_data_services.export_platform_data(data_path=data_path, data_type="origin", is_deleted=True)
        return platform_data_services.download_file(file_path)


class PlatDataUView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        if not request.FILES or not request.FILES.get('file'):
            return Response(general_message(400, "param error", "请指定需要上传的文件"), status=400)

        upload_file = request.FILES.get('file')
        suffix = upload_file.name.split('.')[-1]

        # upload file
        data_path = platform_data_services.get_or_create_path()
        file_path = platform_data_services.upload_file(data_path, upload_file, suffix)
        # extract file
        extract_dir = platform_data_services.upzip_file(file_path)

        # backup platform data
        platform_data_services.export_platform_data(data_path=data_path, data_type="backup", is_deleted=True)
        # recover platform data
        platform_data_services.recover_platform_data(extract_dir)

        result = general_message(200, "success", "恢复数据成功")
        return Response(result, status=result["code"])
