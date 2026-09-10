# -*- coding: utf-8 -*-
import collections
import importlib
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

from addict import Dict

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    configuration_module = ModuleType("openapi_client.configuration")
    rest_module = ModuleType("openapi_client.rest")

    class _DummyConfiguration(object):
        def __init__(self):
            self.client_side_validation = False
            self.host = ""
            self.api_key = {}

    class _DummyApiException(Exception):
        status = 500
        body = ""

    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module.Configuration = _DummyConfiguration
    rest_module.ApiException = _DummyApiException

    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

volume_service_module = importlib.import_module("console.services.app_config.volume_service")
AppVolumeService = volume_service_module.AppVolumeService


class AppVolumeServiceExpansionTestCase(TestCase):
    def setUp(self):
        self.volume_service = AppVolumeService()
        self.tenant = mock.Mock(tenant_name="demo-team", enterprise_id="enterprise-1")
        self.service = mock.Mock(
            create_status="complete",
            service_region="region-1",
            service_alias="demo-service",
        )
        self.volume = mock.Mock()
        self.volume.to_dict.return_value = {
            "volume_name": "data",
            "volume_capacity": 50,
        }

    # capability_id: console.component.volume-expansion-runtime
    def test_attach_volume_runtime_status_merges_expansion_fields(self):
        body = Dict({
            "list": [{
                "volume_name": "data",
                "status": "READY",
                "allow_expansion": True,
                "actual_capacity": 20,
                "requested_capacity": 50,
                "expansion_status": "resizing",
                "expansion_message": "controller is resizing the volume",
                "pvc_count": 2,
            }]
        })
        with mock.patch.object(volume_service_module.region_api,
                               "get_service_volumes",
                               return_value=(mock.Mock(status=200), body)):
            result = self.volume_service._attach_volume_runtime_status(self.tenant, self.service, [self.volume])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "bound")
        self.assertTrue(result[0]["allow_expansion"])
        self.assertEqual(result[0]["actual_capacity"], 20)
        self.assertEqual(result[0]["requested_capacity"], 50)
        self.assertEqual(result[0]["expansion_status"], "resizing")
        self.assertEqual(result[0]["expansion_message"], "controller is resizing the volume")
        self.assertEqual(result[0]["pvc_count"], 2)

    def test_attach_volume_runtime_status_accepts_legacy_region_fields(self):
        body = Dict({"list": [{"volume_name": "data", "status": "READY"}]})
        with mock.patch.object(volume_service_module.region_api,
                               "get_service_volumes",
                               return_value=(mock.Mock(status=200), body)):
            result = self.volume_service._attach_volume_runtime_status(self.tenant, self.service, [self.volume])

        self.assertEqual(result, [{"volume_name": "data", "volume_capacity": 50, "status": "bound"}])
