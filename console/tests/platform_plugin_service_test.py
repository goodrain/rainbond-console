import collections
import importlib
import json
import os
import sys
from contextlib import nullcontext
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.platform_plugin_service import platform_plugin_service  # noqa: E402


class PlatformPluginServiceTests(TestCase):

    def setUp(self):
        platform_plugin_service.clear_market_plugin_cache()
        platform_plugin_service.clear_region_arches_cache()

    def tearDown(self):
        platform_plugin_service.clear_market_plugin_cache()
        platform_plugin_service.clear_region_arches_cache()

    def test_plugin_debug_summary_includes_arch_hint_and_keys(self):
        plugin_info = {
            "plugin_id": "rainbond-vm",
            "plugin_name": "虚拟机",
            "app_level": "free",
            "latest_version": "3.0.0",
            "architectures": ["amd64", "arm64"],
            "plugin_views": ["Platform"],
        }

        summary = platform_plugin_service._plugin_debug_summary(plugin_info)

        self.assertEqual(["amd64", "arm64"], summary["arch_hint"])
        self.assertEqual(
            ["app_level", "architectures", "latest_version", "plugin_id", "plugin_name", "plugin_views"],
            summary["keys"],
        )

    def test_select_market_plugin_prefers_free_variant(self):
        market_plugins = [
            {"plugin_id": "rainbond-recovery", "appKeyID": "enterprise-app-key", "app_level": "enterprise"},
            {"plugin_id": "rainbond-recovery", "appKeyID": "free-app-key", "app_level": "free"},
        ]

        selected = platform_plugin_service._select_market_plugin(market_plugins, "rainbond-recovery", {})

        self.assertEqual("free-app-key", selected["appKeyID"])

    def test_select_market_plugin_matches_arm64_license_mapping_app_key(self):
        market_plugins = [
            {"plugin_id": "rainbond-enterprise-pipeline", "appKeyID": "amd-app-key", "app_level": "enterprise"},
            {"plugin_id": "rainbond-enterprise-pipeline", "appKeyID": "arm-app-key", "app_level": "enterprise"},
        ]

        selected = platform_plugin_service._select_market_plugin(
            market_plugins,
            "rainbond-enterprise-pipeline",
            {"rainbond-enterprise-pipeline-ARM64": "arm-app-key"},
        )

        self.assertEqual("arm-app-key", selected["appKeyID"])

    def test_get_market_platform_plugins_uses_enterprise_market_domain(self):
        default_market = mock.Mock()
        default_market.url = "https://hub.grapps.cn"
        default_market.access_key = "default-ak"

        with mock.patch.object(platform_plugin_service, "_get_default_market", return_value=default_market), \
                mock.patch("console.services.platform_plugin_service.app_store.get_platform_plugins",
                           return_value={"plugins": []}) as get_platform_plugins:
            market, plugins = platform_plugin_service._get_market_platform_plugins("eid")

        self.assertEqual("enterprise", market.domain)
        self.assertEqual("default-ak", market.access_key)
        get_platform_plugins.assert_called_once()

    def test_get_market_platform_plugins_cached_reuses_entry_until_ttl_expires(self):
        default_market = mock.Mock()
        default_market.url = "https://hub.grapps.cn"
        default_market.access_key = "default-ak"

        platform_plugin_service.clear_market_plugin_cache()
        try:
            with mock.patch.object(platform_plugin_service, "_get_default_market", return_value=default_market), \
                    mock.patch("console.services.platform_plugin_service.app_store.get_platform_plugins",
                               return_value={"plugins": [{"plugin_id": "rainbond-vm"}]}) as get_platform_plugins:
                _, first_plugins = platform_plugin_service._get_market_platform_plugins_cached("eid", now=100.0)
                _, second_plugins = platform_plugin_service._get_market_platform_plugins_cached("eid", now=120.0)
                _, third_plugins = platform_plugin_service._get_market_platform_plugins_cached("eid", now=161.0)

            self.assertEqual([{"plugin_id": "rainbond-vm"}], first_plugins)
            self.assertEqual([{"plugin_id": "rainbond-vm"}], second_plugins)
            self.assertEqual([{"plugin_id": "rainbond-vm"}], third_plugins)
            self.assertEqual(2, get_platform_plugins.call_count)
        finally:
            platform_plugin_service.clear_market_plugin_cache()

    def test_list_platform_plugins_without_valid_license_returns_all_market_plugins(self):
        market_plugins = [
            {"plugin_id": "rainbond-free", "plugin_name": "免费插件", "app_level": "free", "latest_version": "1.0.0"},
            {"plugin_id": "rainbond-enterprise", "plugin_name": "商业插件", "app_level": "enterprise", "latest_version": "1.0.0"},
        ]

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"amd64", "arm64"}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins_cached",
                                  return_value=(mock.Mock(), market_plugins)):
            plugins = platform_plugin_service.list_platform_plugins("eid", "region")

        self.assertEqual(2, len(plugins))
        self.assertEqual({"rainbond-free", "rainbond-enterprise"}, {item["plugin_id"] for item in plugins})

    def test_list_platform_plugins_with_valid_license_filters_unauthorized_enterprise_plugins(self):
        market_plugins = [
            {"plugin_id": "rainbond-free", "plugin_name": "免费插件", "app_level": "free", "latest_version": "1.0.0"},
            {"plugin_id": "rainbond-enterprise-a", "plugin_name": "商业插件A", "app_level": "enterprise", "latest_version": "1.0.0"},
            {"plugin_id": "rainbond-enterprise-b", "plugin_name": "商业插件B", "app_level": "enterprise", "latest_version": "1.0.0"},
        ]
        license_bean = {
            "valid": True,
            "plugin_mapping": {
                "rainbond-enterprise-a": "app-key-a",
            }
        }

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"amd64", "arm64"}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins_cached",
                                  return_value=(mock.Mock(), market_plugins)):
            plugins = platform_plugin_service.list_platform_plugins("eid", "region")

        self.assertEqual(2, len(plugins))
        self.assertEqual({"rainbond-free", "rainbond-enterprise-a"}, {item["plugin_id"] for item in plugins})

    def test_list_platform_plugins_with_arm64_license_mapping_returns_authorized_enterprise_plugin(self):
        market_plugins = [
            {"plugin_id": "rainbond-enterprise-a", "plugin_name": "商业插件A", "app_level": "enterprise",
             "latest_version": "1.0.0", "appKeyID": "arm-app-key"},
        ]
        license_bean = {
            "valid": True,
            "plugin_mapping": {
                "rainbond-enterprise-a-ARM64": "arm-app-key",
            }
        }

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"amd64", "arm64"}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins_cached",
                                  return_value=(mock.Mock(), market_plugins)):
            plugins = platform_plugin_service.list_platform_plugins("eid", "region")

        self.assertEqual(1, len(plugins))
        self.assertEqual("rainbond-enterprise-a", plugins[0]["plugin_id"])

    def test_install_platform_plugin_rejects_unauthorized_enterprise_plugin(self):
        market_plugins = [
            {"plugin_id": "rainbond-enterprise-a", "plugin_name": "商业插件A", "app_level": "enterprise"}
        ]
        license_bean = {
            "valid": True,
            "plugin_mapping": {},
            "access_key": "license-ak",
        }

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"amd64", "arm64"}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)):
            with self.assertRaises(ServiceHandleException) as context:
                platform_plugin_service.install_platform_plugin("eid", "region", "rainbond-enterprise-a", mock.Mock())

        self.assertEqual("该插件未授权", context.exception.msg_show)

    def test_bootstrap_agent_kubernetes_credentials_syncs_without_returning_secret(self):
        user = mock.Mock(user_id=1, nick_name="admin")
        kubeconfig = "apiVersion: v1\nclusters: []\nusers: []"

        with mock.patch("console.services.platform_plugin_service.region_api.bootstrap_agent_kubeconfig",
                        return_value=(None, {"bean": {
                            "region_name": "rainbond",
                            "credential_profile": "ops",
                            "service_account": "rainbond-agent",
                            "context_id": "rainbond:ops",
                            "kubeconfig": kubeconfig,
                        }})) as bootstrap_kubeconfig, \
                mock.patch("console.services.platform_plugin_service.region_api.bootstrap_agent_plugin_credential",
                           return_value=(None, {"ok": True})) as bootstrap_plugin:
            result = platform_plugin_service.bootstrap_agent_kubernetes_credentials(
                "eid", "rainbond", user)

        self.assertEqual({"status": "synced", "region_name": "rainbond"}, result)
        bootstrap_kubeconfig.assert_called_once_with("eid", "rainbond", {
            "region_name": "rainbond",
            "context_id": "rainbond",
            "credential_profile": "ops",
            "service_account": "rainbond-agent",
        })
        bootstrap_plugin.assert_called_once()
        plugin_payload = bootstrap_plugin.call_args[0][2]
        self.assertEqual(kubeconfig, plugin_payload["kubeconfig"])
        self.assertEqual("ops", plugin_payload["credential_profile"])
        self.assertEqual("rainbond-agent", plugin_payload["service_account"])
        self.assertEqual("rainbond:ops", plugin_payload["context_id"])
        self.assertNotIn("kubeconfig", result)

    def test_bootstrap_agent_service_mcp_credentials_injects_api_envs_without_returning_secret(self):
        tenant = mock.Mock(tenant_id="team-1", tenant_name="rbd-plugins")
        app = mock.Mock(ID=23)
        service = mock.Mock(service_alias="rainbond-agent-api", service_cname="api")
        component = mock.Mock(component=service)
        user = mock.Mock(nick_name="admin")
        user.get_username.return_value = "admin"
        existing_cookie_env = mock.Mock(ID=7)

        def get_env_by_attr_name(_tenant, _service, attr_name):
            if attr_name == "COPILOT_SERVICE_COOKIE":
                return existing_cookie_env
            return None

        with mock.patch("console.services.platform_plugin_service.jwt_issuer.issue_agent_service_jwt",
                        return_value="jwt-token") as issue_jwt, \
                mock.patch("console.services.platform_plugin_service.env_var_service.get_env_by_attr_name",
                           side_effect=get_env_by_attr_name), \
                mock.patch("console.services.platform_plugin_service.env_var_service.add_service_env_var",
                           return_value=(200, "success", mock.Mock())) as add_env, \
                mock.patch("console.services.platform_plugin_service.env_var_service.update_env_by_env_id",
                           return_value=(200, "success", existing_cookie_env)) as update_env:
            result = platform_plugin_service.bootstrap_agent_service_mcp_credentials(
                tenant, app, "rainbond", [component], user)

        self.assertEqual({"status": "synced", "service_alias": "rainbond-agent-api"}, result)
        issue_jwt.assert_called_once_with(user)
        add_env.assert_called_once()
        add_kwargs = add_env.call_args.kwargs
        self.assertEqual("COPILOT_SERVICE_AUTHORIZATION", add_kwargs["attr_name"])
        self.assertEqual("GRJWT jwt-token", add_kwargs["attr_value"])
        self.assertEqual("inner", add_kwargs["scope"])
        update_env.assert_called_once_with(
            tenant, service, "7", "COPILOT_SERVICE_COOKIE", "token=jwt-token", "admin")
        self.assertNotIn("jwt-token", str(result))

    def test_bootstrap_agent_service_mcp_credentials_defers_when_api_component_missing(self):
        tenant = mock.Mock(tenant_id="team-1", tenant_name="rbd-plugins")
        app = mock.Mock(ID="not-a-real-db-id")

        result = platform_plugin_service.bootstrap_agent_service_mcp_credentials(
            tenant, app, "rainbond", [], mock.Mock())

        self.assertEqual("deferred", result["status"])
        self.assertIn("未找到 AI 助手 API 组件", result["message"])

    def test_ensure_agent_credential_encryption_key_generates_once_and_restarts(self):
        tenant = mock.Mock(tenant_id="team-1", enterprise_id="eid")
        app = mock.Mock(ID=23)
        service = mock.Mock(ID=7, service_alias="rainbond-agent-api", create_status="complete")
        user = mock.Mock(nick_name="admin")
        locked_service = mock.Mock(ID=7, service_alias="rainbond-agent-api", create_status="complete")

        with mock.patch.object(platform_plugin_service, "_resolve_installed_agent_context",
                               return_value=(tenant, app, service)), \
                mock.patch("console.services.platform_plugin_service.TenantServiceInfo.objects.select_for_update") \
                as select_for_update, \
                mock.patch("console.services.platform_plugin_service.env_var_service.get_env_by_attr_name",
                           return_value=None), \
                mock.patch("console.services.platform_plugin_service.env_var_service.add_service_env_var",
                           return_value=(200, "success", mock.Mock())) as add_env, \
                mock.patch("console.services.platform_plugin_service.app_manage_service.restart",
                           return_value=(200, "success")) as restart, \
                mock.patch("console.services.platform_plugin_service.secrets.token_hex",
                           return_value="a" * 64), \
                mock.patch("django.db.transaction.atomic", return_value=nullcontext()):
            select_for_update.return_value.get.return_value = locked_service
            result = platform_plugin_service.ensure_agent_credential_encryption_key(
                "eid", "rainbond", user, {"status": "missing"})

        self.assertEqual({
            "status": "generated",
            "generated": True,
            "restart_requested": True,
            "service_alias": "rainbond-agent-api",
        }, result)
        self.assertEqual("COPILOT_CREDENTIAL_ENCRYPTION_KEY", add_env.call_args.kwargs["attr_name"])
        self.assertEqual("inner", add_env.call_args.kwargs["scope"])
        self.assertFalse(add_env.call_args.kwargs["is_change"])
        restart.assert_called_once_with(tenant, locked_service, user, None)
        self.assertNotIn("a" * 64, str(result))

    def test_ensure_agent_credential_encryption_key_preserves_legacy_key(self):
        tenant = mock.Mock(tenant_id="team-1", enterprise_id="eid")
        app = mock.Mock(ID=23)
        service = mock.Mock(ID=7, service_alias="rainbond-agent-api")
        legacy_env = mock.Mock(attr_value="legacy-key")

        def get_env(_tenant, _service, attr_name):
            if attr_name == "COPILOT_KUBE_CREDENTIAL_KEY":
                return legacy_env
            return None

        with mock.patch.object(platform_plugin_service, "_resolve_installed_agent_context",
                               return_value=(tenant, app, service)), \
                mock.patch("console.services.platform_plugin_service.TenantServiceInfo.objects.select_for_update") \
                as select_for_update, \
                mock.patch("console.services.platform_plugin_service.env_var_service.get_env_by_attr_name",
                           side_effect=get_env), \
                mock.patch("console.services.platform_plugin_service.env_var_service.add_service_env_var") as add_env, \
                mock.patch("console.services.platform_plugin_service.app_manage_service.restart") as restart, \
                mock.patch("django.db.transaction.atomic", return_value=nullcontext()):
            select_for_update.return_value.get.return_value = service
            result = platform_plugin_service.ensure_agent_credential_encryption_key(
                "eid", "rainbond", mock.Mock(), {"status": "legacy_ready"})

        self.assertEqual("already_configured", result["status"])
        self.assertEqual("legacy", result["key_source"])
        self.assertFalse(result["generated"])
        add_env.assert_not_called()
        restart.assert_not_called()

    def test_bootstrap_agent_credential_encryption_key_injects_and_restarts(self):
        tenant = mock.Mock(tenant_id="team-1")
        app = mock.Mock(ID=23)
        service = mock.Mock(service_alias="rainbond-agent-api")
        component = mock.Mock(component=service)
        user = mock.Mock(nick_name="admin")

        with mock.patch.object(platform_plugin_service, "_resolve_agent_api_component", return_value=service), \
                mock.patch.object(platform_plugin_service, "_read_agent_encryption_env", return_value=(None, None)), \
                mock.patch.object(platform_plugin_service, "_upsert_agent_service_envs") as upsert, \
                mock.patch("console.services.platform_plugin_service.app_manage_service.restart",
                           return_value=(200, "success")) as restart:
            result = platform_plugin_service.bootstrap_agent_credential_encryption_key(
                tenant, app, "rainbond", [component], user)

        self.assertEqual("synced", result["status"])
        self.assertTrue(result["restart_requested"])
        upsert.assert_called_once()
        restart.assert_called_once_with(tenant, service, user, None)

    def test_install_agent_platform_plugin_bootstraps_service_mcp_credentials(self):
        market_plugins = [{
            "plugin_id": "rainbond-agent",
            "plugin_name": "AI助手",
            "app_level": "free",
            "appKeyID": "agent-app-key",
            "latest_version": "1.0.0",
        }]
        license_bean = {
            "valid": True,
            "plugin_mapping": {},
            "access_key": "license-ak",
        }
        tenant = mock.Mock()
        tenant.tenant_id = "team-1"
        tenant.tenant_name = "rbd-plugins"
        region_info = mock.Mock()
        region_info.region_name = "rainbond"
        app = mock.Mock()
        app.ID = 23
        component = mock.Mock()

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"amd64", "arm64"}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_team", return_value=tenant), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_app", return_value=app), \
                mock.patch("console.services.platform_plugin_service.region_repo.get_enterprise_region_by_region_name",
                           return_value=region_info), \
                mock.patch("console.services.platform_plugin_service.app_market_service.cloud_app_model_to_db_model",
                           return_value=(
                               mock.Mock(app_id="app-id", app_name="AI助手"),
                               mock.Mock(app_template="{}", update_time="", arch="amd64"),
                           )), \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_tenant_service_group",
                           return_value=mock.Mock()), \
                mock.patch("console.services.platform_plugin_service.AppUpgrade") as app_upgrade_cls, \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_rbdplugin_if_needed"), \
                mock.patch.object(platform_plugin_service, "bootstrap_agent_service_mcp_credentials",
                                  return_value={"status": "synced"}) as bootstrap_mcp, \
                mock.patch.object(platform_plugin_service, "bootstrap_agent_credential_encryption_key",
                                  return_value={"status": "synced"}) as bootstrap_encryption, \
                mock.patch.object(platform_plugin_service, "bootstrap_agent_kubernetes_credentials",
                                  return_value={"status": "synced"}) as bootstrap_kube:
            app_upgrade_cls.return_value.install.return_value = []
            app_upgrade_cls.return_value.new_app.components.return_value = [component]
            result = platform_plugin_service.install_platform_plugin("eid", "rainbond", "rainbond-agent", mock.Mock())

        bootstrap_encryption.assert_called_once_with(tenant, app, "rainbond", [component], mock.ANY)
        bootstrap_mcp.assert_called_once_with(tenant, app, "rainbond", [component], mock.ANY)
        bootstrap_kube.assert_called_once()
        self.assertEqual({"status": "synced"}, result["service_mcp_credential_bootstrap"])
        self.assertEqual({"status": "synced"}, result["credential_encryption_bootstrap"])
        self.assertEqual({"status": "synced"}, result["kubernetes_credential_bootstrap"])

    def test_install_platform_plugin_prefers_free_variant_even_if_enterprise_variant_exists(self):
        market_plugins = [
            {
                "plugin_id": "rainbond-recovery",
                "plugin_name": "灾备恢复",
                "app_level": "enterprise",
                "appKeyID": "enterprise-app-key"
            },
            {
                "plugin_id": "rainbond-recovery",
                "plugin_name": "灾备恢复",
                "app_level": "free",
                "appKeyID": "free-app-key",
                "latest_version": "1.0.0"
            },
        ]
        license_bean = {
            "valid": True,
            "plugin_mapping": {},
            "access_key": "license-ak",
        }
        tenant = mock.Mock()
        tenant.tenant_id = "team-1"
        tenant.tenant_name = "rbd-plugins"
        region = mock.Mock()
        region.region_name = "rainbond"
        region_info = mock.Mock()
        region_info.region_name = "rainbond"
        app = mock.Mock()
        app.ID = 1

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"amd64", "arm64"}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_team", return_value=tenant), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_app", return_value=app), \
                mock.patch("console.services.platform_plugin_service.region_repo.get_enterprise_region_by_region_name",
                           return_value=region_info), \
                mock.patch("console.services.platform_plugin_service.app_market_service.cloud_app_model_to_db_model",
                           return_value=(
                               mock.Mock(app_id="app-id", app_name="灾备恢复"),
                               mock.Mock(app_template="{}", update_time="", arch="amd64"),
                           )) as cloud_model, \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_tenant_service_group",
                           return_value=mock.Mock()), \
                mock.patch("console.services.platform_plugin_service.AppUpgrade") as app_upgrade_cls, \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_rbdplugin_if_needed"), \
                mock.patch.object(platform_plugin_service, "bootstrap_agent_kubernetes_credentials") as bootstrap_agent:
            app_upgrade_cls.return_value.install.return_value = []
            platform_plugin_service.install_platform_plugin("eid", "rainbond", "rainbond-recovery", mock.Mock())

        cloud_model.assert_called_once()
        bootstrap_agent.assert_not_called()
        call_args = cloud_model.call_args[0]
        self.assertEqual("free-app-key", call_args[1])

    def test_install_platform_plugin_accepts_arm64_license_mapping(self):
        market_plugins = [
            {"plugin_id": "rainbond-enterprise-pipeline", "plugin_name": "流水线", "app_level": "enterprise",
             "appKeyID": "arm-app-key", "latest_version": "3.0.0"},
        ]
        license_bean = {
            "valid": True,
            "plugin_mapping": {
                "rainbond-enterprise-pipeline-ARM64": "arm-app-key",
            },
            "access_key": "license-ak",
        }
        tenant = mock.Mock()
        tenant.tenant_id = "team-1"
        tenant.tenant_name = "rbd-plugins"
        region_info = mock.Mock()
        region_info.region_name = "rainbond"
        app = mock.Mock()
        app.ID = 1

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"amd64", "arm64"}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_team", return_value=tenant), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_app", return_value=app), \
                mock.patch("console.services.platform_plugin_service.region_repo.get_enterprise_region_by_region_name",
                           return_value=region_info), \
                mock.patch("console.services.platform_plugin_service.app_market_service.cloud_app_model_to_db_model",
                           return_value=(
                               mock.Mock(app_id="app-id", app_name="流水线"),
                               mock.Mock(app_template="{}", update_time="", arch="arm64"),
                           )) as cloud_model, \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_tenant_service_group",
                           return_value=mock.Mock()), \
                mock.patch("console.services.platform_plugin_service.AppUpgrade") as app_upgrade_cls, \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_rbdplugin_if_needed"), \
                mock.patch.object(platform_plugin_service, "bootstrap_agent_kubernetes_credentials") as bootstrap_agent:
            app_upgrade_cls.return_value.install.return_value = []
            platform_plugin_service.install_platform_plugin("eid", "rainbond", "rainbond-enterprise-pipeline", mock.Mock())

        cloud_model.assert_called_once()
        bootstrap_agent.assert_not_called()
        call_args = cloud_model.call_args[0]
        self.assertEqual("arm-app-key", call_args[1])

    def test_install_platform_plugin_rejects_missing_region_before_creating_team_or_app(self):
        market_plugins = [{
            "plugin_id": "rainbond-agent",
            "plugin_name": "AI助手",
            "app_level": "free",
            "appKeyID": "agent-app-key",
            "latest_version": "1.0.0",
            "arch": "amd64",
        }]

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_get_region_arches", return_value={"amd64"}), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_team") as ensure_team, \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_app") as ensure_app, \
                mock.patch("console.services.platform_plugin_service.region_repo."
                           "get_enterprise_region_by_region_name", return_value=None):
            with self.assertRaises(ServiceHandleException) as context:
                platform_plugin_service.install_platform_plugin(
                    "eid", "missing-region", "rainbond-agent", mock.Mock())

        self.assertEqual("集群不存在", context.exception.msg_show)
        ensure_team.assert_not_called()
        ensure_app.assert_not_called()

    def test_install_platform_plugin_blocks_before_component_mutation_when_preflight_fails(self):
        preflight = {
            "status": "blocked",
            "should_block": True,
            "summary": "集群可用内存不足",
            "checks": [{
                "name": "resources",
                "status": "blocked",
                "required": {"memory_mb": 1024},
                "available": {"memory_mb": 512},
            }],
        }
        tenant = mock.Mock(tenant_id="team-1", tenant_name="rbd-plugins")
        region = mock.Mock(region_name="rainbond")
        app = mock.Mock(ID=1)
        market_app = mock.Mock(app_id="app-id", app_name="AI助手")
        app_version = mock.Mock(
            app_template=json.dumps({"apps": [{"memory": 1024}]}),
            update_time="2026-08-13T00:00:00Z",
            arch="arm64",
        )
        preflight_service = mock.Mock()
        preflight_service.run.return_value = preflight

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins", return_value=(mock.Mock(), [{
                    "plugin_id": "rainbond-agent",
                    "plugin_name": "AI助手",
                    "app_level": "free",
                    "appKeyID": "agent-app-key",
                    "latest_version": "1.0.0",
                    "arch": "arm64",
                }])), \
                mock.patch.object(platform_plugin_service, "_get_region_arches", return_value={"arm64"}), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_team", return_value=tenant), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_app", return_value=app) as ensure_app, \
                mock.patch("console.services.platform_plugin_service.region_repo.get_enterprise_region_by_region_name",
                           return_value=region), \
                mock.patch("console.services.platform_plugin_service.app_market_service.cloud_app_model_to_db_model",
                           return_value=(market_app, app_version)), \
                mock.patch("console.services.platform_plugin_service.market_install_preflight_service",
                           preflight_service, create=True), \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_tenant_service_group") \
                as create_component_group, \
                mock.patch("console.services.platform_plugin_service.AppUpgrade") as app_upgrade_cls, \
                mock.patch("console.services.platform_plugin_service.enterprise_first_deploy_service."
                           "safe_begin_deploy_tracking") as begin_tracking:
            with self.assertRaises(ServiceHandleException) as context:
                platform_plugin_service.install_platform_plugin(
                    "eid", "rainbond", "rainbond-agent", mock.Mock())

        expected_template = {
            "apps": [{"memory": 1024}],
            "update_time": "2026-08-13T00:00:00Z",
            "arch": "arm64",
        }
        preflight_service.run.assert_called_once_with(tenant, region, expected_template, check_images=False)
        self.assertEqual(412, context.exception.status_code)
        self.assertEqual(10412, context.exception.error_code)
        self.assertEqual("platform plugin preflight blocked", context.exception.msg)
        self.assertEqual("集群可用内存不足", context.exception.msg_show)
        self.assertIs(preflight, context.exception.bean)
        ensure_app.assert_not_called()
        create_component_group.assert_not_called()
        app_upgrade_cls.assert_not_called()
        begin_tracking.assert_not_called()

    def test_install_platform_plugin_continues_once_when_preflight_only_warns(self):
        preflight = {
            "status": "warning",
            "should_block": False,
            "summary": "资源接口暂不可用",
            "checks": [{"name": "resources", "status": "warning"}],
        }
        tenant = mock.Mock(tenant_id="team-1", tenant_name="rbd-plugins")
        region = mock.Mock(region_name="rainbond")
        app = mock.Mock(ID=1)
        market_app = mock.Mock(app_id="app-id", app_name="AI助手")
        app_template = {"apps": [], "update_time": "update-time", "arch": "amd64"}
        app_version = mock.Mock(app_template=json.dumps({"apps": []}), update_time="update-time", arch="amd64")
        component_group = mock.Mock()
        preflight_service = mock.Mock()
        preflight_service.run.return_value = preflight
        app_upgrade = mock.Mock()
        app_upgrade.install.return_value = []
        app_upgrade.new_app.components.return_value = []

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins", return_value=(mock.Mock(), [{
                    "plugin_id": "rainbond-agent",
                    "plugin_name": "AI助手",
                    "app_level": "free",
                    "appKeyID": "agent-app-key",
                    "latest_version": "1.0.0",
                    "arch": "amd64",
                }])), \
                mock.patch.object(platform_plugin_service, "_get_region_arches", return_value={"amd64"}), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_team", return_value=tenant), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_app", return_value=app) as ensure_app, \
                mock.patch("console.services.platform_plugin_service.region_repo.get_enterprise_region_by_region_name",
                           return_value=region), \
                mock.patch("console.services.platform_plugin_service.app_market_service.cloud_app_model_to_db_model",
                           return_value=(market_app, app_version)), \
                mock.patch("console.services.platform_plugin_service.market_install_preflight_service",
                           preflight_service, create=True), \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_tenant_service_group",
                           return_value=component_group) as create_component_group, \
                mock.patch("console.services.platform_plugin_service.AppUpgrade", return_value=app_upgrade) \
                as app_upgrade_cls, \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_rbdplugin_if_needed"), \
                mock.patch("console.services.platform_plugin_service.market_app_service._extract_event_ids",
                           return_value=[]):
            platform_plugin_service.install_platform_plugin(
                "eid", "rainbond", "rainbond-agent", mock.Mock())

        preflight_service.run.assert_called_once_with(tenant, region, app_template, check_images=False)
        ensure_app.assert_called_once_with(
            tenant, "rainbond", "AI助手", "eid", "rainbond-agent")
        create_component_group.assert_called_once()
        app_upgrade_cls.assert_called_once()
        app_upgrade.install.assert_called_once_with()


