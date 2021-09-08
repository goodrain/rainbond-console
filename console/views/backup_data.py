# -*- coding: utf-8 -*-
from console.services.backup_data_service import platform_data_services
from console.views.base import EnterpriseAdminView
from django.contrib.auth import authenticate
from rest_framework.response import Response
from www.utils.return_message import general_message


class BackupDataCView(EnterpriseAdminView):
    def get(self, request, *args, **kwargs):
        backups = platform_data_services.list_backups()
        result = general_message(200, "success", "数据上传成功", list=backups)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        platform_data_services.create_backup()
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])

    def delete(self, request, *args, **kwargs):
        name = request.data.get("name")
        if not name:
            result = general_message(200, "backup file can not be empty", "备份文件名称不能为空")
        else:
            platform_data_services.remove_backup(name)
            result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])


class BackupDateDownload(EnterpriseAdminView):
    def get(self, request, backup_name, *args, **kwargs):
        return platform_data_services.download_file(backup_name)


class BackupUploadCView(EnterpriseAdminView):
    def post(self, request, *args, **kwargs):
        if not request.FILES or not request.FILES.get('file'):
            return Response(general_message(400, "param error", "请指定需要上传的文件"), status=400)

        upload_file = request.FILES.get('file')
        suffix = upload_file.name.split('.')[-1]
        if suffix != "gz":
            return Response(general_message(400, "param error", "请上传以 tar.gz 结尾的数据备份文件"), status=400)
        # upload file
        platform_data_services.upload_file(upload_file)
        result = general_message(200, "success", "数据上传成功")
        return Response(result, status=result["code"])


class BackupRecoverCView(EnterpriseAdminView):
    def post(self, request, *args, **kwargs):
        name = request.data.get("name")
        password = request.data.get("password")
        u = authenticate(username=request.user.get_username(), password=password)
        if not u:
            return Response(general_message(400, "param error", "输入密码不正确"), status=400)
        if not name:
            result = general_message(200, "backup file can not be empty", "备份文件名称不能为空")
        else:
            platform_data_services.recover_platform_data(name)
            result = general_message(200, "success", "恢复成功")
        return Response(result, status=result["code"])
