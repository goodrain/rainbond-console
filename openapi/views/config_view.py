# -*- coding: utf-8 -*-
# creater by: barnett
import logging

# from django.db import transaction
# from drf_yasg.utils import swagger_auto_schema
# from rest_framework import status
# from rest_framework.response import Response
#
# from console.models.main import ConsoleSysConfig
# from console.repositories.oauth_repo import oauth_repo
# from console.services.config_service import
# from console.services.enterprise_services import enterprise_services
# from openapi.serializer.config_serializers import BaseConfigRespSerializer
# from openapi.serializer.config_serializers import FeatureConfigRespSerializer
# from openapi.serializer.config_serializers import UpdateBaseConfigReqSerializer
# from openapi.serializer.config_serializers import UpdateFeatureCfgReqSerializer
# from openapi.views.base import BaseOpenAPIView

logger = logging.getLogger("default")

# class BaseConfigView(BaseOpenAPIView):
#     @swagger_auto_schema(
#         operation_description="获取基础配置",
#         responses={200: BaseConfigRespSerializer()},
#         tags=['openapi-config'],
#     )
#     def get(self, req):
#         ent = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id=req.user.enterprise_id)
#         if ent is None:
#             raise Response({"msg": "企业不存在"}, status.HTTP_404_NOT_FOUND)
#         data = config_service.list_by_keys(config_service.base_cfg_keys)
#         data["ENTERPRISE_ALIAS"] = ent.enterprise_alias
#         serializer = BaseConfigRespSerializer(data)
#         return Response(serializer.data)
#
#     @swagger_auto_schema(
#         operation_description="更新基础配置",
#         request_body=UpdateBaseConfigReqSerializer(),
#         responses={200: None},
#         tags=['openapi-config'],
#     )
#     @transaction.atomic
#     def put(self, req):
#         serializer = UpdateBaseConfigReqSerializer(data=req.data)
#         serializer.is_valid(raise_exception=True)
#         config_service.update_or_create(req.user.enterprise_id, req.data)
#         return Response(None, status=status.HTTP_200_OK)

# class ListFeatureConfigView(BaseOpenAPIView):
#     @swagger_auto_schema(
#         operation_description="获取全部功能配置",
#         responses={200: FeatureConfigRespSerializer()},
#         tags=['openapi-config'],
#     )
#     def get(self, request):
#         user = request.user
#         queryset = config_service.initialization_or_get_config()
#         oauth_services = []
#         services = oauth_repo.get_all_oauth_services(str(user.enterprise_id))
#
#         for service in services:
#             oauth_services.append(
#                 {
#                     "service_id": service.ID,
#                     "enable": service.enable,
#                     "name": service.name,
#                     "client_id": service.client_id,
#                     "auth_url": service.auth_url,
#                     "redirect_uri": service.redirect_uri,
#                     "oauth_type": service.oauth_type,
#                     "is_console": service.is_console,
#                     "home_url": service.home_url,
#                     "eid": service.eid,
#                     "access_token_url": service.access_token_url,
#                     "api_url": service.api_url,
#                     "client_secret": service.client_secret,
#                     "is_auto_login": service.is_auto_login
#                 }
#             )
#         queryset["oauth_services"]["value"] = oauth_services
#         serializer = FeatureConfigRespSerializer(queryset)
#         return Response(serializer.data)
#
#     @swagger_auto_schema(
#         operation_description="修改指定的功能配置及状态",
#         request_body=UpdateFeatureCfgReqSerializer(),
#         responses={
#             status.HTTP_200_OK: None,
#             status.HTTP_404_NOT_FOUND: None
#         },
#         tags=['openapi-config'],
#     )
#     def put(self, req):
#         serializer = UpdateFeatureCfgReqSerializer(data=req.data)
#         serializer.is_valid(raise_exception=True)
#         for key in serializer.validated_data.keys():
#             if key.upper() in config_service.feature_cfg_keys:
#                 data = serializer.validated_data[key]
#                 if "enable" in data.keys():
#                     enable = data.get("enable")
#                     if data.get("value"):
#                         if isinstance(data.get("value"), dict):
#                             value = dict(data.get("value"))
#                         elif isinstance(data.get("value"), list):
#                             value = list(data.get("value"))
#                         else:
#                             value = data.get("value")
#                     else:
#                         value = data.get("value")
#                     try:
#                         config_service.update_by_key(key, enable, value)
#                     except ConsoleSysConfig.DoesNotExist:
#                         return Response(None, status.HTTP_404_NOT_FOUND)
#                 else:
#                     return Response(u"缺少参数：enable", status.HTTP_400_BAD_REQUEST)
#                 return Response(None, status.HTTP_200_OK)
#             else:
#                 return Response(u"要配置的项目找不到", status.HTTP_400_BAD_REQUEST)
#
#
# class FeatureConfigView(BaseOpenAPIView):
#     @swagger_auto_schema(
#         operation_description="获取指定的功能配置",
#         responses={200: FeatureConfigRespSerializer()},
#         tags=['openapi-config'],
#     )
#     def get(self, req, key):
#         queryset = config_service.list_by_keys([key])
#         queryset["OPEN_DATA_CENTER_STATUS"] = queryset.get("OPEN_DATA_CENTER_STATUS", None)
#         if key.upper() == "OPEN_DATA_CENTER_STATUS" and queryset["OPEN_DATA_CENTER_STATUS"] is None:
#             queryset["OPEN_DATA_CENTER_STATUS"] = False
#         serializer = FeatureConfigRespSerializer(queryset)
#         return Response(serializer.data)
#
#     @swagger_auto_schema(
#         operation_description="删除指定的功能配置",
#         responses={
#             status.HTTP_200_OK: None,
#             status.HTTP_404_NOT_FOUND: None
#         },
#         tags=['openapi-config'],
#     )
#     def delete(self, req, key):
#         try:
#             config_service.delete_by_key(key)
#         except ConsoleSysConfig.DoesNotExist:
#             return Response(None, status.HTTP_404_NOT_FOUND)
#         return Response(None, status.HTTP_200_OK)
