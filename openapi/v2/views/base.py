# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework.views import APIView
from openapi.v2.auth.authentication import OpenAPIManageAuthentication
from openapi.v2.auth.permissions import OpenAPIPermissions
from rest_framework import generics


class BaseOpenAPIView(APIView):
    authentication_classes = [OpenAPIManageAuthentication]
    permission_classes = [OpenAPIPermissions]

    def __init__(self):
        super(BaseOpenAPIView, self).__init__()

    def initial(self, request, *args, **kwargs):
        super(BaseOpenAPIView, self).initial(request, *args, **kwargs)


class ListAPIView(generics.ListAPIView):
    authentication_classes = [OpenAPIManageAuthentication]
    permission_classes = [OpenAPIPermissions]
