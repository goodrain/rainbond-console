# -*- coding: utf-8 -*-
# creater by: barnett

import logging
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.views.base import TeamAppAPIView
from rest_framework import status
from openapi.serializer.base_serializer import FailSerializer
from rest_framework.response import Response
from django.forms.models import model_to_dict
from console.exception.main import ServiceHandleException
from openapi.serializer.app_serializer import InstallSerializer, ServiceBaseInfoSerializer, AppInfoSerializer
from console.services.group_service import group_service
from console.services.team_services import team_services
from console.services.market_app_service import market_app_service
from console.services.market_app_service import market_sycn_service
from console.services.app import app_market_service
from www.utils.crypt import make_uuid
from console.utils.restful_client import get_market_client

logger = logging.getLogger("default")


# Install cloud city application, which is implemented by a simplified scheme.
# Users provide cloud city application information and initiate to download application metadata to the application market.
class AppInstallView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="安装云市应用",
        manual_parameters=[
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用组id", type=openapi.TYPE_INTEGER),
        ],
        request_body=InstallSerializer(),
        responses={200: AppInfoSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, app_id, *args, **kwargs):
        is_deploy = request.GET.get("is_deploy", False)
        serializer = InstallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        market_url = serializer.data.get("market_url")
        market_domain = serializer.data.get("market_url")
        market_type = serializer.data.get("market_url")
        market_access_key = serializer.data.get("market_url")
        app_model_id = serializer.data.get("market_url")
        app_model_version = serializer.data.get("market_url")
        market = app_market_service.get_app_market_by_domain_url(self.team.enterprise_id, market_domain, market_url)
        market_name = market.name
        if not market:
            market_name = make_uuid()
            dt ={
                "name": market_name,
                "url": market_url,
                "type": market_type,
                "enterprise_id": self.team.enterprise_id,
                "access_key": market_access_key,
                "domain": market_domain,
            }
            app_market_service.create_app_market(dt)
            dt, market = app_market_service.get_app_market(self.team.enterprise_id, market_name, raise_exception=True)
        app, app_version_info = app_market_service.cloud_app_model_to_db_model(market, app_model_id, app_model_version)
        if not app:
            raise ServiceHandleException(status_code=404, msg="not found", msg_show="云端应用不存在")
        market_app_service.install_service(
            self.team,
            self.region_name,
            self.user,
            app_id,
            app,
            app_version_info,
            is_deploy,
            True,
            market_name=market_name)
        services = group_service.get_group_services(app_id)
        appInfo = model_to_dict(app)
        appInfo["enterprise_id"] = self.team.enterprise_id
        appInfo["service_list"] = ServiceBaseInfoSerializer(services, many=True)
        reapp = AppInfoSerializer(data=appInfo)
        reapp.is_valid()
        return Response(reapp.data, status=status.HTTP_200_OK)

# 应用升级
class AppUpgradeView(TeamAppAPIView):
    pass