class PlatformPluginInstallViewTests(TestCase):

    def test_post_preserves_structured_service_exception_response(self):
        preflight = {
            "status": "blocked",
            "should_block": True,
            "summary": "集群资源不足",
            "checks": [{"name": "resources", "status": "blocked"}],
        }
        error = ServiceHandleException(
            msg="platform plugin preflight blocked",
            msg_show="集群资源不足",
            status_code=412,
            error_code=10412,
            bean=preflight,
        )
        base_module = ModuleType("console.views.base")
        base_module.JWTAuthApiView = object
        exception_module = ModuleType("console.exception.main")
        exception_module.ServiceHandleException = ServiceHandleException
        module_name = "console.views.platform_plugin"
        missing = object()
        previous_module = sys.modules.get(module_name, missing)
        try:
            with mock.patch.dict(sys.modules, {
                    "console.views.base": base_module,
                    "console.exception.main": exception_module,
            }):
                sys.modules.pop(module_name, None)
                platform_plugin_view = importlib.import_module(module_name)
                self.assertIs(platform_plugin_view, sys.modules[module_name])

                view = platform_plugin_view.PlatformPluginInstallView()
                view.user = mock.Mock()
                with mock.patch.object(
                        platform_plugin_view.platform_plugin_service,
                        "install_platform_plugin",
                        side_effect=error):
                    response = view.post(mock.Mock(), "eid", "rainbond", "rainbond-agent")
        finally:
            sys.modules.pop(module_name, None)
            if previous_module is not missing:
                sys.modules[module_name] = previous_module

        if previous_module is missing:
            self.assertNotIn(module_name, sys.modules)
        else:
            self.assertIs(previous_module, sys.modules[module_name])

        self.assertEqual(412, response.status_code)
        self.assertEqual(10412, response.data["code"])
        self.assertEqual("platform plugin preflight blocked", response.data["msg"])
        self.assertEqual("集群资源不足", response.data["msg_show"])
        self.assertIs(preflight, response.data["data"]["bean"])

    # capability_id: console.platform-plugin.vm-runtime-status-guard
    def test_ensure_vm_plugin_running_accepts_running_status(self):
        with mock.patch.object(platform_plugin_service, "_get_installed_plugins", return_value={
                "rainbond-vm": {
                    "name": "rainbond-vm",
                    "status": "RUNNING",
                }
        }):
            platform_plugin_service.ensure_vm_plugin_running("eid", "region")

    # capability_id: console.platform-plugin.vm-runtime-status-guard
    def test_ensure_vm_plugin_running_rejects_non_running_status(self):
        with mock.patch.object(platform_plugin_service, "_get_installed_plugins", return_value={
                "rainbond-vm": {
                    "name": "rainbond-vm",
                    "status": "FAILED",
                }
        }):
            with self.assertRaises(ServiceHandleException) as context:
                platform_plugin_service.ensure_vm_plugin_running("eid", "region")

        self.assertEqual(412, context.exception.status_code)
        self.assertEqual("虚拟机功能未正常运行，不允许执行虚拟机相关操作", context.exception.msg_show)

    # ---------- arch field parsing ----------

    def test_get_plugin_arch_reads_explicit_field(self):
        self.assertEqual("arm64", platform_plugin_service._get_plugin_arch({"arch": "arm64"}))
        self.assertEqual("amd64", platform_plugin_service._get_plugin_arch({"arch": "amd64"}))

    def test_get_plugin_arch_normalizes_case_and_whitespace(self):
        self.assertEqual("arm64", platform_plugin_service._get_plugin_arch({"arch": "ARM64"}))
        self.assertEqual("amd64", platform_plugin_service._get_plugin_arch({"arch": " AMD64 "}))

    def test_get_plugin_arch_falls_back_to_amd64_when_missing_or_unknown(self):
        self.assertEqual("amd64", platform_plugin_service._get_plugin_arch({}))
        self.assertEqual("amd64", platform_plugin_service._get_plugin_arch({"arch": ""}))
        self.assertEqual("amd64", platform_plugin_service._get_plugin_arch({"arch": "riscv"}))
        self.assertEqual("amd64", platform_plugin_service._get_plugin_arch(None))

    # ---------- region arch retrieval with cache ----------

    def test_get_region_arches_returns_set_from_region_api(self):
        platform_plugin_service.clear_region_arches_cache()
        with mock.patch("console.services.platform_plugin_service.region_api.get_cluster_nodes_arch",
                        return_value=(None, {"list": ["arm64", "arm64"]})):
            arches = platform_plugin_service._get_region_arches("rainbond")
        self.assertEqual({"arm64"}, arches)

    def test_get_region_arches_falls_back_to_full_set_on_failure(self):
        platform_plugin_service.clear_region_arches_cache()
        with mock.patch("console.services.platform_plugin_service.region_api.get_cluster_nodes_arch",
                        side_effect=Exception("network down")):
            arches = platform_plugin_service._get_region_arches("rainbond")
        self.assertEqual({"amd64", "arm64"}, arches)

    def test_get_region_arches_caches_within_ttl(self):
        platform_plugin_service.clear_region_arches_cache()
        # TTL 默认 60s, 第一次 now=100 写缓存 expires_at=160; 后两次均在 expires_at 之前应命中
        with mock.patch("console.services.platform_plugin_service.region_api.get_cluster_nodes_arch",
                        return_value=(None, {"list": ["amd64"]})) as get_arch:
            platform_plugin_service._get_region_arches("rainbond", now=100.0)
            platform_plugin_service._get_region_arches("rainbond", now=130.0)
            platform_plugin_service._get_region_arches("rainbond", now=159.0)
        self.assertEqual(1, get_arch.call_count)

    def test_get_region_arches_refetches_after_ttl_expires(self):
        platform_plugin_service.clear_region_arches_cache()
        with mock.patch("console.services.platform_plugin_service.region_api.get_cluster_nodes_arch",
                        return_value=(None, {"list": ["amd64"]})) as get_arch:
            platform_plugin_service._get_region_arches("rainbond", now=100.0)
            platform_plugin_service._get_region_arches("rainbond", now=200.0)
        self.assertEqual(2, get_arch.call_count)

    # ---------- arch-based filtering in list_platform_plugins ----------

    def _market_plugins_arm_and_amd(self):
        return [
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "amd-ak", "latest_version": "1.0.0", "arch": "amd64"},
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "arm-ak", "latest_version": "1.0.0", "arch": "arm64"},
        ]

    def _list_with_region_arches(self, market_plugins, region_arches,
                                 installed_plugins=None, license_bean=None):
        installed_plugins = installed_plugins or {}
        license_bean = license_bean or {}
        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins",
                                  return_value=installed_plugins), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins_cached",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value=region_arches):
            return platform_plugin_service.list_platform_plugins("eid", "rainbond")

    def test_list_platform_plugins_on_arm_cluster_shows_arm_sku_only(self):
        plugins = self._list_with_region_arches(self._market_plugins_arm_and_amd(), {"arm64"})
        self.assertEqual(1, len(plugins))
        self.assertEqual("arm64", plugins[0]["installed_arch"] or plugins[0].get("selected_arch"))
        self.assertEqual({"amd64", "arm64"}, set(plugins[0]["available_arches"]))

    def test_list_platform_plugins_on_amd_cluster_shows_amd_sku_only(self):
        plugins = self._list_with_region_arches(self._market_plugins_arm_and_amd(), {"amd64"})
        self.assertEqual(1, len(plugins))
        self.assertEqual("amd64", plugins[0].get("selected_arch"))

    def test_list_platform_plugins_on_mixed_cluster_prefers_amd_sku(self):
        plugins = self._list_with_region_arches(
            self._market_plugins_arm_and_amd(), {"amd64", "arm64"})
        self.assertEqual(1, len(plugins))
        self.assertEqual("amd64", plugins[0].get("selected_arch"))

    def test_list_platform_plugins_drops_plugin_when_no_arch_match(self):
        market_plugins = [
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "amd-ak", "latest_version": "1.0.0", "arch": "amd64"},
        ]
        plugins = self._list_with_region_arches(market_plugins, {"arm64"})
        self.assertEqual(0, len(plugins))

    def test_list_platform_plugins_fallback_full_arch_set_when_region_arches_empty(self):
        # fallback 全集场景下不丢失任何 plugin
        plugins = self._list_with_region_arches(
            self._market_plugins_arm_and_amd(), {"amd64", "arm64"})
        self.assertEqual(1, len(plugins))

    # ---------- installed SKU anchoring latest_version ----------

    def test_list_platform_plugins_installed_local_import_does_not_report_upgrade(self):
        # 已装的 plugin 来自本地 import (service_source.group_key 不在市场 candidates 中),
        # 跟市场上同 plugin_id 的 SKU 是两份资产; 跨源时不应该假阳性报"可升级",
        # 升级页 (按 group_key 拉本地版本) 才是真实的可升级来源
        market_plugins = [
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "market-amd-ak", "latest_version": "1.0.0", "arch": "amd64"},
        ]
        installed_plugins = {
            "rainbond-agent": {
                "name": "rainbond-agent",
                "status": "RUNNING",
                "team_name": "rbd-plugins",
                "region_app_id": "region-app-local",
                "plugin_type": "JSInject",
            }
        }

        component_group = mock.Mock(group_version="0.1", group_key="5da180e862344ae7945245cb66ca856d")
        component_groups_qs = mock.Mock()
        component_groups_qs.last.return_value = component_group
        component_groups_qs.__iter__ = lambda self: iter([component_group])

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins",
                                  return_value=installed_plugins), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map",
                                  return_value={"region-app-local": 99}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins_cached",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"amd64"}), \
                mock.patch("console.services.platform_plugin_service.tenant_service_group_repo.get_group_by_app_id",
                           return_value=component_groups_qs):
            plugins = platform_plugin_service.list_platform_plugins("eid", "rainbond")

        self.assertEqual(1, len(plugins))
        info = plugins[0]
        self.assertTrue(info["installed"])
        self.assertEqual("0.1", info["installed_version"])
        # latest_version 锁到 installed_version, 避免跟市场 SKU 的 1.0.0 跨源比对
        self.assertEqual("0.1", info["latest_version"])
        self.assertFalse(info["upgradeable"])
        self.assertFalse(info["can_upgrade"])
        self.assertIsNone(info["installed_arch"])  # 反查不到 SKU, installed_arch 也是 None

    def test_list_platform_plugins_installed_arm_anchors_latest_version_against_arm_sku(self):
        # ARM SKU 已装 v1.0.0；AMD SKU 在市场上 v2.0.0；ARM 集群应该锁 ARM v1.0.0
        market_plugins = [
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "amd-ak", "latest_version": "2.0.0", "arch": "amd64"},
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "arm-ak", "latest_version": "1.0.0", "arch": "arm64"},
        ]
        installed_plugins = {
            "rainbond-agent": {
                "name": "rainbond-agent",
                "status": "RUNNING",
                "team_name": "rbd-plugins",
                "region_app_id": "region-app-1",
                "plugin_type": "frontend",
            }
        }

        component_group = mock.Mock(group_version="1.0.0", group_key="arm-ak")
        component_groups_qs = mock.Mock()
        component_groups_qs.last.return_value = component_group
        component_groups_qs.__iter__ = lambda self: iter([component_group])

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value={}), \
                mock.patch.object(platform_plugin_service, "_get_installed_plugins",
                                  return_value=installed_plugins), \
                mock.patch.object(platform_plugin_service, "_get_region_app_id_map",
                                  return_value={"region-app-1": 42}), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins_cached",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"arm64"}), \
                mock.patch("console.services.platform_plugin_service.tenant_service_group_repo.get_group_by_app_id",
                           return_value=component_groups_qs):
            plugins = platform_plugin_service.list_platform_plugins("eid", "rainbond")

        self.assertEqual(1, len(plugins))
        info = plugins[0]
        self.assertTrue(info["installed"])
        self.assertEqual("1.0.0", info["latest_version"])
        self.assertEqual("1.0.0", info["installed_version"])
        self.assertFalse(info["upgradeable"])
        self.assertEqual("arm64", info["installed_arch"])

    # ---------- install_platform_plugin arch selection ----------

    def _install_with_arch(self, market_plugins, region_arches, plugin_id):
        license_bean = {"valid": False, "plugin_mapping": {}, "access_key": "license-ak"}
        tenant = mock.Mock(tenant_id="team-1", tenant_name="rbd-plugins")
        region_info = mock.Mock(region_name="rainbond")
        app = mock.Mock(ID=1)

        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value=region_arches), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_team", return_value=tenant), \
                mock.patch.object(platform_plugin_service, "_ensure_plugin_app", return_value=app), \
                mock.patch("console.services.platform_plugin_service.region_repo.get_enterprise_region_by_region_name",
                           return_value=region_info), \
                mock.patch("console.services.platform_plugin_service.app_market_service.cloud_app_model_to_db_model",
                           return_value=(
                               mock.Mock(app_id="app-id", app_name="AI助手"),
                               mock.Mock(app_template="{}", update_time="",
                                         arch=next(iter(region_arches))),
                           )) as cloud_model, \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_tenant_service_group",
                           return_value=mock.Mock()), \
                mock.patch("console.services.platform_plugin_service.AppUpgrade") as app_upgrade_cls, \
                mock.patch("console.services.platform_plugin_service.market_app_service._create_rbdplugin_if_needed"), \
                mock.patch.object(platform_plugin_service, "bootstrap_agent_credential_encryption_key",
                                  return_value={"status": "synced"}), \
                mock.patch.object(platform_plugin_service, "bootstrap_agent_kubernetes_credentials",
                                  return_value={"status": "synced", "region_name": "rainbond"}) as bootstrap_agent:
            app_upgrade_cls.return_value.install.return_value = []
            result = platform_plugin_service.install_platform_plugin("eid", "rainbond", plugin_id, mock.Mock())
            return cloud_model, bootstrap_agent, result

    def test_install_platform_plugin_on_arm_cluster_picks_arm_sku(self):
        market_plugins = [
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "amd-ak", "latest_version": "1.0.0", "arch": "amd64"},
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "arm-ak", "latest_version": "1.0.0", "arch": "arm64"},
        ]
        cloud_model, bootstrap_agent, result = self._install_with_arch(
            market_plugins, {"arm64"}, "rainbond-agent")
        cloud_model.assert_called_once()
        self.assertEqual("arm-ak", cloud_model.call_args[0][1])
        bootstrap_agent.assert_called_once()
        self.assertEqual({"status": "synced", "region_name": "rainbond"},
                         result["kubernetes_credential_bootstrap"])

    def test_install_platform_plugin_raises_when_arch_mismatch(self):
        market_plugins = [
            {"plugin_id": "rainbond-agent", "plugin_name": "AI助手", "app_level": "free",
             "appKeyID": "amd-ak", "latest_version": "1.0.0", "arch": "amd64"},
        ]
        license_bean = {"valid": False, "plugin_mapping": {}, "access_key": "license-ak"}
        with mock.patch.object(platform_plugin_service, "_get_license_bean", return_value=license_bean), \
                mock.patch.object(platform_plugin_service, "_get_market_platform_plugins",
                                  return_value=(mock.Mock(), market_plugins)), \
                mock.patch.object(platform_plugin_service, "_get_region_arches",
                                  return_value={"arm64"}):
            with self.assertRaises(ServiceHandleException) as ctx:
                platform_plugin_service.install_platform_plugin(
                    "eid", "rainbond", "rainbond-agent", mock.Mock())
        self.assertIn("arm64", ctx.exception.msg_show)
