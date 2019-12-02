# -*- coding: utf8 -*-
import datetime
import logging

from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from console.repositories.app import service_source_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message
from www.models.main import TenantServiceInfo, Tenants
from openapi.views.base import BaseOpenAPIView
from openapi.serializer.base_serializer import FailSerializer
from openapi.serializer.app_serializer import BuildSourceInfoSerializer
from openapi.serializer.app_serializer import BuildSourceUpdateSerializer

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class BuildSourceInfo(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取构建源信息",
        responses={status.HTTP_200_OK: BuildSourceInfoSerializer(),
                   status.HTTP_400_BAD_REQUEST: FailSerializer()},
        tags=['openapi-app'],
    )
    def get(self, request, tenant_name, service_alias, *args, **kwargs):
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        service = TenantServiceInfo.objects.filter(service_alias=service_alias, tenant_id=tenant.tenant_id).first()
        try:
            bean = {
                "service_source": service.service_source,
                "image": service.image,
                "cmd": service.cmd,
                "code_from": service.code_from,
                "version": service.version,
                "docker_cmd": service.docker_cmd,
                "create_time": service.create_time,
                "git_url": service.git_url,
                "code_version": service.code_version,
                "server_type": service.server_type,
                "language": service.language,
            }
            serializer = BuildSourceInfoSerializer(bean)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.debug(e)
            return Response({"msg": e}, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="修改构建源信息",
        request_body=BuildSourceUpdateSerializer(),
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_400_BAD_REQUEST: FailSerializer(),
        },
        tags=['openapi-app'],
    )
    def put(self, request, tenant_name, service_alias, *args, **kwargs):
        s_id = transaction.savepoint()
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        service = TenantServiceInfo.objects.filter(service_alias=service_alias, tenant_id=tenant.tenant_id).first()
        try:
            serializer = BuildSourceUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            image = serializer.data.get("image", None)
            cmd = serializer.data.get("cmd", None)
            service_source = serializer.data.get("service_source")
            git_url = serializer.data.get("git_url", None)
            code_version = serializer.data.get("code_version", None)
            user_name = serializer.data.get("user_name", None)
            password = serializer.data.get("password", None)
            if not service_source:
                return Response(general_message(400, "param error", "参数错误"), status=400)

            service_source_user = service_source_repo.get_service_source(
                team_id=service.tenant_id, service_id=service.service_id)

            if not service_source_user:
                service_source_info = {
                    "service_id": service.service_id,
                    "team_id": service.tenant_id,
                    "user_name": user_name,
                    "password": password,
                    "create_time": datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                }
                service_source_repo.create_service_source(**service_source_info)
            else:
                service_source_user.user_name = user_name
                service_source_user.password = password
                service_source_user.save()
            if service_source == "source_code":

                if code_version:
                    service.code_version = code_version
                else:
                    service.code_version = "master"
                if git_url:
                    service.git_url = git_url
                service.save()
                transaction.savepoint_commit(s_id)
            elif service_source == "docker_run":
                if image:
                    version = image.split(':')[-1]
                    if not version:
                        version = "latest"
                        image = image + ":" + version
                    service.image = image
                    service.version = version
                service.cmd = cmd
                service.save()
                transaction.savepoint_commit(s_id)
            return Response(None, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(e)
            transaction.savepoint_rollback(s_id)
            return Response({"msg": e}, status=status.HTTP_200_OK)
