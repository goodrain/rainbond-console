# -*- coding: utf8 -*-
"""
  Created on 2018/4/24.
"""

import logging
from typing import Any

from console.views.base import RegionTenantHeaderView
from console.utils.cache_decorators import never_cache
from rest_framework.request import Request
from rest_framework.response import Response
# -*- coding: utf8 -*-
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class RegionProtocolView(RegionTenantHeaderView):
    @never_cache
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
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
            # NOTE: region API result may be None; indexing it is a latent risk (backlog).
            protocols = protocols_info["list"]  # type: ignore[index]
            p_list = []
            for p in protocols:
                p_list.append(p["protocol_child"])
            result = general_message(200, "success", "查询成功", list=list(set(p_list)))
        except Exception as e:
            logger.exception(e)
            result = general_message(200, "", "查询成功", list=["http", "stream"])
        return Response(result, status=result["code"])
