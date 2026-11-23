# -*- coding: utf-8 -*-
# capability_id: console.ai-engine.monitoring-credential-installation
import importlib
import os
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")
import django  # noqa: E402

django.setup()
from console.exception.main import ServiceHandleException  # noqa: E402


class AIEngineMonitoringInstallationTests(TestCase):
    def setUp(self):
        self.module = importlib.import_module("console.services.ai_engine_installation")
        self.tenant = SimpleNamespace(tenant_id="team",
                                      tenant_name="team",
                                      namespace="rbd-plugins",
                                      enterprise_id="enterprise",
                                      creater=42)
        self.region = SimpleNamespace(region_name="region", enterprise_id="enterprise")
        self.backend = self.component("backend", "ai-engine")
        self.prometheus = self.component("prometheus", "ai-engine-prometheus")
        self.components = [self.backend, self.prometheus]
        self.relations = [
            SimpleNamespace(service_id=item.service_id, tenant_id="team", region_name="region", group_id=1)
            for item in self.components
        ]
        self.env = {}
        self.in_allocation = False
        patches = {
            "admin":
            mock.patch.object(self.module.enterprise_user_perm_repo, "is_admin", return_value=True),
            "relation_query":
            mock.patch.object(self.module.ServiceGroupRelation.objects, "filter", side_effect=self.relation_filter),
            "components_query":
            mock.patch.object(self.module.TenantServiceInfo.objects, "filter", return_value=self.components),
            "locked":
            mock.patch.object(self.module.TenantServiceInfo.objects, "select_for_update"),
            "atomic":
            mock.patch.object(self.module.transaction, "atomic", side_effect=self.atomic),
            "read":
            mock.patch.object(self.module.env_var_service, "get_env_by_attr_name", side_effect=self.read_env),
            "add":
            mock.patch.object(self.module.env_var_repo, "add_service_env", side_effect=self.add_env),
            "update":
            mock.patch.object(self.module.env_var_repo, "update_env_var", side_effect=self.update_env),
            "sync":
            mock.patch.object(self.module.region_api, "set_ai_engine_monitoring_env", side_effect=self.sync_env),
            "random":
            mock.patch.object(self.module.secrets, "token_hex", return_value="a" * 64),
        }
        for name, patcher in patches.items():
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.locked.return_value.filter.return_value.order_by.return_value = self.components

    @staticmethod
    def component(service_id, role):
        return SimpleNamespace(service_id=service_id,
                               service_alias=service_id,
                               k8s_component_name=role,
                               tenant_id="team",
                               service_region="region",
                               service_source="docker_image",
                               create_status="complete")

    def relation_filter(self, **kwargs):
        if "service_id" in kwargs:
            return [item for item in self.relations if item.service_id == kwargs["service_id"]]
        return self.relations

    @contextmanager
    def atomic(self):
        self.assertFalse(self.in_allocation)
        self.in_allocation = True
        try:
            yield
        finally:
            self.in_allocation = False

    def read_env(self, tenant, component, name):
        self.assertEqual(name, self.module.MONITORING_TOKEN_ENV)
        return self.env.get(component.service_id)

    def add_env(self, **kwargs):
        self.assertTrue(self.in_allocation)
        self.assertEqual(kwargs["attr_name"], self.module.MONITORING_TOKEN_ENV)
        self.env[kwargs["service_id"]] = SimpleNamespace(**kwargs)

    def update_env(self, tenant_id, service_id, name, **kwargs):
        self.assertTrue(self.in_allocation)
        self.assertEqual(name, self.module.MONITORING_TOKEN_ENV)
        self.env[service_id].__dict__.update(kwargs)

    def sync_env(self, enterprise_id, region_name, tenant_name, alias, value, **kwargs):
        self.assertFalse(self.in_allocation, "Region calls must not hold the allocation lock")
        self.assertEqual(value, self.env[alias].attr_value)
        self.assertTrue(kwargs["create"], "POST/duplicate-to-PUT also recovers partial previous syncs")

    def test_generates_one_protected_value_shared_by_both_components_and_reuses_on_retry(self):
        self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.random.assert_called_once_with(32)
        self.assertEqual(self.add.call_count, 2)
        self.assertEqual(self.sync.call_count, 4)
        for current in self.env.values():
            self.assertRegex(current.attr_value, r"^[0-9a-f]{64}$")
            self.assertEqual(current.scope, "inner")
            self.assertTrue(current.is_change)
        self.assertEqual(self.env["backend"].attr_value, self.env["prometheus"].attr_value)

    def test_existing_legal_pair_is_preserved_without_random_generation(self):
        for component in self.components:
            self.env[component.service_id] = SimpleNamespace(attr_value="existing-protected-value-" * 2,
                                                             scope="inner",
                                                             is_change=True)
        self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.random.assert_not_called()
        self.add.assert_not_called()
        self.assertEqual(self.env["backend"].attr_value, "existing-protected-value-" * 2)

    def test_partial_sync_retry_uses_the_same_persisted_value(self):
        self.sync.side_effect = RuntimeError("upstream request contains sensitive data")
        with self.assertRaises(ServiceHandleException) as caught:
            self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.assertNotIn("sensitive", str(caught.exception))
        self.sync.side_effect = self.sync_env
        self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.random.assert_called_once_with(32)

    def test_second_component_first_write_failure_recovers_without_rotating_either_value(self):
        region_env = {}
        fail_prometheus = True

        def sync(enterprise, region, tenant, alias, value, **kwargs):
            nonlocal fail_prometheus
            self.sync_env(enterprise, region, tenant, alias, value, **kwargs)
            if alias == "prometheus" and fail_prometheus:
                fail_prometheus = False
                raise RuntimeError("unavailable")
            region_env[alias] = value

        self.sync.side_effect = sync
        with self.assertRaises(ServiceHandleException):
            self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.assertEqual(set(region_env), {"backend"})
        self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.assertEqual(set(region_env), {"backend", "prometheus"})
        self.assertEqual(region_env["backend"], region_env["prometheus"])
        self.random.assert_called_once_with(32)

    def test_rejects_cross_app_team_region_and_ambiguous_membership_before_allocating(self):
        self.relations[1].tenant_id = "foreign"
        with self.assertRaises(ServiceHandleException):
            self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.relations[1].tenant_id = "team"
        self.relations.append(SimpleNamespace(**self.relations[0].__dict__))
        with self.assertRaises(ServiceHandleException):
            self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.random.assert_not_called()
        self.sync.assert_not_called()

    def test_invalid_existing_value_fails_without_replacement(self):
        self.env["backend"] = SimpleNamespace(attr_value="short-sensitive", scope="inner", is_change=True)
        with self.assertRaises(ServiceHandleException) as caught:
            self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.assertNotIn("short-sensitive", str(caught.exception))
        self.random.assert_not_called()
        self.sync.assert_not_called()

    def test_different_valid_existing_values_are_never_silently_rotated(self):
        self.env["backend"] = SimpleNamespace(attr_value="a" * 64, scope="inner", is_change=True)
        self.env["prometheus"] = SimpleNamespace(attr_value="b" * 64, scope="inner", is_change=True)
        with self.assertRaises(ServiceHandleException):
            self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.random.assert_not_called()
        self.update.assert_not_called()
        self.sync.assert_not_called()

    def test_one_existing_valid_value_is_reused_to_fill_the_missing_component(self):
        self.env["prometheus"] = SimpleNamespace(attr_value="b" * 64, scope="inner", is_change=True)
        self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.assertEqual(self.env["backend"].attr_value, self.env["prometheus"].attr_value)
        self.random.assert_not_called()

    def test_other_app_and_virtual_machine_lifecycle_do_not_read_or_allocate(self):
        ordinary = self.component("ordinary", "web")
        virtual_machine = self.component("vm", "ai-engine")
        virtual_machine.service_source = "vm_run"
        self.module.prepare_component_credentials(self.tenant, [ordinary, virtual_machine])
        self.relation_query.assert_not_called()
        self.random.assert_not_called()
        self.sync.assert_not_called()

    def test_missing_dedicated_prometheus_blocks_configuration_instead_of_skipping_monitoring(self):
        self.components_query.return_value = [self.backend]
        with self.assertRaises(ServiceHandleException):
            self.module.configure_monitoring_installation(self.tenant, self.region, self.backend)
        self.random.assert_not_called()
        self.sync.assert_not_called()

    def test_missing_dedicated_prometheus_blocks_predeploy_before_platform_bootstrap(self):
        self.components_query.return_value = [self.backend]
        with mock.patch.object(self.module.RegionConfig.objects, "get", return_value=self.region), \
                mock.patch.object(self.module, "configure_installation") as configure:
            with self.assertRaises(ServiceHandleException):
                self.module.prepare_component_credentials(self.tenant, [self.backend])
        configure.assert_not_called()

    def test_starting_both_roles_bootstraps_the_backend_only_once(self):
        with mock.patch.object(self.module.RegionConfig.objects, "get", return_value=self.region), \
                mock.patch.object(self.module, "configure_installation") as configure:
            self.module.prepare_component_credentials(self.tenant, self.components)
        configure.assert_called_once_with(self.tenant, self.region, self.backend)
