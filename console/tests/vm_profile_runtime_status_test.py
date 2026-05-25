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
