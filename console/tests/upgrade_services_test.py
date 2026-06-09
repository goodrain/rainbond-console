# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase

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

from console.models.main import AppUpgradeRecordType, UpgradeStatus  # noqa: E402
from console.services.upgrade_services import UpgradeService  # noqa: E402


class FakeAppRecord(object):
    def __init__(self, record_type, status):
        self.record_type = record_type
        self.status = status


class FakeComponentRecord(object):
    def __init__(self, status):
        self.status = status


# capability_id: console.app-upgrade.record-status-summary
class UpgradeServiceRecordStatusTests(TestCase):
    def setUp(self):
        self.service = UpgradeService()

    def test_update_app_record_status_keeps_upgrading_when_any_component_unfinished(self):
        app_record = FakeAppRecord(AppUpgradeRecordType.UPGRADE.value, UpgradeStatus.UPGRADING.value)
        component_records = [
            FakeComponentRecord(UpgradeStatus.UPGRADED.value),
            FakeComponentRecord(UpgradeStatus.UPGRADING.value),
        ]

        self.service._update_app_record_status(app_record, component_records)

        self.assertEqual(UpgradeStatus.UPGRADING.value, app_record.status)

    def test_update_app_record_status_marks_partial_upgrade_for_mixed_success_and_failure(self):
        app_record = FakeAppRecord(AppUpgradeRecordType.UPGRADE.value, UpgradeStatus.UPGRADING.value)
        component_records = [
            FakeComponentRecord(UpgradeStatus.UPGRADED.value),
            FakeComponentRecord(UpgradeStatus.UPGRADE_FAILED.value),
        ]

        self.service._update_app_record_status(app_record, component_records)

        self.assertEqual(UpgradeStatus.PARTIAL_UPGRADED.value, app_record.status)

    def test_update_app_record_status_marks_partial_upgrade_when_component_records_empty(self):
        app_record = FakeAppRecord(AppUpgradeRecordType.UPGRADE.value, UpgradeStatus.UPGRADING.value)

        self.service._update_app_record_status(app_record, [])

        self.assertEqual(UpgradeStatus.PARTIAL_UPGRADED.value, app_record.status)
