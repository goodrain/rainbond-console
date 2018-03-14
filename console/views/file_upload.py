# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""
import logging

from rest_framework.response import Response

from console.services.git_service import GitCodeService
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import error_message, general_message
from console.services.file_upload_service import upload_service

logger = logging.getLogger("default")
git_service = GitCodeService()


class ConsoleUploadFileView(RegionTenantHeaderView):
    def post(self, request, *args, **kwargs):
        """
        上传文件
        ---
        parameters:
            - name: file
              description: 文件上传
              required: true
              type: file
              paramType: form

        """
        try:
            if not request.FILES or not request.FILES.get('file'):
                return Response(general_message(400, "param error", "请指定需要上传的文件"))
            upload_file = request.FILES.get('file')
            suffix = upload_file.name.split('.')[-1]
            file_url = upload_service.upload_file(upload_file, suffix)
            if not file_url:
                result = general_message(400,"upload file error", "上传失败")
            else:
                result = general_message(200, "file upload success", "上传成功", bean={"file_url": file_url})
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
