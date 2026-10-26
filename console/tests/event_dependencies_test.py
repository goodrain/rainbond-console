# -*- coding: utf-8 -*-
# capability_id: console.events.batch-dependencies
import copy
import json
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.test import RequestFactory, SimpleTestCase  # noqa: E402

try:
    import openapi_client  # noqa: F401,E402
except ImportError:
    client = ModuleType("openapi_client")
    configuration = ModuleType("openapi_client.configuration")
    configuration.Configuration = type("Configuration", (), {"__init__": lambda self: None})
    rest = ModuleType("openapi_client.rest")
    rest.ApiException = type("ApiException", (Exception,), {})
    client.ApiClient = object
    client.MarketOpenapiApi = object
    stub_modules = {
            "openapi_client": client,
            "openapi_client.configuration": configuration,
            "openapi_client.rest": rest}
    sys.modules.update(stub_modules)
    try:
        from console.views import app_event as view_module
        from console.services.kubeblocks_service import kubeblocks_service
    finally:
        for module_name in stub_modules:
            sys.modules.pop(module_name, None)
else:
    from console.views import app_event as view_module
    from console.services.kubeblocks_service import kubeblocks_service

from www.models.main import TenantServiceInfo  # noqa: E402


class ServiceRows(list):
    def first(self):
        return self[0] if self else None

    def order_by(self, field):
        if field != "pk":
            raise AssertionError("Unexpected ordering: " + field)
        return ServiceRows(sorted(self, key=lambda row: row.pk))


