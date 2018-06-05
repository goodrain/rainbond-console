# -*- coding:utf8 -*-
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.models import RainbondCenterPlugin
from console.services.market_plugin_service import market_plugin_service
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message, error_message

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
        try:
            plugin_name = request.GET.get('plugin_name')
            page = request.GET.get('page', 1)
            limit = request.GET.get('limit', 10)
            is_download = request.GET.get('is_download')
            source = request.GET.get('source')

            total, plugins = market_plugin_service.get_paged_plugins(
                plugin_name, is_download, source, page, limit
            )
            result = general_message(
                200, "success", "查询成功", list=plugins, total=total, next_page=int(page) + 1
            )
            return Response(data=result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class SyncMarketPluginsView(RegionTenantHeaderView):
    def post(self, request, *args, **kwargs):
        """
        同步云市插件分享
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            market_plugin_service.sync_market_plugins(self.tenant.tenant_id)
            result = general_message(200, "success", "同步成功")
            return Response(result, 200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, 500)


class SyncMarketPluginTemplatesView(RegionTenantHeaderView):
    def post(self, request, *args, **kwargs):
        """
        同步插件模板
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            plugin_data = request.data
            data = []
            for p in plugin_data:
                data.append({
                    'plugin_key': p["plugin_key"],
                    'version': p['version']
                })

            market_plugin_service.sync_market_plugin_templates(self.tenant.tenant_id, data)
            result = general_message(200, "success", "同步成功")
            return Response(result, 200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, 500)


class InstallMarketPlugin(RegionTenantHeaderView):
    def post(self, requset, team_name, *args, **kwargs):
        """
        安装插件
        :param requset:
        :param team_name:
        :param args:
        :param kwargs:
        :return:
        """
        plugin_id = requset.data.get('plugin_id')

        try:
            plugin = RainbondCenterPlugin.objects.get(ID=plugin_id)
            status, msg = market_plugin_service.install_plugin(
                self.user.user_id, self.team, self.response_region, plugin
            )
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
        try:
            plugin_name = request.GET.get('plugin_name')
            page = request.GET.get('page', 1)
            limit = request.GET.get('limit', 10)
            scope = request.GET.get('scope')

            total, plugins = market_plugin_service.get_paged_plugins(
                plugin_name, is_complete=True, scope=scope, tenant=self.tenant,
                page=page, limit=limit
            )
            result = general_message(
                200, "success", "查询成功", list=plugins, total=total, next_page=int(page) + 1
            )
            return Response(data=result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)
