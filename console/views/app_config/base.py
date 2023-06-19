# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from rest_framework.response import Response

from console.exception.main import BusinessException, AbortRequest
from console.services.group_service import group_service
from console.views.base import RegionTenantHeaderView
from www.models.main import Tenants, TenantServiceInfo
from console.models.main import ComponentGraph
from www.utils.return_message import general_message
from console.views.base import CloudEnterpriseCenterView

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

        services = TenantServiceInfo.objects.filter(service_alias=service_alias, tenant_id=self.tenant.tenant_id)
        if services:
            self.service = services[0]
            # update app
            if request.method != 'GET':
                group_service.set_app_update_time_by_service(self.service)
            if self.service.tenant_id != self.tenant.tenant_id:
                team_info = Tenants.objects.filter(tenant_id=self.service.tenant_id)
                if team_info:
                    raise BusinessException(
                        response=Response(
                            general_message(10403, "service team is not current team", "组件{0}不属于当前团队".format(service_alias),
                                            {"service_team_name": team_info[0].tenant_name}),
                            status=404))
                else:
                    raise BusinessException(
                        response=Response(
                            general_message(10403, "service team is not current team", "组件{0}不属于当前团队且其团队不存在".format(
                                service_alias), {"service_team_name": ""}),
                            status=404))
            # 请求应用资源的数据中心与用户当前页面数据中心不一致
            if self.service.service_region != self.response_region:
                self.response_region = self.service.service_region
        else:
            raise BusinessException(
                Response(general_message(404, "service not found", "组件{0}不存在".format(service_alias)), status=404))


class AppBaseCloudEnterpriseCenterView(AppBaseView, CloudEnterpriseCenterView):
    def __init__(self, *args, **kwargs):
        super(AppBaseCloudEnterpriseCenterView, self).__init__(*args, **kwargs)
        self.oauth_instance = None
        self.oauth = None
        self.oauth_user = None

    def initial(self, request, *args, **kwargs):
        AppBaseView.initial(self, request, *args, **kwargs)
        CloudEnterpriseCenterView.initial(self, request, *args, **kwargs)


class ComponentGraphBaseView(AppBaseView):
    def __init__(self, *args, **kwargs):
        super(ComponentGraphBaseView, self).__init__(*args, **kwargs)
        self.graph = None

    def initial(self, request, *args, **kwargs):
        super(ComponentGraphBaseView, self).initial(request, *args, **kwargs)
        try:
            graph_id = kwargs.get("graph_id", None)
            graph = ComponentGraph.objects.filter(component_id=self.service.service_id, graph_id=graph_id).first()
        except ComponentGraph.DoesNotExist:
            raise AbortRequest("graph not found", "监控图不存在", 404, 404)
        self.graph = graph
