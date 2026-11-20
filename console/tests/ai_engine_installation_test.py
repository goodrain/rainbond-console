# -*- coding: utf-8 -*-
# capability_id: console.ai-engine.platform-credential-installation
import copy
import importlib
import os
import sys
from contextlib import nullcontext
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from console.exception.main import ServiceHandleException  # noqa: E402


class AIEngineInstallationTests(TestCase):
    def setUp(self):
        self.module = importlib.import_module("console.services.ai_engine_installation")
        self.expected = "a" * 64
        patchers = {
            "bootstrap":
            mock.patch.object(self.module.region_api,
                              "bootstrap_ai_engine_platform_token",
                              return_value=self.expected,
                              create=True),
            "set_env":
            mock.patch.object(self.module.region_api, "set_ai_engine_platform_env", create=True),
            "owner_is_admin":
            mock.patch.object(self.module.enterprise_user_perm_repo, "is_admin", return_value=True),
            "legacy_add":
            mock.patch.object(self.module.env_var_service,
                              "add_service_env_var",
                              side_effect=AssertionError("credential write must verify region TLS")),
            "legacy_update":
            mock.patch.object(self.module.region_api,
                              "update_service_env",
                              side_effect=AssertionError("credential write must verify region TLS")),
        }
        for name, patcher in patchers.items():
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.tenant = SimpleNamespace(tenant_id="team-a",
                                      tenant_name="team-a",
                                      enterprise_id="enterprise-a",
                                      namespace="rbd-plugins",
                                      creater=42)
        self.region = SimpleNamespace(region_name="region-a", enterprise_id="enterprise-a", token="Token fixture-region-token")
        self.backend = SimpleNamespace(tenant_id="team-a",
                                       service_region="region-a",
                                       service_id="backend-id",
                                       service_alias="backend",
                                       create_status="complete")

    def test_credential_comes_only_from_authenticated_region_bootstrap(self):
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=None), \
                mock.patch.object(self.module.env_var_repo, "add_service_env") as add:
            self.module.configure_installation(self.tenant, self.region, self.backend)
        self.bootstrap.assert_called_once_with("enterprise-a", "region-a")
        self.assertEqual(add.call_args.kwargs["attr_value"], self.expected)
        self.assertNotEqual(add.call_args.kwargs["attr_value"], self.region.token)
        self.legacy_add.assert_not_called()
        self.legacy_update.assert_not_called()

    def test_malformed_region_bootstrap_credential_fails_without_echoing_it(self):
        for value in (None, "", "fixture-secret", "a" * 63, "A" * 64, {"token": "a" * 64}):
            self.bootstrap.return_value = value
            with self.subTest(value=type(value)), \
                    mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=None), \
                    mock.patch.object(self.module.env_var_repo, "add_service_env") as add, \
                    self.assertRaises(ServiceHandleException) as caught:
                self.module.configure_installation(self.tenant, self.region, self.backend)
            add.assert_not_called()
            self.set_env.assert_not_called()
            self.assertEqual(caught.exception.status_code, 503)
            self.assertNotIn("fixture", str(caught.exception))

    def test_new_install_injects_only_backend_inner_changed_env(self):
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=None), \
                mock.patch.object(self.module.env_var_repo, "add_service_env") as add:
            result = self.module.configure_installation(self.tenant, self.region, self.backend)
        self.assertIsNone(result)
        options = add.call_args.kwargs
        self.assertEqual(options["service_id"], self.backend.service_id)
        self.assertEqual(options["tenant_id"], self.tenant.tenant_id)
        self.assertEqual(options["attr_name"], "AI_ENGINE_PLATFORM_TOKEN")
        self.assertEqual(options["attr_value"], self.expected)
        self.assertTrue(options["is_change"])
        self.assertEqual(options["scope"], "inner")
        self.assertEqual(options["container_port"], 0)
        self.set_env.assert_called_once_with("enterprise-a", "region-a", "team-a", "backend", self.expected, create=True)

    def test_repeat_sync_is_noop_and_rotation_preserves_runtime_metadata(self):
        current = SimpleNamespace(ID=9, attr_value=self.expected, scope="inner", is_change=True)
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=current), \
                mock.patch.object(self.module.env_var_repo, "update_env_var") as persist:
            self.module.configure_installation(self.tenant, self.region, self.backend)
            self.set_env.assert_not_called()
            persist.assert_not_called()
            self.bootstrap.return_value = "b" * 64
            self.module.configure_installation(self.tenant, self.region, self.backend)
        self.set_env.assert_called_once_with("enterprise-a", "region-a", "team-a", "backend", "b" * 64, create=False)
        self.assertEqual(persist.call_args.kwargs["attr_value"], "b" * 64)
        self.assertEqual(persist.call_args.kwargs["scope"], "inner")
        self.assertTrue(persist.call_args.kwargs["is_change"])

    def test_existing_outer_or_template_env_is_repaired_even_when_value_matches(self):
        current = SimpleNamespace(ID=9, attr_value=self.expected, scope="outer", is_change=False)
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=current), \
                mock.patch.object(self.module.env_var_repo, "update_env_var") as persist:
            self.module.configure_installation(self.tenant, self.region, self.backend)
        self.set_env.assert_called_once_with("enterprise-a", "region-a", "team-a", "backend", self.expected, create=False)
        self.assertTrue(persist.call_args.kwargs["is_change"])
        self.assertEqual(persist.call_args.kwargs["scope"], "inner")

    def test_foreign_component_or_region_never_gets_credential(self):
        for attribute, foreign in (("tenant_id", "other-team"), ("service_region", "other-region")):
            old = getattr(self.backend, attribute)
            setattr(self.backend, attribute, foreign)
            with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name") as read, \
                    self.assertRaises(ServiceHandleException):
                self.module.configure_installation(self.tenant, self.region, self.backend)
            read.assert_not_called()
            self.bootstrap.assert_not_called()
            setattr(self.backend, attribute, old)
        self.region.enterprise_id = "other-enterprise"
        with self.assertRaises(ServiceHandleException):
            self.module.configure_installation(self.tenant, self.region, self.backend)
        self.bootstrap.assert_not_called()

    def test_arbitrary_team_claiming_plugin_identity_never_gets_platform_token(self):
        self.tenant.namespace = "ordinary-team"
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name") as read, \
                self.assertRaises(ServiceHandleException):
            self.module.configure_installation(self.tenant, self.region, self.backend)
        read.assert_not_called()
        self.bootstrap.assert_not_called()

    def test_ordinary_owner_preclaiming_platform_namespace_is_rejected(self):
        self.owner_is_admin.return_value = False
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name") as read, \
                self.assertRaises(ServiceHandleException):
            self.module.configure_installation(self.tenant, self.region, self.backend)
        self.owner_is_admin.assert_called_once_with("enterprise-a", 42)
        read.assert_not_called()
        self.bootstrap.assert_not_called()

    def test_valid_mtls_bootstrap_needs_no_region_token_or_hmac_mode(self):
        self.region.token = ""
        with mock.patch.object(settings, "MODULES", {"RegionToken": False}), \
                mock.patch.dict(os.environ, {"REGION_TOKEN": ""}), \
                mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=None), \
                mock.patch.object(self.module.env_var_repo, "add_service_env") as add:
            self.module.configure_installation(self.tenant, self.region, self.backend)
        self.bootstrap.assert_called_once_with("enterprise-a", "region-a")
        self.assertEqual(add.call_args.kwargs["attr_value"], self.expected)

    def test_unsynchronized_backend_keeps_env_local_until_normal_service_sync(self):
        self.backend.create_status = "creating"
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=None), \
                mock.patch.object(self.module.env_var_repo, "add_service_env") as add:
            self.module.configure_installation(self.tenant, self.region, self.backend)
        self.set_env.assert_not_called()
        self.assertEqual(add.call_args.kwargs["attr_value"], self.expected)
        self.assertEqual(add.call_args.kwargs["scope"], "inner")

    def test_bootstrap_error_is_sanitized_before_any_env_write(self):
        self.bootstrap.side_effect = RuntimeError("fixture-secret")
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=None), \
                mock.patch.object(self.module.env_var_repo, "add_service_env") as add, \
                self.assertRaises(ServiceHandleException) as caught:
            self.module.configure_installation(self.tenant, self.region, self.backend)
        add.assert_not_called()
        self.set_env.assert_not_called()
        self.assertNotIn("fixture-secret", str(caught.exception))

    def test_env_api_failure_is_sanitized_and_never_persists_failed_change(self):
        current = SimpleNamespace(ID=9, attr_value="old-fixture", scope="inner", is_change=True)
        self.set_env.side_effect = RuntimeError("fixture-secret")
        with mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", return_value=current), \
                mock.patch.object(self.module.env_var_repo, "update_env_var") as persist, \
                self.assertRaises(ServiceHandleException) as caught:
            self.module.configure_installation(self.tenant, self.region, self.backend)
        persist.assert_not_called()
        self.assertNotIn("fixture-secret", str(caught.exception))


