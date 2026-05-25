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


class VMProfileRuntimeStatusTests(TestCase):
    def test_get_vm_profile_exposes_runtime_status(self):
        with mock.patch.object(vms, "get_vm_runtime_config", return_value={}), \
                mock.patch.object(vms, "get_vm_asset_for_service", return_value=None):
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
                mock.patch.object(vms, "get_vm_asset_for_service", return_value=None):
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
