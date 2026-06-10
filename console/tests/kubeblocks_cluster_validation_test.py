# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import mock
import unittest

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
openapi_client = ModuleType("openapi_client")
openapi_client.ApiClient = mock.Mock()
openapi_client.MarketOpenapiApi = mock.Mock()
configuration_module = ModuleType("openapi_client.configuration")
configuration_module.Configuration = mock.Mock
rest_module = ModuleType("openapi_client.rest")
rest_module.ApiException = Exception
sys.modules.setdefault("openapi_client", openapi_client)
sys.modules.setdefault("openapi_client.configuration", configuration_module)
sys.modules.setdefault("openapi_client.rest", rest_module)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.kubeblocks_service import KubeBlocksService  # noqa: E402


class KubeBlocksClusterValidationTests(unittest.TestCase):

    def setUp(self):
        self.service = KubeBlocksService()

    def _valid_params(self):
        return {
            "cluster_name": "mysql-demo",
            "database_type": "mysql",
            "version": "8.0.30",
            "cpu": "500m",
            "memory": "512Mi",
            "storage_size": "10Gi",
            "replicas": 1,
        }

    # capability_id: console.kubeblocks.cluster-resource-validation
    def test_validate_cluster_params_rejects_zero_cpu(self):
        params = self._valid_params()
        params["cpu"] = "0m"

        valid, message = self.service.validate_cluster_params(params)

        self.assertFalse(valid)
        self.assertEqual(message, "CPU 配置必须大于0")

    # capability_id: console.kubeblocks.cluster-resource-validation
    def test_validate_cluster_params_rejects_zero_memory(self):
        params = self._valid_params()
        params["memory"] = "0Mi"

        valid, message = self.service.validate_cluster_params(params)

        self.assertFalse(valid)
        self.assertEqual(message, "内存配置必须大于0")

    # capability_id: console.kubeblocks.cluster-resource-validation
    def test_validate_cluster_params_accepts_positive_decimal_cpu_and_memory(self):
        params = self._valid_params()
        params["cpu"] = "0.5"
        params["memory"] = "0.5Gi"

        valid, message = self.service.validate_cluster_params(params)

        self.assertTrue(valid)
        self.assertEqual(message, "")
