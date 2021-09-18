# -*- coding: utf-8 -*-
# creater by: barnett

import logging

from console.exception.main import ServiceHandleException
from console.services.app import app_market_service
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from console.services.upgrade_services import upgrade_service
from django.forms.models import model_to_dict
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.serializer.app_serializer import (InstallSerializer, ListUpgradeSerializer, MarketInstallSerializer,
                                               UpgradeSerializer)
from openapi.views.base import EnterpriseServiceOauthView, TeamAppAPIView
from rest_framework import status
from rest_framework.response import Response
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


# Install cloud city application, which is implemented by a simplified scheme.
# Users provide cloud city application information and initiate to download application metadata to the application market.
class AppInstallView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="安装云市应用",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用组id", type=openapi.TYPE_INTEGER),
            openapi.Parameter(
                "is_deploy", openapi.IN_QUERY, description="是否构建", type=openapi.TYPE_STRING, enum=["true", "false"]),
        ],
        request_body=InstallSerializer(),
        responses={200: MarketInstallSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, app_id, *args, **kwargs):
        is_deploy = request.GET.get("is_deploy", False)
        if is_deploy == "true":
            is_deploy = True
        serializer = InstallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        market_url = serializer.data.get("market_url")
        market_domain = serializer.data.get("market_domain")
        market_type = serializer.data.get("market_type")
        market_access_key = serializer.data.get("market_access_key")
        app_model_id = serializer.data.get("app_model_id")
        app_model_version = serializer.data.get("app_model_version")
        market = app_market_service.get_app_market_by_domain_url(self.team.enterprise_id, market_domain, market_url)
        if not market:
            market_name = make_uuid()
            dt = {
                "name": market_name,
                "url": market_url,
                "type": market_type,
                "enterprise_id": self.team.enterprise_id,
                "access_key": market_access_key,
                "domain": market_domain,
            }
            app_market_service.create_app_market(dt)
            dt, market = app_market_service.get_app_market(self.team.enterprise_id, market_name, raise_exception=True)
        market_name = market.name
        app, app_version_info = app_market_service.cloud_app_model_to_db_model(
            market, app_model_id, app_model_version, for_install=True)
        if not app:
            raise ServiceHandleException(status_code=404, msg="not found", msg_show="云端应用不存在")
        if not app_version_info:
            raise ServiceHandleException(status_code=404, msg="not found", msg_show="云端应用版本不存在")
        market_app_service.install_service(
            self.team, self.region_name, self.user, app_id, app, app_version_info, is_deploy, True, market_name=market_name)
        services = group_service.get_group_services(app_id)
        app_info = model_to_dict(self.app)
        app_info["app_name"] = app_info["group_name"]
        app_info["team_id"] = app_info["tenant_id"]
        app_info["enterprise_id"] = self.team.enterprise_id
        app_info["service_list"] = services
        reapp = MarketInstallSerializer(data=app_info)
        reapp.is_valid()
        return Response(reapp.data, status=status.HTTP_200_OK)


# 应用升级
class AppUpgradeView(TeamAppAPIView, EnterpriseServiceOauthView):
    @swagger_auto_schema(
        operation_description="升级应用",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用组id", type=openapi.TYPE_INTEGER),
        ],
        responses={200: ListUpgradeSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, request, *args, **kwargs):
        app_models = market_app_service.get_market_apps_in_app(self.region_name, self.team, self.app)
        serializer = ListUpgradeSerializer(data=app_models, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        operation_description="升级应用",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用组id", type=openapi.TYPE_INTEGER),
        ],
        request_body=UpgradeSerializer(),
        responses={200: ListUpgradeSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        serializer = UpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upgrade_service.openapi_upgrade_app_models(self.user, self.team, self.region_name, self.oauth_instance, self.app.ID,
                                                   serializer.data)
        app_models = market_app_service.get_market_apps_in_app(self.region_name, self.team, self.app)
        serializer = ListUpgradeSerializer(data=app_models, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=200)
