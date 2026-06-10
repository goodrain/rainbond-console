# -*- coding: utf-8 -*-
"""Tests that operate_app / upgrade_app surface operation event ids.

Returning event ids lets rainagent correlate a later failure event (via
get_operation_failure_context) back to the exact operation it triggered,
instead of guessing.
"""
import os
import sys
from types import ModuleType
from unittest.mock import patch

import django
from django.test import SimpleTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")
django.setup()

from console.services.mcp_query_service import mcp_query_service


class Obj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _team():
    return Obj(tenant_name="team1", tenant_id="tid-1", enterprise_id="eid-1")


def _app():
    return Obj(ID=7, region_name="rg")


class OperateAppEventIdsTests(SimpleTestCase):

    # capability_id: console.mcp.operation-event-ids
    def test_operate_app_returns_event_ids_mapped_to_alias(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "action": "start", "service_ids": ["svc-1", "svc-2"]}
        batch_result = [
            {"service_id": "svc-1", "operation": "start", "event_id": "ev-1", "status": "success"},
            {"service_id": "svc-2", "operation": "start", "event_id": "ev-2", "status": "success"},
        ]
        services = [Obj(service_id="svc-1", service_alias="gr-aaa"),
                    Obj(service_id="svc-2", service_alias="gr-bbb")]
        with patch.object(mcp_query_service, "_get_team_app_context", return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.app_manage_service.batch_operations",
                       return_value=batch_result):
                with patch("console.services.mcp_query_service.service_repo.get_services_by_service_ids",
                           return_value=services):
                    result = mcp_query_service.operate_app(Obj(nick_name="t"), args)

        self.assertIn("event_ids", result)
        mapping = {e["service_alias"]: e["event_id"] for e in result["event_ids"]}
        self.assertEqual(mapping, {"gr-aaa": "ev-1", "gr-bbb": "ev-2"})
        # existing fields preserved
        self.assertEqual(result["action"], "start")
        self.assertEqual(result["service_ids"], ["svc-1", "svc-2"])

    # capability_id: console.mcp.operation-event-ids
    def test_operate_app_restart_returns_empty_event_ids(self):
        # The restart path returns serialized services (no per-component event_id);
        # event_ids must still be present (empty) so the field is stable.
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "action": "restart", "service_ids": ["svc-1"]}
        services = [Obj(service_id="svc-1", service_alias="gr-aaa", to_dict=lambda: {"service_id": "svc-1"})]
        with patch.object(mcp_query_service, "_get_team_app_context", return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.app_manage_service.batch_action",
                       return_value=(200, "ok", services)):
                result = mcp_query_service.operate_app(Obj(nick_name="t"), args)
        self.assertEqual(result["event_ids"], [])

    # capability_id: console.mcp.operation-event-ids
    def test_operate_app_skips_entries_without_event_id(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "action": "stop", "service_ids": ["svc-1", "svc-2"]}
        batch_result = [
            {"service_id": "svc-1", "operation": "stop", "event_id": "ev-1"},
            {"service_id": "svc-2", "operation": "stop", "event_id": ""},
        ]
        services = [Obj(service_id="svc-1", service_alias="gr-aaa"),
                    Obj(service_id="svc-2", service_alias="gr-bbb")]
        with patch.object(mcp_query_service, "_get_team_app_context", return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.app_manage_service.batch_operations",
                       return_value=batch_result):
                with patch("console.services.mcp_query_service.service_repo.get_services_by_service_ids",
                           return_value=services):
                    result = mcp_query_service.operate_app(Obj(nick_name="t"), args)
        self.assertEqual([e["event_id"] for e in result["event_ids"]], ["ev-1"])


class UpgradeAppEventIdsTests(SimpleTestCase):

    # capability_id: console.mcp.operation-event-ids
    def test_upgrade_app_returns_event_ids_from_records(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "update_versions": [{"app_model_id": "m1", "app_model_version": "2.0", "market_name": ""}]}

        record_a = Obj(service=Obj(service_alias="gr-aaa"), event_id="up-ev-1")
        record_b = Obj(service=Obj(service_alias="gr-bbb"), event_id="up-ev-2")
        app_record = Obj(service_upgrade_records=_Manager([record_a, record_b]))

        with patch.object(mcp_query_service, "_get_team_app_context", return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.upgrade_service.openapi_upgrade_app_models",
                       return_value=[app_record]) as mock_upgrade:
                with patch("console.services.mcp_query_service.market_app_service.get_market_apps_in_app",
                           return_value=[]):
                    result = mcp_query_service.upgrade_app(Obj(nick_name="t"), args)

        self.assertTrue(mock_upgrade.called)
        self.assertTrue(result["upgraded"])
        mapping = {e["service_alias"]: e["event_id"] for e in result["event_ids"]}
        self.assertEqual(mapping, {"gr-aaa": "up-ev-1", "gr-bbb": "up-ev-2"})

    # capability_id: console.mcp.operation-event-ids
    def test_upgrade_app_tolerates_no_records(self):
        args = {"team_name": "team1", "region_name": "rg", "app_id": "7",
                "update_versions": [{"app_model_id": "m1", "app_model_version": "2.0", "market_name": ""}]}
        with patch.object(mcp_query_service, "_get_team_app_context", return_value=(_team(), _app())):
            with patch("console.services.mcp_query_service.upgrade_service.openapi_upgrade_app_models",
                       return_value=None):
                with patch("console.services.mcp_query_service.market_app_service.get_market_apps_in_app",
                           return_value=[]):
                    result = mcp_query_service.upgrade_app(Obj(nick_name="t"), args)
        self.assertEqual(result["event_ids"], [])
        self.assertTrue(result["upgraded"])


class _Manager(object):
    """Minimal stand-in for a Django related manager (`.all()`)."""

    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)