class AIEngineReconciliationTests(TestCase):
    def test_reconciliation_configures_resolved_ai_backend_before_registering_plugin(self):
        from console.tests import rbd_plugin_sync_service_test as fixtures
        fixture = fixtures.RBDPluginSyncServiceTests()
        fixture.setUp()
        template = copy.deepcopy(fixture.template)
        template["platform_plugin"]["plugin_id"] = "rainbond-ai-engine"
        configure = mock.Mock()
        helper = ModuleType("console.services.ai_engine_installation")
        helper.configure_installation = configure
        patches = fixture._patch_desired_state()
        with mock.patch.dict(sys.modules, {helper.__name__: helper}), \
                patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5] as apply:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            order = []
            configure.side_effect = lambda *args: order.append("credential")
            apply.side_effect = lambda *args: order.append("register")
            result = fixture.service.reconcile(fixture.tenant, fixture.region, template, 23)
        configure.assert_called_once_with(fixture.tenant, fixture.region, fixture.api)
        self.assertEqual(order, ["credential", "register"])
        self.assertNotIn("TOKEN", repr(result))
        self.assertNotIn("TOKEN", repr(apply.call_args))

    def test_non_ai_plugin_preserves_existing_reconciliation(self):
        from console.tests import rbd_plugin_sync_service_test as fixtures
        fixture = fixtures.RBDPluginSyncServiceTests()
        fixture.setUp()
        helper = ModuleType("console.services.ai_engine_installation")
        helper.configure_installation = mock.Mock()
        patches = fixture._patch_desired_state()
        with mock.patch.dict(sys.modules, {helper.__name__: helper}), \
                patches[0] as relation_filter, patches[1], patches[2], patches[3], patches[4], patches[5]:
            relation_filter.return_value.values_list.return_value = ["svc-ui", "svc-api"]
            fixture.service.reconcile(fixture.tenant, fixture.region, fixture.template, 23)
        helper.configure_installation.assert_not_called()


