# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
from rest_framework.response import Response

from console.views.base import RegionTenantHeaderView
from www.models import TenantServiceInfo, Tenants
from www.utils.return_message import general_message
import logging
from console.exception.main import BusinessException

logger = logging.getLogger('default')


class AppBaseView(RegionTenantHeaderView):
    def __init__(self, *args, **kwargs):
        super(AppBaseView, self).__init__(*args, **kwargs)
        self.service = None

    def initial(self, request, *args, **kwargs):
        super(AppBaseView, self).initial(request, *args, **kwargs)
        service_alias = kwargs.get("serviceAlias", None)
        if not service_alias:
            raise ImportError("You url not contains args - serviceAlias -")
        services = TenantServiceInfo.objects.filter(service_alias=service_alias,tenant_id=self.tenant.tenant_id)
        if services:
            self.service = services[0]
            if self.service.tenant_id != self.tenant.tenant_id:
                team_info = Tenants.objects.filter(tenant_id=self.service.tenant_id)
                if team_info:
                    raise BusinessException(response=Response(general_message(10403, "service team is not current team", "应用{0}不属于当前团队".format(service_alias), {"service_team_name": team_info[0].tenant_name}), status=404))
                else:
                    raise BusinessException(response=Response(general_message(10403, "service team is not current team", "应用{0}不属于当前团队且其团队不存在".format(service_alias), {"service_team_name": ""}), status=404))
            # 请求应用资源的数据中心与用户当前页面数据中心不一致
            if self.service.service_region != self.response_region:
                raise BusinessException(Response(general_message(10404, "service region is not current region", "应用{0}不属于当前数据中心".format(service_alias), {"service_region": self.service.service_region}), status=404))
        else:
            raise BusinessException(Response(general_message(404, "service not found", "应用{0}不存在".format(service_alias)), status=404))
        self.initial_header_info(request)

    def initial_header_info(self, request):
        pass
