import collections
import json
import os
from types import ModuleType, SimpleNamespace
from unittest import mock
from unittest import TestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import sys  # noqa: E402

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

import django  # noqa: E402

django.setup()

from console.services.k8s_attribute import k8s_attribute_service  # noqa: E402


class ComponentK8sAttributeServiceTests(TestCase):

    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="team-a")
        self.component = SimpleNamespace(service_id="service-a", service_alias="service-a")

    def test_create_k8s_attribute_serializes_json_array_values(self):
        attribute = {
            "name": "vm_gpu_resources",
            "save_type": "json",
            "attribute_value": ["nvidia.com/TU104", "nvidia.com/TU106"],
        }

        with mock.patch("console.services.k8s_attribute.k8s_attribute_repo.create") as repo_create, \
                mock.patch("console.services.k8s_attribute.region_api.create_component_k8s_attribute") as region_create:
            k8s_attribute_service.create_k8s_attribute.__wrapped__(
                k8s_attribute_service,
                self.tenant,
                self.component,
                "demo-region",
                attribute,
                "alice"
            )

        expected_value = json.dumps(["nvidia.com/TU104", "nvidia.com/TU106"])
        repo_create.assert_called_once_with(
            tenant_id="tenant-a",
            component_id="service-a",
            name="vm_gpu_resources",
            save_type="json",
            attribute_value=expected_value
        )
        region_create.assert_called_once_with(
            "team-a",
            "demo-region",
            "service-a",
            {
                "name": "vm_gpu_resources",
                "save_type": "json",
                "attribute_value": expected_value,
                "operator": "alice"
            }
        )

    def test_update_k8s_attribute_preserves_key_value_json_payloads(self):
        attribute = {
            "name": "labels",
            "save_type": "json",
            "attribute_value": [
                {
                    "key": "disktype",
                    "value": "ssd"
                },
                {
                    "key": "zone",
                    "value": "ap-shanghai-1"
                },
            ],
        }

        with mock.patch("console.services.k8s_attribute.k8s_attribute_repo.update") as repo_update, \
                mock.patch("console.services.k8s_attribute.region_api.update_component_k8s_attribute") as region_update:
            k8s_attribute_service.update_k8s_attribute.__wrapped__(
                k8s_attribute_service,
                self.tenant,
                self.component,
                "demo-region",
                attribute
            )

        expected_value = json.dumps({
            "disktype": "ssd",
            "zone": "ap-shanghai-1"
        })
        repo_update.assert_called_once_with(
            "service-a",
            "labels",
            attribute_value=expected_value
        )
        region_update.assert_called_once_with(
            "team-a",
            "demo-region",
            "service-a",
            {
                "name": "labels",
                "save_type": "json",
                "attribute_value": expected_value
            }
        )
