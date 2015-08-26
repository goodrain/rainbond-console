# -*- coding: utf8 -*-
from rest_framework.response import Response
from api.views.base import APIView
from www.models import TenantServiceInfo
from www.service_http import RegionServiceApi

import logging
logger = logging.getLogger('default')


class SelectedServiceView(APIView):
    '''
    对单个服务的动作
    '''
    allowed_methods = ('PUT', )

    def put(self, request, serviceId, format=None):
        """
        更新服务属性
        ---
        parameters:
            - name: attribute_list
              description: 属性列表
              required: true
              type: string
              paramType: body
        """
        try:
            data = request.data
            TenantServiceInfo.objects.filter(service_id=serviceId).update(**data)
            region = RegionServiceApi()
            region.update_service(serviceId, data)
            return Response({"ok": True}, status=201)
        except TenantServiceInfo.DoesNotExist, e:
            logger.error(e)
            return Response({"ok": False, "reason": e}, status=404)
