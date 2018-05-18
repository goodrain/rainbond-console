# -*- coding: utf8 -*-
"""
  Created on 2018/4/24.
"""

# -*- coding: utf8 -*-
from www.apiclient.regionapi import RegionInvokeApi

import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.views.base import RegionTenantHeaderView
from www.decorator import perm_required
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class RegionProtocolView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取数据中心支持的协议
        ---
        parameters:
            - name: tenantName
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: region_name
              description: 数据中心名称
              required: false
              type: string
              paramType: query
        """
        try:
            region_name = request.GET.get("region_name", self.response_region)
            protocols_info = region_api.get_protocols(region_name, self.team.tenant_name)
            protocols = protocols_info["list"]
            pList = []
            for p in protocols:
                pList.append(p["protocol_child"])
            result = general_message(200, "success", "查询成功", list=pList)
        except Exception as e:
            logger.exception(e)
            result = general_message(200, e.message, "查询成功", list=["http", "stream"])
        return Response(result, status=result["code"])
