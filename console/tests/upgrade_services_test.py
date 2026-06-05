# coding: utf-8
"""应用升级状态汇总测试"""
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

openapi_client_module = sys.modules.setdefault("openapi_client", ModuleType("openapi_client"))
configuration_module = sys.modules.setdefault("openapi_client.configuration", ModuleType("openapi_client.configuration"))
rest_module = sys.modules.setdefault("openapi_client.rest", ModuleType("openapi_client.rest"))


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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.models.main import AppUpgradeRecordType  # noqa: E402
from console.models.main import UpgradeStatus  # noqa: E402
from console.services.upgrade_services import UpgradeService  # noqa: E402


class FakeAppRecord(object):
    def __init__(self, record_type, status):
        self.record_type = record_type
        self.status = status


class FakeComponentRecord(object):
    def __init__(self, status):
        self.status = status


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
