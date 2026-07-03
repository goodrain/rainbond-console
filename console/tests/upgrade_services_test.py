# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase
from unittest.mock import MagicMock, patch

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
from console.services import upgrade_services as upgrade_services_module  # noqa: E402
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


class FakeTeam(object):
    def __init__(self):
        self.tenant_id = "tenant-1"
        self.enterprise_id = "ent-1"


# capability_id: console.app-upgrade.openapi-upgrade-group-id
class OpenapiUpgradeGroupIdTests(TestCase):
    """openapi_upgrade_app_models must always pass upgrade_group_id to
    get_or_create_upgrade_record (which requires it as a positional arg).

    Regression for the missing-argument crash: the OpenAPI upgrade endpoint
    and the MCP upgrade tool both reached get_or_create_upgrade_record without
    upgrade_group_id, raising TypeError. The value comes from the request when
    supplied, otherwise falls back to the component's tenant_service_group_id.
    """

    def setUp(self):
        self.service = upgrade_services_module.upgrade_service
        self.team = FakeTeam()

    def _run(self, update_version):
        exist_component = MagicMock()
        exist_component.tenant_service_group_id = 2878
        services = MagicMock()
        services.first.return_value = exist_component

        created_record = MagicMock()
        created_record.ID = 99

        data = {"update_versions": [update_version]}

        with patch.object(upgrade_services_module.group_service, "get_rainbond_services", return_value=services), \
                patch.object(upgrade_services_module, "PropertiesChanges"), \
                patch.object(self.service, "get_upgrade_info", return_value=({}, {})), \
                patch.object(self.service, "get_or_create_upgrade_record",
                             return_value=created_record) as mock_get_or_create, \
                patch.object(self.service, "synchronous_upgrade_status"), \
                patch.object(upgrade_services_module.AppUpgradeRecord.objects, "get", return_value=created_record), \
                patch.object(upgrade_services_module.service_repo,
                             "get_services_by_service_ids_and_group_key", return_value=[]), \
                patch.object(self.service, "upgrade_database"), \
                patch.object(self.service, "send_upgrade_request"), \
                patch.object(upgrade_services_module.upgrade_repo, "change_app_record_status"):
            self.service.openapi_upgrade_app_models(
                user=MagicMock(), team=self.team, region_name="rainbond",
                oauth_instance=None, app_id="3199", data=data)

        return mock_get_or_create

    def test_uses_upgrade_group_id_from_request_when_provided(self):
        mock_get_or_create = self._run({
            "app_model_id": "model-1",
            "app_model_version": "1.14.4",
            "market_name": "market-1",
            "upgrade_group_id": 2867,
        })

        self.assertEqual(2867, mock_get_or_create.call_args.kwargs["upgrade_group_id"])

    def test_falls_back_to_component_group_id_when_request_omits_it(self):
        mock_get_or_create = self._run({
            "app_model_id": "model-1",
            "app_model_version": "1.14.4",
            "market_name": "market-1",
        })

        self.assertEqual(2878, mock_get_or_create.call_args.kwargs["upgrade_group_id"])
