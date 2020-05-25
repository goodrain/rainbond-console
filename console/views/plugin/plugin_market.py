# -*- coding:utf8 -*-
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from console.models.main import RainbondCenterPlugin
from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.plugin import plugin_repo
from console.services.market_plugin_service import market_plugin_service
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message

logger = logging.getLogger('default')


class MarketPluginsView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取云市插件分页列表
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        plugin_name = request.GET.get('plugin_name')
        page = request.GET.get('page', 1)
        limit = request.GET.get('limit', 10)
        # is_download = request.GET.get('is_download')

        # market_plugin_service.sync_market_plugins(self.tenant.tenant_id)
        total, plugins = market_plugin_service.get_paged_plugins(
            plugin_name,
            page=page,
            limit=limit,
            order_by='is_complete',
            source='market',
            scope='goodrain',
            tenant=self.tenant)
        result = general_message(200, "success", "查询成功", list=plugins, total=total, next_page=int(page) + 1)
        return Response(data=result, status=200)


class SyncMarketPluginsView(RegionTenantHeaderView):
    def post(self, request, *args, **kwargs):
        """
        同步云市插件分享
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if not self.user.is_sys_admin:
            if not self.is_enterprise_admin:
                return Response(general_message(403, "current user is not enterprise admin", "非企业管理员无法进行此操作"), status=403)

        ent = enterprise_repo.get_enterprise_by_enterprise_id(self.tenant.enterprise_id)
        if ent and not ent.is_active:
            result = general_message(10407, "failed", "用户未跟云市认证")
            return Response(result, 500)

        page = request.GET.get('page', 1)
        limit = request.GET.get('limit', 10)
        plugin_name = request.GET.get('plugin_name', '')

        plugins, total = market_plugin_service.sync_market_plugins(self.tenant, self.user, page, limit, plugin_name)
        result = general_message(200, "success", "同步成功", list=plugins, total=total)
        return Response(result, 200)


class SyncMarketPluginTemplatesView(RegionTenantHeaderView):
    def post(self, request, *args, **kwargs):
        """
        同步插件模板
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if not self.user.is_sys_admin:
            if not self.is_enterprise_admin:
                return Response(general_message(403, "current user is not enterprise admin", "非企业管理员无法进行此操作"), status=403)

        ent = enterprise_repo.get_enterprise_by_enterprise_id(self.tenant.enterprise_id)
        if ent and not ent.is_active:
            result = general_message(10407, "failed", "用户未跟云市认证")
            return Response(result, 500)

        plugin_data = request.data
        data = {'plugin_key': plugin_data["plugin_key"], 'version': plugin_data['version']}

        market_plugin_service.sync_market_plugin_templates(self.user, self.tenant, data)
        result = general_message(200, "success", "同步成功")
        return Response(result, 200)


class InstallMarketPlugin(RegionTenantHeaderView):
    def post(self, requset, *args, **kwargs):
        """
        安装插件
        :param requset:
        :param args:
        :param kwargs:
        :return:
        """
        plugin_id = requset.data.get('plugin_id')

        try:
            plugin = RainbondCenterPlugin.objects.get(ID=plugin_id)
            status, msg = market_plugin_service.install_plugin(self.user, self.team, self.response_region, plugin)
            if status != 200:
                return Response(general_message(500, 'install plugin failed', msg), 500)
            return Response(general_message(200, '', ''), 200)
        except RainbondCenterPlugin.DoesNotExist:
            return Response(general_message(404, "plugin not exist", "插件不存在"), status=404)


class InternalMarketPluginsView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        内部插件市场接口
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        plugin_name = request.GET.get('plugin_name')
        page = request.GET.get('page', 1)
        limit = request.GET.get('limit', 10)
        scope = request.GET.get('scope')

        total, plugins = market_plugin_service.get_paged_plugins(
            plugin_name, is_complete=True, scope=scope, tenant=self.tenant, page=page, limit=limit)
        result = general_message(200, "success", "查询成功", list=plugins, total=total, next_page=int(page) + 1)
        return Response(data=result, status=200)


class InstallableInteralPluginsView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        获取可安装的内部插件列表接口
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        plugin_name = request.GET.get('plugin_name')
        page = request.GET.get('page', 1)
        limit = request.GET.get('limit', 10)

        total, plugins = market_plugin_service.get_paged_plugins(
            plugin_name, is_complete=True, tenant=self.tenant, page=page, limit=limit)

        installed = plugin_repo.get_tenant_plugins(self.tenant.tenant_id, self.response_region). \
            filter(origin__in=['local_market', 'market'])

        for p in plugins:
            if installed.filter(origin_share_id=p["plugin_key"]).exists():
                # if installed.filter(plugin_alias=p["plugin_name"]).exists():
                p["is_installed"] = True
            else:
                p["is_installed"] = False

        result = general_message(200, "success", "查询成功", list=plugins, total=total, next_page=int(page) + 1)
        return Response(data=result, status=200)


class UninstallPluginTemplateView(RegionTenantHeaderView):
    def post(self, requset, *args, **kwargs):
        """
        卸载插件模板
        :param requset:
        :param args:
        :param kwargs:
        :return:
        """
        if not self.user.is_sys_admin:
            return Response(general_message(403, "you are not admin", "此操作需平台管理员才能操作"), status=403)

        plugin_id = requset.data.get('plugin_id')

        try:
            plugin = RainbondCenterPlugin.objects.get(ID=plugin_id)
            plugin.delete()
            return Response(general_message(200, '', ''), 200)
        except RainbondCenterPlugin.DoesNotExist:
            return Response(general_message(404, "plugin not exist", "插件不存在"), status=404)
