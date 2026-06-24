# -*- coding: utf-8 -*-
# capability_id: console.region.update-region-config
import base64
import collections
import collections.abc
import json
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services import region_services as region_services_module  # noqa: E402
from console.services.region_services import RegionService  # noqa: E402

REGION_JSON = '[{"region_name": "rainbond", "enable": true}]'


class UpdateRegionConfigTest(TestCase):
    def setUp(self):
        self.service = RegionService()

    def test_update_when_config_exists_passes_dict_value(self):
        # Arrange
        with mock.patch.object(self.service, "generate_region_config", return_value=REGION_JSON), \
                mock.patch.object(region_services_module, "platform_config_service") as cfg:
            cfg.get_config_by_key.return_value = object()  # truthy: config exists

            # Act
            self.service.update_region_config()

        # Assert
        cfg.update_config.assert_called_once_with("REGION_SERVICE_API", {"enable": True, "value": REGION_JSON})
        cfg.add_config.assert_not_called()

    def test_add_when_config_missing_passes_json_string_and_desc(self):
        # Arrange
        with mock.patch.object(self.service, "generate_region_config", return_value=REGION_JSON), \
                mock.patch.object(region_services_module, "platform_config_service") as cfg:
            cfg.get_config_by_key.return_value = None  # config does not exist

            # Act
            self.service.update_region_config()

        # Assert
        cfg.add_config.assert_called_once()
        args, kwargs = cfg.add_config.call_args
        self.assertEqual(args[0], "REGION_SERVICE_API")
        self.assertEqual(args[1], REGION_JSON)
        self.assertEqual(args[2], "json")
        desc = kwargs.get("desc", args[4] if len(args) > 4 else None)
        self.assertEqual(desc, "数据中心配置")
        cfg.update_config.assert_not_called()


def _b64(value):
    return base64.b64encode(value.encode("UTF-8")).decode("UTF-8")


class CreateDefaultRegionTest(TestCase):
    def test_default_region_keeps_api_service_and_uses_internal_websocket_service(self):
        region_config = {
            "binaryData": {
                "ca.pem": _b64("ca"),
                "client.key.pem": _b64("key"),
                "client.pem": _b64("cert"),
            },
            "data": {
                "websocketAddress": "ws://public.example.com:6060",
                "defaultDomainSuffix": "apps.example.com",
                "defaultTCPHost": "192.0.2.10",
            },
        }
        process = mock.Mock()
        process.stdout.read.return_value = json.dumps(region_config).encode("UTF-8")

        with mock.patch.object(region_services_module.subprocess, "Popen", return_value=process), \
                mock.patch.object(region_services_module, "make_uuid", return_value="region-id"), \
                mock.patch.object(region_services_module.region_services, "add_region", return_value="created") as add_region:
            result = region_services_module.region_services.create_default_region("enterprise-id", object())

        self.assertEqual(result, "created")
        region_info = add_region.call_args[0][0]
        self.assertEqual(region_info["url"], "https://rbd-api-api:8443")
        self.assertEqual(region_info["wsurl"], "ws://rbd-api-websocket:6060")
