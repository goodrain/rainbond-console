# -*- coding: utf8 -*-
"""
  Created on 18/1/9.
"""
import logging
import os

from rest_framework.response import Response

from console.services.git_service import GitCodeService
from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message
from console.services.file_upload_service import upload_service

logger = logging.getLogger("default")
git_service = GitCodeService()


class ConsoleUploadFileView(JWTAuthApiView):
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
        if not request.FILES or not request.FILES.get('file'):
            return Response(general_message(400, "param error", "请指定需要上传的文件"), status=400)
        upload_file = request.FILES.get('file')
        if upload_file.size > 1048576 * 2:
            return Response(general_message(400, "file is too large", "图片大小不能超过2M"), status=400)

        ext = os.path.splitext(upload_file.name)[1].lower()
        allowed_extensions = ['.jpg', '.png', '.gif', '.jpeg']
        if ext not in allowed_extensions:
            return Response(general_message(400, "The image format is currently not supported", "图片格式暂不支持"), status=400)
        suffix = upload_file.name.split('.')[-1]
        file_url = upload_service.upload_file(upload_file, suffix)
        if not file_url:
            result = general_message(400, "upload file error", "上传失败")
        else:
            result = general_message(200, "file upload success", "上传成功", bean={"file_url": file_url})
        return Response(result, status=result["code"])
