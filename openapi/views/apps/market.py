# -*- coding: utf-8 -*-
# creater by: barnett

import logging
from drf_yasg.utils import swagger_auto_schema
from openapi.views.base import BaseOpenAPIView
from rest_framework import status
from openapi.serializer.base_serializer import FailSerializer
from rest_framework.response import Response
from django.forms.models import model_to_dict
from openapi.serializer.app_serializer import MarketInstallSerializer, ServiceBaseInfoSerializer, AppInfoSerializer
from console.services.group_service import group_service
from console.services.team_services import team_services
from console.services.market_app_service import market_app_service
from console.services.market_app_service import market_sycn_service
from console.utils.restful_client import get_market_client

logger = logging.getLogger("default")


# Install cloud city application, which is implemented by a simplified scheme.
# Users provide cloud city application information and initiate to download application metadata to the application market.
class MarketAppInstallView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="安装云市应用",
        request_body=MarketInstallSerializer(),
        responses={200: AppInfoSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        serializer = MarketInstallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        logger.info(data)
        app = group_service.get_app_by_pk(data["app_id"])
        if not app:
            return Response(FailSerializer({"msg": "install target app not found"}), status=status.HTTP_400_BAD_REQUEST)
        tenant = team_services.get_team_by_team_id(app.tenant_id)
        # TODO: get app info by order id
        token = market_sycn_service.get_enterprise_access_token(tenant.enterprise_id, "market")
        if token:
            market_client = get_market_client(token.access_id, token.access_token, token.access_url)
            app_version = market_client.download_app_by_order(order_id=data["order_id"])
            if not app_version:
                return Response(FailSerializer({"msg": "download app metadata failure"}), status=status.HTTP_400_BAD_REQUEST)
            rainbond_app, rainbond_app_version = market_app_service.conversion_cloud_version_to_app(app_version)
            market_app_service.install_service(tenant, app.region_name, request.user, app.ID, rainbond_app,
                                               rainbond_app_version, True, True)
            services = group_service.get_group_services(data["app_id"])
            appInfo = model_to_dict(app)
            appInfo["enterprise_id"] = tenant.enterprise_id
            appInfo["service_list"] = ServiceBaseInfoSerializer(services, many=True)
            reapp = AppInfoSerializer(data=appInfo)
            reapp.is_valid()
            return Response(reapp.data, status=status.HTTP_200_OK)
        else:
            return Response(
                FailSerializer({"msg": "not support install from market, not bound"}), status=status.HTTP_400_BAD_REQUEST)
