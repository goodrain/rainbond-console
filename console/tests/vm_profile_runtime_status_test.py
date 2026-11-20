# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
openapi_client_module = ModuleType("openapi_client")
openapi_client_module.ApiClient = lambda configuration=None: SimpleNamespace(configuration=configuration)
openapi_client_module.MarketOpenapiApi = lambda client=None: SimpleNamespace(client=client)

openapi_client_configuration = ModuleType("openapi_client.configuration")


class _OpenAPIConfiguration(object):
    def __init__(self):
        self.client_side_validation = False
        self.host = ""
        self.api_key = {}


openapi_client_configuration.Configuration = _OpenAPIConfiguration

openapi_client_rest = ModuleType("openapi_client.rest")


class _ApiException(Exception):
    def __init__(self, status=400, body=""):
        super().__init__(body)
        self.status = status
        self.body = body


openapi_client_rest.ApiException = _ApiException

sys.modules.setdefault("openapi_client", openapi_client_module)
sys.modules.setdefault("openapi_client.configuration", openapi_client_configuration)
sys.modules.setdefault("openapi_client.rest", openapi_client_rest)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.virtual_machine import vms  # noqa: E402
from console.services.app_actions.app_log import AppEventService  # noqa: E402


# capability_id: console.vm-guest.profile-observation
class VMGuestStatusIntegrationTests(TestCase):
    def test_status_service_preserves_observed_false_and_distinguishes_old_backend(self):
        from console.services.app import app_service
        tenant = SimpleNamespace(tenant_name="team", enterprise_id="enterprise")
        service = SimpleNamespace(service_region="region", service_alias="alias", extend_method="vm")
        guest = {"status": "unconfirmed", "reason": "agent_disconnected", "agent_connected": False}
        with mock.patch("console.services.app.region_api.check_service_status", return_value={
                "bean": {"cur_status": "running", "start_time": "", "vm_guest": guest}}):
            result = app_service.get_service_status(tenant, service)
        self.assertEqual(result["vm_guest"], guest)
        with mock.patch("console.services.app.region_api.check_service_status", return_value={
                "bean": {"cur_status": "running", "start_time": ""}}):
            self.assertEqual(app_service.get_service_status(tenant, service)["vm_guest"]["reason"], "backend_unsupported")
        with mock.patch("console.services.app.region_api.check_service_status", side_effect=RuntimeError), \
                mock.patch("console.services.app.logger.exception"):
            self.assertEqual(app_service.get_service_status(tenant, service)["vm_guest"]["reason"], "read_failed")

    def test_profile_exposes_whitelisted_guest_observation(self):
        guest = {"status": "responding", "reason": "agent_connected", "agent_connected": True,
                 "os": {"name": "Ubuntu", "version": "24.04", "kernel_release": "6.8", "users": ["omit"]}}
        service = SimpleNamespace(service_id="service", tenant_id="tenant", image="", extend_method="vm")
        with mock.patch.object(vms, "get_vm_runtime_config", return_value={}), \
                mock.patch.object(vms, "get_vm_asset_for_service", return_value=None), \
                mock.patch.object(vms, "get_vm_network_profile", return_value={}):
            profile = vms.get_vm_profile(service, runtime_status={"status": "running", "vm_guest": guest})
        self.assertIs(profile["guest"]["agent_connected"], True)
        self.assertNotIn("users", profile["guest"]["os"])

    def test_status_to_profile_preserves_guest_states_and_existing_fields(self):
        from console.services.app import app_service
        tenant = SimpleNamespace(tenant_name="team", enterprise_id="enterprise")
        service = SimpleNamespace(service_id="service", tenant_id="tenant", image="", extend_method="vm",
                                  service_region="region", service_alias="alias")
        cases = [
            ("running", "responding", "agent_connected", True),
            ("running", "unconfirmed", "agent_disconnected", False),
            ("running", "unconfirmed", "agent_not_reported", None),
            ("closed", "powered_off", "vm_stopped", None),
            ("paused", "paused", "vm_paused", None),
            ("starting", "starting", "vm_starting", None),
            ("running", "unavailable", "read_failed", None),
            ("running", "unavailable", "backend_unsupported", None),
        ]
        for power, state, reason, connected in cases:
            with self.subTest(reason=reason):
                guest = {"status": state, "reason": reason, "agent_connected": connected}
                restore = {"operation_id": "restore-observation"}
                with mock.patch("console.services.app.region_api.check_service_status", return_value={
                        "bean": {"cur_status": power, "start_time": "observed-start", "vm_restore": restore,
                                 "vm_guest": guest}}), \
                        mock.patch.object(vms, "get_vm_runtime_config", return_value={}), \
                        mock.patch.object(vms, "get_vm_asset_for_service", return_value=None), \
                        mock.patch.object(vms, "get_vm_network_profile", return_value={}):
                    status = app_service.get_service_status(tenant, service)
                    profile = vms.get_vm_profile(service, runtime_status=status)
                self.assertEqual(profile["guest"], guest)
                self.assertIs(profile["guest"]["agent_connected"], connected)
                self.assertEqual(profile["runtime_status"], status)
                self.assertEqual(status["start_time"], "observed-start")
                self.assertEqual(status["vm_restore"], restore)

    def test_container_status_does_not_gain_vm_guest_fields(self):
        from console.services.app import app_service
        tenant = SimpleNamespace(tenant_name="team", enterprise_id="enterprise")
        service = SimpleNamespace(service_region="region", service_alias="alias", extend_method="stateless")
        with mock.patch("console.services.app.region_api.check_service_status", return_value={
                "bean": {"cur_status": "running", "start_time": "observed-start"}}):
            status = app_service.get_service_status(tenant, service)
        self.assertNotIn("vm_guest", status)
        self.assertEqual(status["status"], "running")


