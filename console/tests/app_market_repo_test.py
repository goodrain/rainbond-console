from unittest import TestCase, mock

from console.exception.main import ServiceHandleException
from console.repositories.app import (
    PLATFORM_PLUGIN_DEFAULT_URL,
    PLATFORM_PLUGIN_MARKET_DOMAIN,
    PLATFORM_PLUGIN_MARKET_NAME,
    app_market_repo,
)


class AppMarketRepoPlatformPluginMarketTests(TestCase):
    """get_app_market_by_name 需要把 __platform_plugin__ 合成名解析成"默认市场 + domain=enterprise"
    的内存 AppMarket 实例, 否则升级管理列表 / get_property_changes / 升级执行等
    "按 market_name 查市场"的链路, 都会因为 app_market 表里没有这条记录而拿到 404, UI 表现为
    "暂无数据". 这里覆盖正常 / 没有默认市场两种路径.
    """

    def test_synthetic_platform_plugin_name_returns_default_market_with_enterprise_domain(self):
        default = mock.Mock()
        default.url = "https://hub.example.com"
        default.access_key = "default-ak"

        queryset = mock.Mock()
        queryset.first.return_value = default

        with mock.patch("console.repositories.app.AppMarket.objects.filter", return_value=queryset) as filter_call:
            market = app_market_repo.get_app_market_by_name("eid", PLATFORM_PLUGIN_MARKET_NAME, raise_exception=True)

        filter_call.assert_called_once_with(enterprise_id="eid", is_personal=False)
        self.assertEqual(PLATFORM_PLUGIN_MARKET_NAME, market.name)
        self.assertEqual("https://hub.example.com", market.url)
        self.assertEqual(PLATFORM_PLUGIN_MARKET_DOMAIN, market.domain)
        self.assertEqual("default-ak", market.access_key)
        self.assertEqual("eid", market.enterprise_id)

    def test_synthetic_platform_plugin_name_falls_back_to_default_url_when_default_market_has_no_url(self):
        default = mock.Mock()
        default.url = ""
        default.access_key = "default-ak"

        queryset = mock.Mock()
        queryset.first.return_value = default

        with mock.patch("console.repositories.app.AppMarket.objects.filter", return_value=queryset):
            market = app_market_repo.get_app_market_by_name("eid", PLATFORM_PLUGIN_MARKET_NAME)

        self.assertEqual(PLATFORM_PLUGIN_DEFAULT_URL, market.url)

    def test_synthetic_platform_plugin_name_returns_none_without_default_market_when_not_raising(self):
        queryset = mock.Mock()
        queryset.first.return_value = None

        with mock.patch("console.repositories.app.AppMarket.objects.filter", return_value=queryset):
            market = app_market_repo.get_app_market_by_name("eid", PLATFORM_PLUGIN_MARKET_NAME, raise_exception=False)

        self.assertIsNone(market)

    def test_synthetic_platform_plugin_name_raises_when_default_market_missing_and_raise_requested(self):
        queryset = mock.Mock()
        queryset.first.return_value = None

        with mock.patch("console.repositories.app.AppMarket.objects.filter", return_value=queryset):
            with self.assertRaises(ServiceHandleException) as ctx:
                app_market_repo.get_app_market_by_name("eid", PLATFORM_PLUGIN_MARKET_NAME, raise_exception=True)

        self.assertEqual(404, ctx.exception.status_code)