class AIEnginePredeployCredentialTests(TestCase):
    def fixture(self, plugin_id):
        from console.services.market_app.app_upgrade import AppUpgrade
        app = AppUpgrade.__new__(AppUpgrade)
        app.tenant = SimpleNamespace(tenant_id="team-a")
        app.region = SimpleNamespace(region_name="region-a")
        app.region_name = "region-a"
        app.app = SimpleNamespace(ID=23)
        app.user = SimpleNamespace()
        app.app_template = {"platform_plugin": {"plugin_id": plugin_id}}
        app.is_deploy = True
        app.install_plugins = mock.Mock()
        app.sync_new_app = mock.Mock()
        app.save_new_app = mock.Mock()
        app.create_service_tcp_domains = mock.Mock()
        app._install_deploy = mock.Mock(return_value=[])
        return app

    def test_new_ai_install_bootstraps_before_first_deploy(self):
        app = self.fixture("rainbond-ai-engine")
        order = []
        app.save_new_app.side_effect = lambda: order.append("save")
        app._install_deploy.side_effect = lambda: order.append("deploy") or []
        with mock.patch("console.services.rbd_plugin_sync_service.rbd_plugin_sync_service.reconcile",
                        side_effect=lambda *args: order.append("credential")):
            app.install()
        self.assertEqual(order, ["save", "credential", "deploy"])

    def test_upgrade_bootstraps_before_normal_update_deploy(self):
        app = self.fixture("rainbond-ai-engine")
        app.app_model_key = "model-a"
        app.version = "v2"
        app.tenant.tenant_name = "team-a"
        app.install_from_cloud = False
        app.record = SimpleNamespace(ID=9)
        app._save_app = mock.Mock()
        app._deploy = mock.Mock()
        order = []
        app._save_app.side_effect = lambda: order.append("save")
        app._deploy.side_effect = lambda *args: order.append("deploy")
        with mock.patch("console.services.cleanup_retirement.lock_template_use", return_value=nullcontext()), \
                mock.patch("console.services.market_app.app_upgrade.AppUpgradeRecord.objects.filter"), \
                mock.patch("console.services.rbd_plugin_sync_service.rbd_plugin_sync_service.reconcile",
                           side_effect=lambda *args: order.append("credential")):
            app.upgrade()
        self.assertEqual(order, ["save", "credential", "deploy"])

    def test_other_plugin_install_has_no_new_predeploy_hook(self):
        app = self.fixture("other-plugin")
        with mock.patch("console.services.rbd_plugin_sync_service.rbd_plugin_sync_service.reconcile") as reconcile:
            app.install()
        reconcile.assert_not_called()
