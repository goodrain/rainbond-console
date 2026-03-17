# -*- coding: utf-8 -*-
from rest_framework.response import Response

from console.views.base import EnterpriseAdminView, JWTAuthApiView
from goodrain_web.tools import general_message
from www.models.main import TenantEnterprise


class PlatformSettingsView(JWTAuthApiView):
    def get(self, request, eid, *args, **kwargs):
        try:
            enterprise = TenantEnterprise.objects.get(enterprise_id=eid)
        except TenantEnterprise.DoesNotExist:
            return Response(general_message(404, "not found", "企业不存在"), status=404)
        data = {
            "enable_team_resource_view": enterprise.enable_team_resource_view,
        }
        return Response(general_message(200, "success", "获取成功", bean=data))


class PlatformSettingsUpdateView(EnterpriseAdminView):
    def put(self, request, eid, *args, **kwargs):
        try:
            enterprise = TenantEnterprise.objects.get(enterprise_id=eid)
        except TenantEnterprise.DoesNotExist:
            return Response(general_message(404, "not found", "企业不存在"), status=404)
        enable = request.data.get("enable_team_resource_view")
        if enable is None:
            return Response(general_message(400, "bad request", "缺少 enable_team_resource_view 参数"), status=400)
        enterprise.enable_team_resource_view = bool(enable)
        enterprise.save(update_fields=["enable_team_resource_view"])
        return Response(general_message(200, "success", "更新成功"))
