# coding: utf-8
from types import SimpleNamespace
from unittest import TestCase, mock


class FakeRegionQuery(list):
    def order_by(self, field):
        return FakeRegionQuery(sorted(self, key=lambda region: region.ID))


# capability_id: console.login-security.configuration
class LoginSecurityConfigServiceTests(TestCase):
    def service(self, regions=None, now=lambda: 1000, enterprise_resolver=None):
        region_repository = mock.Mock()
        region_repository.get_usable_regions.return_value = FakeRegionQuery(regions or [])
        region_client = mock.Mock()
        from console.services.login_security_service import LoginSecurityConfigService
        return (
            LoginSecurityConfigService(
                region_repository=region_repository,
                region_client=region_client,
                now=now,
                cache_ttl=5,
                enterprise_resolver=enterprise_resolver,
            ),
            region_repository,
            region_client,
        )

    # capability_id: console.login-security.plugin-configuration
    def test_missing_enterprise_or_plugin_defaults_both_features_off(self):
        service, region_repository, region_client = self.service()

        config = service.get_config("")

        self.assertFalse(config["plugin_installed"])
        self.assertFalse(config["login_captcha_enabled"])
        self.assertFalse(config["login_limit_enabled"])
        region_repository.get_usable_regions.assert_not_called()
        region_client.request_plugin_backend.assert_not_called()

    # capability_id: console.login-security.plugin-configuration
    def test_login_identifier_resolves_enterprise_when_platform_env_is_missing(self):
        region = SimpleNamespace(ID=1, region_name="rainbond")
        service, region_repository, region_client = self.service(
            [region], enterprise_resolver=lambda identifier: "eid-from-user")
        region_client.cluster_plugin_exists.return_value = False

        service.get_config(login_identifier="admin")

        region_repository.get_usable_regions.assert_called_once_with("eid-from-user")

    # capability_id: console.login-security.plugin-configuration
    def test_login_enterprise_lookup_failure_defaults_features_off(self):
        service, region_repository, _ = self.service(
            enterprise_resolver=mock.Mock(side_effect=RuntimeError("database unavailable")))

        with mock.patch.dict("os.environ", {}, clear=True):
            config = service.get_config(login_identifier="admin")

        self.assertFalse(config["plugin_installed"])
        self.assertFalse(config["login_captcha_enabled"])
        self.assertFalse(config["login_limit_enabled"])
        region_repository.get_usable_regions.assert_not_called()

    # capability_id: console.login-security.plugin-configuration
    def test_checks_regions_in_id_order_and_reads_first_installed_plugin(self):
        regions = [
            SimpleNamespace(ID=20, region_name="region-b"),
            SimpleNamespace(ID=10, region_name="region-a"),
        ]
        service, _, region_client = self.service(regions)
        region_client.cluster_plugin_exists.side_effect = [False, True]
        region_client.request_plugin_backend.return_value = (
            200,
            {
                "code": 200,
                "data": {
                    "login_captcha_enabled": True,
                    "login_limit_enabled": True,
                },
            },
        )

        config = service.get_config("eid-1")

        self.assertTrue(config["plugin_installed"])
        self.assertTrue(config["login_captcha_enabled"])
        self.assertTrue(config["login_limit_enabled"])
        self.assertEqual(config["source_region"], "region-b")
        self.assertEqual(
            region_client.cluster_plugin_exists.call_args_list,
            [
                mock.call("eid-1", "region-a", "rainbond-security-center"),
                mock.call("eid-1", "region-b", "rainbond-security-center"),
            ],
        )
        region_client.request_plugin_backend.assert_called_once_with(
            "eid-1",
            "region-b",
            "rainbond-security-center",
            "GET",
            "/api/v1/config",
            timeout=3,
        )

    # capability_id: console.login-security.plugin-configuration
    def test_unreadable_plugin_config_keeps_enterprise_features_off(self):
        region = SimpleNamespace(ID=1, region_name="rainbond")
        service, _, region_client = self.service([region])
        region_client.cluster_plugin_exists.return_value = True
        region_client.request_plugin_backend.side_effect = RuntimeError("plugin unavailable")

        config = service.get_config("eid-1")

        self.assertTrue(config["plugin_installed"])
        self.assertFalse(config["login_captcha_enabled"])
        self.assertFalse(config["login_limit_enabled"])
        self.assertEqual(config["source_region"], "")

    # capability_id: console.login-security.plugin-configuration
    def test_region_lookup_failure_keeps_enterprise_features_off(self):
        service, region_repository, _ = self.service()
        region_repository.get_usable_regions.side_effect = RuntimeError("database unavailable")

        config = service.get_config("eid-1")

        self.assertFalse(config["plugin_installed"])
        self.assertFalse(config["login_captcha_enabled"])
        self.assertFalse(config["login_limit_enabled"])

    # capability_id: console.login-security.plugin-configuration
    def test_malformed_plugin_envelope_keeps_enterprise_features_off(self):
        region = SimpleNamespace(ID=1, region_name="rainbond")
        service, _, region_client = self.service([region])
        region_client.cluster_plugin_exists.return_value = True
        region_client.request_plugin_backend.return_value = (200, {"code": "invalid", "data": {}})

        config = service.get_config("eid-1")

        self.assertTrue(config["plugin_installed"])
        self.assertFalse(config["login_captcha_enabled"])
        self.assertFalse(config["login_limit_enabled"])

    # capability_id: console.login-security.plugin-configuration
    def test_result_is_cached_for_five_seconds(self):
        clock = [1000]
        region = SimpleNamespace(ID=1, region_name="rainbond")
        service, _, region_client = self.service([region], now=lambda: clock[0])
        region_client.cluster_plugin_exists.return_value = False

        service.get_config("eid-1")
        service.get_config("eid-1")
        clock[0] = 1006
        service.get_config("eid-1")

        self.assertEqual(region_client.cluster_plugin_exists.call_count, 2)

    # capability_id: console.login-security.plugin-configuration
    def test_effective_plugin_config_overrides_legacy_console_captcha_flag(self):
        from console.services.login_security_service import apply_login_security_to_platform_config

        data = {"captcha_code": {"enable": True, "value": "legacy"}}
        effective = {
            "plugin_installed": False,
            "login_captcha_enabled": False,
            "login_limit_enabled": False,
        }

        result = apply_login_security_to_platform_config(data, effective)

        self.assertFalse(result["captcha_code"]["enable"])
        self.assertIsNone(result["captcha_code"]["value"])
        self.assertEqual(result["login_security"], effective)