class EventDependenciesTests(SimpleTestCase):
    def setUp(self):
        self.tenant = SimpleNamespace(tenant_id="tenant-a", tenant_name="team-a")
        self.service = self.component("app", "应用")
        self.services = [self.service, self.component("a", "组件A"), self.component("b", "组件B"),
                         self.component("foreign", "其他团队", tenant_id="tenant-b")]
        query_patch = mock.patch.object(TenantServiceInfo.objects, "filter", side_effect=self.filter_services)
        self.filter = query_patch.start()
        self.addCleanup(query_patch.stop)

    @staticmethod
    def component(alias, name, tenant_id="tenant-a"):
        return SimpleNamespace(service_alias=alias, service_cname=name, tenant_id=tenant_id,
                               service_id="id-" + alias, service_region="region-a", extend_method="stateless", pk=1)

    def filter_services(self, **kwargs):
        rows = self.services
        for key, value in kwargs.items():
            if key == "service_alias__in":
                rows = [row for row in rows if row.service_alias in value]
            else:
                rows = [row for row in rows if getattr(row, key) == value]
        return ServiceRows(rows)

    @staticmethod
    def event(index, message="a,b", opt_type="INITIATING"):
        return {"event_id": str(index), "opt_type": opt_type, "message": message,
                "create_time": "2026-10-20T10:00:{:02d}".format(index), "status": "failure"}

    def read_events(self, path, events):
        with mock.patch.object(view_module.event_service, "get_target_events",
                               return_value=(copy.deepcopy(events), len(events), False)), mock.patch.object(
                view_module.event_service, "merge_vm_restore_event", side_effect=lambda rows, *_: rows):
            if path == "ordinary":
                view = view_module.AppEventsView()
                view.tenant = self.tenant
                response = view.get(RequestFactory().get("/events", {"target": "service", "targetAlias": "app"}))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["code"], 200)
                self.assertEqual(response.data["data"]["total"], len(events))
                self.assertIs(response.data["data"]["has_next"], False)
                return response.data["data"]["list"]
            with mock.patch.object(kubeblocks_service, "get_cluster_events", return_value=([], 0, False)):
                result = kubeblocks_service.merge_region_and_kb_events(
                    "service", self.service.service_id, self.tenant, "region-a", self.service, 1, 6)
                self.assertEqual(result[1:], (len(events), False))
                return result[0]

    @staticmethod
    def dependencies(event):
        return json.loads(event["Message"].split(" ", 1)[1])

    def test_six_events_share_one_tenant_scoped_dependency_query(self):
        for path, expected_count in (("ordinary", 2), ("kb", 1)):
            with self.subTest(path=path):
                self.filter.reset_mock()
                rows = self.read_events(path, [self.event(index) for index in range(6)])
                self.assertEqual(self.filter.call_count, expected_count)
                dependency_query = self.filter.call_args.kwargs
                self.assertEqual(dependency_query["tenant_id"], self.tenant.tenant_id)
                self.assertEqual(set(dependency_query["service_alias__in"]), {"a", "b"})
                expected = [{"service_cname": "组件A", "serivce_alias": "a"},
                            {"service_cname": "组件B", "serivce_alias": "b"}]
                self.assertTrue(all(self.dependencies(row) == expected for row in rows))

    def test_dependencies_are_independent_per_event_and_keep_alias_order_and_duplicates(self):
        for path in ("ordinary", "kb"):
            with self.subTest(path=path):
                rows = self.read_events(path, [self.event(1, "b,a,b"), self.event(2, "a")])
                by_id = {row["event_id"]: row for row in rows}
                self.assertEqual([item["serivce_alias"] for item in self.dependencies(by_id["1"])], ["b", "a", "b"])
                self.assertEqual([item["serivce_alias"] for item in self.dependencies(by_id["2"])], ["a"])

    def test_missing_and_other_tenant_dependencies_are_skipped(self):
        for path in ("ordinary", "kb"):
            with self.subTest(path=path):
                rows = self.read_events(path, [self.event(1, "foreign,missing,a")])
                self.assertEqual(self.dependencies(rows[0]), [{"service_cname": "组件A", "serivce_alias": "a"}])

    def test_duplicate_database_alias_keeps_the_first_primary_key_record(self):
        duplicate = self.component("a", "later record")
        duplicate.pk = 99
        self.services.append(duplicate)
        for path in ("ordinary", "kb"):
            with self.subTest(path=path):
                rows = self.read_events(path, [self.event(1, "a")])
                self.assertEqual(self.dependencies(rows[0]), [{"service_cname": "组件A", "serivce_alias": "a"}])

    def test_no_initiating_events_make_no_dependency_query_or_response_changes(self):
        for path, count in (("ordinary", 1), ("kb", 0)):
            for events in ([], [self.event(1, opt_type="BUILD")]):
                with self.subTest(path=path, events=events):
                    self.filter.reset_mock()
                    self.assertEqual(self.read_events(path, events), events)
                    self.assertEqual(self.filter.call_count, count)

    def test_unresolved_dependencies_preserve_each_paths_existing_message_convention(self):
        for path in ("ordinary", "kb"):
            for message in (None, "", "missing,foreign"):
                with self.subTest(path=path, message=message):
                    event = self.event(1, message)
                    event["Message"] = "original"
                    rows = self.read_events(path, [event])
                    if path == "ordinary":
                        self.assertEqual(self.dependencies(rows[0]), [])
                    else:
                        self.assertEqual(rows[0], event)

    def test_non_dependency_fields_and_order_remain_unchanged(self):
        events = [self.event(1), self.event(2, opt_type="BUILD")]
        for path in ("ordinary", "kb"):
            with self.subTest(path=path):
                rows = self.read_events(path, events)
                expected_order = ["1", "2"] if path == "ordinary" else ["2", "1"]
                self.assertEqual([row["event_id"] for row in rows], expected_order)
                for row in rows:
                    original = next(event for event in events if event["event_id"] == row["event_id"])
                    self.assertEqual({key: value for key, value in row.items() if key != "Message"}, original)

    def test_kb_merge_formats_both_sources_after_sorting_and_pagination(self):
        region_events = [self.event(1, "hidden"), self.event(2, "a")]
        kb_events = [self.event(3, "b,a")]
        with mock.patch.object(view_module.event_service, "get_target_events", return_value=(region_events, 2, False)), \
                mock.patch.object(kubeblocks_service, "get_cluster_events", return_value=(kb_events, 1, False)):
            rows, total, has_next = kubeblocks_service.merge_region_and_kb_events(
                "service", self.service.service_id, self.tenant, "region-a", self.service, 1, 2)
        self.assertEqual([row["event_id"] for row in rows], ["3", "2"])
        self.assertEqual((total, has_next), (3, True))
        self.assertEqual([item["serivce_alias"] for item in self.dependencies(rows[0])], ["b", "a"])
        self.assertEqual([item["serivce_alias"] for item in self.dependencies(rows[1])], ["a"])
        self.filter.assert_called_once()
        self.assertEqual(set(self.filter.call_args.kwargs["service_alias__in"]), {"a", "b"})
