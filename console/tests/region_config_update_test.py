# -*- coding: utf-8 -*-
# capability_id: console.region.update-region-config
import collections
import collections.abc
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
        cfg.update_config.assert_called_once_with(
            "REGION_SERVICE_API", {"enable": True, "value": REGION_JSON})
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