class VMProfileRuntimeStatusTests(TestCase):
    def test_get_vm_profile_exposes_runtime_status(self):
        with mock.patch.object(vms, "get_vm_runtime_config", return_value={}), \
                mock.patch.object(vms, "get_vm_asset_for_service", return_value=None), \
                mock.patch.object(vms, "get_vm_network_profile", return_value={}):
            profile = vms.get_vm_profile(
                SimpleNamespace(
                    tenant_id="tenant-a",
                    service_id="service-a",
                    image="demo/win10",
                    extend_method="vm"
                ),
                runtime_status={
                    "status": "restoring",
                    "status_cn": "恢复中",
                }
            )

        self.assertEqual({"status": "restoring", "status_cn": "恢复中"}, profile["runtime_status"])

    def test_get_vm_profile_hides_vnc_until_current_vm_pod_ip_is_ready(self):
        with mock.patch.object(vms, "get_vm_runtime_config", return_value={}), \
                mock.patch.object(vms, "get_vm_asset_for_service", return_value=None), \
                mock.patch.object(vms, "get_vm_network_profile", return_value={}):
            profile = vms.get_vm_profile(
                SimpleNamespace(
                    tenant_id="tenant-a",
                    service_id="service-a",
                    image="demo/win10",
                    extend_method="vm"
                ),
                current_pod_ip="",
                connections={
                    "vnc_url": "http://example.com/vnc",
                    "console_url": "http://example.com/console"
                }
            )

        self.assertEqual("", profile["current_pod_ip"])
        self.assertEqual("", profile["connections"]["vnc_url"])
        self.assertEqual("", profile["connections"]["console_url"])


class VMRestoreEventTests(TestCase):
    # capability_id: console.vm-template-import.restore-operation-record
    def test_build_vm_restore_event_exposes_progress_and_importer_logs(self):
        service = SimpleNamespace(service_id="service-a", deploy_version="20260522172810")

        event = AppEventService().build_vm_restore_event(service, {
            "status": "restoring",
            "status_cn": "恢复中",
            "progress": "11.34%",
            "message": "manual133: TransferRunning",
            "data_volumes": [
                {
                    "name": "manual133",
                    "phase": "ImportInProgress",
                    "progress": "11.34%",
                    "message": "TransferRunning",
                }
            ],
            "importer_pods": [
                {
                    "name": "importer-manual133",
                    "namespace": "default",
                    "volume": "manual133",
                }
            ],
        })

        self.assertEqual("vm-disk-restore-service-a", event["event_id"])
        self.assertEqual("vm-disk-restore", event["opt_type"])
        self.assertEqual("restoring", event["status"])
        self.assertEqual("", event["final_status"])
        self.assertEqual("11.34%", event["vm_restore"]["progress"])
        self.assertEqual(0, event["syn_type"])

    # capability_id: console.vm-template-import.restore-operation-record
    def test_build_vm_restore_event_marks_success_after_import_finishes(self):
        service = SimpleNamespace(service_id="service-a", deploy_version="20260522172810")

        event = AppEventService().build_vm_restore_event(service, {
            "status": "success",
            "status_cn": "恢复完成",
            "progress": "100.0%",
            "data_volumes": [
                {
                    "name": "manual133",
                    "phase": "Succeeded",
                    "progress": "100.0%",
                }
            ],
        })

        self.assertEqual("success", event["status"])
        self.assertEqual("complete", event["final_status"])
        self.assertEqual("100.0%", event["vm_restore"]["progress"])
