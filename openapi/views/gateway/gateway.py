# -*- coding: utf-8 -*-
# creater by: barnett

# -*- coding: utf-8 -*-
# creater by: barnett

import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from openapi.views.base import ListAPIView
from openapi.serializer.gateway_serializer import HTTPGatewayRuleSerializer, PostHTTPGatewayRuleSerializer
from console.services.app_config import domain_service
from console.services.group_service import group_service
logger = logging.getLogger("default")


class ListAppGatewayHTTPRuleView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取应用http访问策略列表",
        manual_parameters=[],
        responses={200: HTTPGatewayRuleSerializer(many=True)},
        tags=['openapi-gateway'],
    )
    def get(self, req, app_id, *args, **kwargs):
        app = group_service.get_app_by_id(app_id)
        if not app:
            return Response({"msg": "app is not exist"}, status=status.HTTP_404_NOT_FOUND)
        rules = domain_service.get_http_rules_by_app_id(app_id)
        re = HTTPGatewayRuleSerializer(rules, many=True)
        return Response(re.data, status=status.HTTP_200_OK)


class AddGatewayHTTPRuleView(ListAPIView):
    @swagger_auto_schema(
        operation_description="创建HTTP网关策略",
        request_body=PostHTTPGatewayRuleSerializer(),
        responses={200: HTTPGatewayRuleSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, *args, **kwargs):
        serializer = PostHTTPGatewayRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(None, status=status.HTTP_201_CREATED)
