# -*- coding: utf-8 -*-
# capability_id: console.ai-engine.monitoring-credential-lifecycle
import importlib
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402


class AIEngineMonitoringLifecycleTests(TestCase):
    def setUp(self):
        self.module = importlib.import_module("console.services.app_actions.app_manage")
        self.manager = self.module.AppManageService()
        self.real_prepare = self.module._prepare_ai_engine_credentials
        self.tenant = SimpleNamespace(tenant_id="team-a",
                                      tenant_name="team-a",
                                      enterprise_id="enterprise-a",
                                      namespace="rbd-plugins",
                                      creater=42)
        self.service = SimpleNamespace(tenant_id="team-a",
                                       service_id="existing-ai-backend",
                                       service_alias="ai-backend",
                                       service_region="region-a",
                                       service_source="docker_image",
                                       create_status="complete",
                                       extend_method="stateless_multiple",
                                       arch="amd64",
                                       build_upgrade=False,
                                       language=None,
                                       image="example.invalid/ai-backend:existing",
                                       cmd="",
                                       git_url="")
        self.user = SimpleNamespace(nick_name="admin", user_id=42)
        self.events = []
        patches = {
            "quota": mock.patch.object(self.module, "check_account_quota", return_value=True),
            "prepare": mock.patch.object(self.module, "_prepare_ai_engine_credentials", create=True, side_effect=self._prepare),
            "services": mock.patch.object(self.module.service_repo, "get_services_by_service_ids", return_value=[self.service]),
        }
        for name, patcher in patches.items():
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def _prepare(self, tenant, services):
        self.assertIs(tenant, self.tenant)
        self.assertEqual(list(services), [self.service])
        self.events.append("prepare")

    def _rpc(self, *args, **kwargs):
        self.events.append("region")

    def test_existing_installation_start_prepares_credentials_before_region_start(self):
        with mock.patch.object(self.module.region_api, "start_service", side_effect=self._rpc) as start:
            code, _ = self.manager.start(self.tenant, self.service, self.user, None)
        self.assertEqual(code, 200)
        self.assertEqual(self.events, ["prepare", "region"])
        self.prepare.assert_called_once()
        start.assert_called_once()

    def test_existing_installation_upgrade_prepares_credentials_before_region_upgrade(self):
        def upgrade(*args, **kwargs):
            self._rpc()
            return {"bean": {"event_id": "upgrade-event"}}

        with mock.patch.object(self.module.region_api, "upgrade_service", side_effect=upgrade) as rpc:
            code, _, event_id = self.manager.upgrade(self.tenant, self.service, self.user)
        self.assertEqual((code, event_id), (200, "upgrade-event"))
        self.assertEqual(self.events, ["prepare", "region"])
        self.prepare.assert_called_once()
        rpc.assert_called_once()

    def test_build_deploy_prepares_credentials_before_region_build(self):
        def build(*args, **kwargs):
            self._rpc()
            return {"bean": {"status": "success", "event_id": "build-event"}}

        with mock.patch.object(self.module.region_api, "get_cluster_nodes_arch",
                               return_value=(200, {"list": ["amd64"]})), \
                mock.patch.object(self.module.env_var_repo, "get_build_envs", return_value={}), \
                mock.patch.object(self.module.service_source_repo, "get_service_source", return_value=None), \
                mock.patch.object(self.module.region_api, "build_service", side_effect=build) as rpc:
            code, _, event_id = self.manager.deploy(self.tenant, self.service, self.user)
        self.assertEqual((code, event_id), (200, "build-event"))
        self.assertEqual(self.events, ["prepare", "region"])
        self.prepare.assert_called_once()
        rpc.assert_called_once()

    def test_batch_start_upgrade_and_deploy_prepare_after_payload_before_region(self):
        for action in ("start", "upgrade", "deploy"):
            self.events.clear()
            self.prepare.reset_mock()

            def payload(*args, **kwargs):
                self.events.append("payload")
                return 200, {"operation": action}

            def operate(*args, **kwargs):
                self._rpc()
                return 200, {"bean": {"batch_result": ["event"]}}

            with self.subTest(action=action), \
                    mock.patch.object(self.manager, action + "_services_info", side_effect=payload), \
                    mock.patch.object(self.module.region_api, "batch_operation_service", side_effect=operate) as rpc:
                result = self.manager.batch_operations(self.tenant, "region-a", self.user, action, [self.service.service_id])
            self.assertEqual(result, ["event"])
            self.assertEqual(self.events, ["payload", "prepare", "region"])
            self.prepare.assert_called_once()
            rpc.assert_called_once()

    def test_credential_failure_blocks_start_and_upgrade_and_preserves_503(self):
        for action, rpc_name in (("start", "start_service"), ("upgrade", "upgrade_service")):
            failure = ServiceHandleException("AI Engine credential unavailable", status_code=503)
            self.prepare.side_effect = failure
            with self.subTest(action=action), \
                    mock.patch.object(self.module.region_api, rpc_name) as rpc, \
                    self.assertRaises(ServiceHandleException) as caught:
                getattr(self.manager, action)(self.tenant, self.service, self.user, None)
            self.assertIs(caught.exception, failure)
            self.assertEqual(caught.exception.status_code, 503)
            rpc.assert_not_called()

    def test_credential_failure_blocks_each_batch_lifecycle_action(self):
        for action in ("start", "upgrade", "deploy"):
            failure = ServiceHandleException("AI Engine credential unavailable", status_code=503)
            self.prepare.side_effect = failure
            with self.subTest(action=action), \
                    mock.patch.object(self.manager, action + "_services_info", return_value=(200, {})), \
                    mock.patch.object(self.module.region_api, "batch_operation_service") as rpc, \
                    self.assertRaises(ServiceHandleException) as caught:
                self.manager.batch_operations(self.tenant, "region-a", self.user, action, [self.service.service_id])
            self.assertIs(caught.exception, failure)
            rpc.assert_not_called()

    def test_batch_stop_does_not_bootstrap_or_pair_credentials(self):
        with mock.patch.object(self.manager, "stop_services_info", return_value=(200, {})), \
                mock.patch.object(self.module.region_api, "batch_operation_service",
                                  return_value=(200, {"bean": {"batch_result": []}})) as rpc:
            result = self.manager.batch_operations(self.tenant, "region-a", self.user, "stop", [self.service.service_id])
        self.assertEqual(result, [])
        self.prepare.assert_not_called()
        rpc.assert_called_once()

    def test_legacy_batch_preflights_before_atomic_body_and_restores_context_without_duplicate_sync(self):
        context = self.module._ai_credentials_prepared
        previous = frozenset({"previous-request-service"})
        marker = context.set(previous)
        try:
            for should_fail in (False, True):
                self.events.clear()

                def synchronize(tenant, services):
                    self.assertEqual(context.get(), previous)
                    self._prepare(tenant, services)

                def atomic_body(*args, **kwargs):
                    self.events.append("atomic-body")
                    self.assertEqual(list(kwargs["prepared_services"]), [self.service])
                    self.assertEqual(context.get(), frozenset({self.service.service_id}))
                    # Single-component methods inside the batch must reuse preflight.
                    self.real_prepare(self.tenant, [self.service])
                    if should_fail:
                        raise RuntimeError("batch fixture failure")
                    return 200, "success", [self.service]

                with self.subTest(failing_body=should_fail), \
                        mock.patch.object(self.module, "_prepare_ai_engine_credentials", wraps=self.real_prepare), \
                        mock.patch("console.services.ai_engine_installation.prepare_component_credentials",
                                   side_effect=synchronize) as synchronize_mock, \
                        mock.patch.object(self.manager, "_batch_action", side_effect=atomic_body) as atomic:
                    if should_fail:
                        with self.assertRaisesRegex(RuntimeError, "batch fixture failure"):
                            self.manager.batch_action("region-a", self.tenant, self.user, "start", [self.service.service_id],
                                                      None, None)
                    else:
                        result = self.manager.batch_action("region-a", self.tenant, self.user, "start",
                                                           [self.service.service_id], None, None)
                        self.assertEqual(result, (200, "success", [self.service]))
                    self.assertEqual(self.events, ["prepare", "atomic-body"])
                    self.assertEqual(context.get(), previous)
                    synchronize_mock.assert_called_once()
                    atomic.assert_called_once()
                    # The next independent operation must not inherit batch deduplication.
                    self.real_prepare(self.tenant, [self.service])
                    self.assertEqual(synchronize_mock.call_count, 2)
        finally:
            context.reset(marker)

    def test_legacy_batch_preflight_failure_never_enters_atomic_body_or_changes_context(self):
        failure = ServiceHandleException("AI Engine credential unavailable", status_code=503)
        self.prepare.side_effect = failure
        previous = self.module._ai_credentials_prepared.get()
        with mock.patch.object(self.manager, "_batch_action") as atomic, \
                self.assertRaises(ServiceHandleException) as caught:
            self.manager.batch_action("region-a", self.tenant, self.user, "start", [self.service.service_id], None, None)
        self.assertIs(caught.exception, failure)
        self.assertEqual(self.module._ai_credentials_prepared.get(), previous)
        self.prepare.assert_called_once()
        atomic.assert_not_called()

    def test_ordinary_team_start_never_prepares_platform_credentials(self):
        self.tenant.namespace = "ordinary-team"
        with mock.patch.object(self.module, "_prepare_ai_engine_credentials", wraps=self.real_prepare), \
                mock.patch("console.services.ai_engine_installation.prepare_component_credentials") as synchronize, \
                mock.patch.object(self.module.region_api, "bootstrap_ai_engine_platform_token") as bootstrap, \
                mock.patch.object(self.module.region_api, "start_service") as start:
            code, _ = self.manager.start(self.tenant, self.service, self.user, None)
        self.assertEqual(code, 200)
        synchronize.assert_not_called()
        bootstrap.assert_not_called()
        start.assert_called_once()
