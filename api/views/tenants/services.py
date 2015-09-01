# -*- coding: utf8 -*-
from rest_framework.response import Response
from api.views.base import APIView
from www.models import TenantServiceStatics

import logging
logger = logging.getLogger('default')

class TenantServiceStaticsView(APIView):
    '''
    计费基础数据统计
    '''
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
        datas = request.data
        for data in datas:
            try:
                tenant_id = data["tenant_id"]
                service_id = data["service_id"]
                node_num = data["node_num"]
                node_memory = data["node_memory"]
                time_stamp = data["time_stamp"]
                storage_disk = data["storage_disk"]
                net_in = data["net_in"]
                net_out = data["net_out"]
                ts = TenantServiceStatics(tenant_id=tenant_id, service_id=service_id, node_num=node_num, node_memory=node_memory, time_stamp=time_stamp, storage_disk=storage_disk, net_in=net_in, net_out=net_out)
                ts.save()
            except Exception as e:
                logger.error(e)
        return Response({"ok": True}, status=200)
