# -*- coding: utf8 -*-
from rest_framework.response import Response
from api.views.base import APIView
from www.models import TenantServiceInfo

import logging
logger = logging.getLogger('default')

class TenantServiceStatics(object):

    allowed_methods = ('POST',)
        
    def post(self, request, format=None):
        """
        统计租户服务
        ---
        parameters:
            - name: data
              description: 数据列表
              required: true
              type: string
              paramType: body
        """
        try:
            data = request.data
            return Response({"ok": True}, status=200)
        except TenantServiceInfo.DoesNotExist, e:
            logger.error(e)
            return Response({"ok": False, "reason": e}, status=500)
