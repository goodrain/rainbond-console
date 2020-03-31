# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework.views import APIView
from openapi.auth.authentication import OpenAPIAuthentication
from openapi.auth.authentication import EnterOpenAPIAuthentication
from openapi.auth.permissions import OpenAPIPermissions
from rest_framework import generics


class BaseOpenAPIView(APIView):
    authentication_classes = [OpenAPIAuthentication]
    permission_classes = [OpenAPIPermissions]


class ListAPIView(generics.ListAPIView):
    authentication_classes = [OpenAPIAuthentication]
    permission_classes = [OpenAPIPermissions]


class EnterpriseCenterAPIView(APIView):
    authentication_classes = [EnterOpenAPIAuthentication]
