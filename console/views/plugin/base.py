# -*- coding: utf8 -*-
"""
  Created on 18/3/4.
"""
from console.exception.main import BusinessException
from console.views.base import RegionTenantHeaderView
from www.models import TenantPlugin, Tenants, PluginBuildVersion
from rest_framework.response import Response

from www.utils.return_message import general_message


class PluginBaseView(RegionTenantHeaderView):
    def __init__(self, *args, **kwargs):
        super(PluginBaseView, self).__init__(*args, **kwargs)
        self.plugin = None
        self.plugin_version = None

    def initial(self, request, *args, **kwargs):
        super(PluginBaseView, self).initial(request, *args, **kwargs)
        plugin_id = kwargs.get("plugin_id", None)
        if not plugin_id:
            raise ImportError("You url not contains args - plugin_id -")
        tenant_plugin = TenantPlugin.objects.filter(plugin_id=plugin_id)
        if tenant_plugin:
            self.plugin = tenant_plugin[0]
            if self.plugin.tenant_id != self.tenant.tenant_id:
                team_info = Tenants.objects.filter(tenant_id=self.plugin.tenant_id)
                if team_info:
                    raise BusinessException(
                        response=Response(general_message(10403, "plugin team is not current team", "插件不属于当前团队"),
                                          status=404))
                else:
                    raise BusinessException(
                        response=Response(general_message(10403, "current team is not exist", "团队不存在"), status=404))
            # 请求应用资源的数据中心与用户当前页面数据中心不一致
            if self.plugin.region != self.response_region:
                raise BusinessException(
                    Response(general_message(10404, "plugin region is not current region", "插件不属于当前数据中心"), status=404))
        else:
            raise BusinessException(Response(general_message(404, "plugin not found", "插件不存在"), status=404))
        self.initial_header_info(request)

        build_version = kwargs.get("build_version", None)
        if build_version:
            plugin_build_version = PluginBuildVersion.objects.filter(plugin_id=plugin_id, build_version=build_version)
            if plugin_build_version:
                self.plugin_version = plugin_build_version[0]
            else:
                raise BusinessException(
                    response=Response(general_message(10403,
                                                      "plugin id {0}, build version {1} is not exist".format(plugin_id,
                                                                                                             build_version),
                                                      "当前版本插件不存在"),
                                      status=404))

    def initial_header_info(self, request):
        pass
