# -*- coding: utf-8 -*-
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from console.services.file_upload_service import upload_service
from openapi.views.base import BaseOpenAPIView


class UploadFileReqSerializer(serializers.Serializer):
    file = serializers.FileField(help_text=u"需要上传的文件")


class UploadFileRespSerializer(serializers.Serializer):
    file_url = serializers.CharField(max_length=1024, required=True, help_text=u"访问文件的URL")


class UploadView(BaseOpenAPIView):
    parser_classes = (MultiPartParser, )

    @swagger_auto_schema(
        operation_description="上传文件",
        manual_parameters=[
            openapi.Parameter("file", openapi.IN_FORM, description="文件", type=openapi.TYPE_FILE),
        ],
        responses={status.HTTP_200_OK: UploadFileRespSerializer()},
        tags=['openapi-upload'],
    )
    def post(self, request):
        req = UploadFileReqSerializer(data=request.FILES)
        req.is_valid(raise_exception=True)

        if not request.FILES or not request.FILES.get('file'):
            raise serializers.ValidationError("请指定需要上传的文件", status.HTTP_400_BAD_REQUEST)
        upload_file = request.FILES.get('file')
        if upload_file.size > 1048576 * 2:
            raise serializers.ValidationError("图片大小不能超过2M", status.HTTP_400_BAD_REQUEST)

        suffix = upload_file.name.split('.')[-1]
        file_url = upload_service.upload_file(upload_file, suffix)
        if not file_url:
            raise serializers.ValidationError("上传失败", status.HTTP_400_BAD_REQUEST)

        serializer = UploadFileRespSerializer(data={"file_url": file_url})
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)
