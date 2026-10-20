# -*- coding: utf-8 -*-
# capability_id: console.region-api.polling-deadlines
import os
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import RequestFactory, SimpleTestCase  # noqa: E402
from rest_framework.request import Request  # noqa: E402

from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


try:
    import openapi_client  # noqa: F401,E402
except ImportError:
    openapi_client = ModuleType("openapi_client")
    configuration = ModuleType("openapi_client.configuration")
    configuration.Configuration = type("Configuration", (), {"__init__": lambda self: None})
    rest = ModuleType("openapi_client.rest")
    rest.ApiException = type("ApiException", (Exception,), {})
    openapi_client.ApiClient = object
    openapi_client.MarketOpenapiApi = object
    _stub_modules = {
        "openapi_client": openapi_client,
        "openapi_client.configuration": configuration,
        "openapi_client.rest": rest,
    }
    sys.modules.update(_stub_modules)
    try:
        from console.services import kubeblocks_service as kb_module
        from console.views import app_overview as overview_module
    finally:
        for _name in _stub_modules:
            sys.modules.pop(_name, None)
else:
    from console.services import kubeblocks_service as kb_module
    from console.views import app_overview as overview_module


class PollingDeadlineTestCase(SimpleTestCase):

    def setUp(self):
        self.client = RegionInvokeApi()
        self.access = mock.patch.object(
            self.client,
            "_RegionInvokeApi__get_region_access_info",
            return_value=("https://region.example", "region-token"),
        )
        self.tenant_region = mock.patch.object(
            self.client,
            "_RegionInvokeApi__get_tenant_region_info",
            return_value=SimpleNamespace(region_tenant_name="tenant-a"),
        )
        self.access.start()
        self.tenant_region.start()
        self.addCleanup(self.access.stop)
        self.addCleanup(self.tenant_region.stop)

    def assert_polling_deadline(self, request, read_timeout):
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["connect_timeout"], 3)
        self.assertEqual(kwargs["timeout"], read_timeout)
        self.assertEqual(kwargs["retries"], 0)

    def assert_legacy_deadline(self, request, read_timeout=None):
        kwargs = request.call_args.kwargs
        self.assertNotIn("connect_timeout", kwargs)
        self.assertNotIn("retries", kwargs)
        if read_timeout is None:
            self.assertNotIn("timeout", kwargs)
        else:
            self.assertEqual(kwargs["timeout"], read_timeout)


class RegionApiPollingDeadlineTests(PollingDeadlineTestCase):

    def test_default_calls_preserve_legacy_deadlines(self):
        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"bean": {}})) as request:
            self.client.check_service_status("region-a", "team-a", "component-a", "enterprise-a")
        self.assert_legacy_deadline(request)

        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": []})) as request:
            self.client.get_service_pods("region-a", "team-a", "component-a", "enterprise-a")
        self.assert_legacy_deadline(request, 15)

        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": []})) as request:
            self.client.get_target_events_list("region-a", "team-a", "service", "service-id", 1, 6)
        self.assert_legacy_deadline(request, 20)

    def test_polling_calls_use_bounded_deadlines(self):
        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"bean": {}})) as request:
            self.client.check_service_status("region-a", "team-a", "component-a", "enterprise-a", polling=True)
        self.assert_polling_deadline(request, 5)

        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": []})) as request:
            self.client.get_service_pods("region-a", "team-a", "component-a", "enterprise-a", polling=True)
        self.assert_polling_deadline(request, 8)

        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": []})) as request:
            self.client.get_target_events_list("region-a", "team-a", "service", "service-id", 1, 6, polling=True)
        self.assert_polling_deadline(request, 8)

    def test_http_polling_entrypoints_enable_bounded_deadlines(self):
        repo_root = Path(__file__).resolve().parents[2]
        overview_source = (repo_root / "console/views/app_overview.py").read_text()
        event_view_source = (repo_root / "console/views/app_event.py").read_text()
        app_service_source = (repo_root / "console/services/app.py").read_text()
        event_service_source = (repo_root / "console/services/app_actions/app_log.py").read_text()
        kubeblocks_source = (repo_root / "console/services/kubeblocks_service.py").read_text()

        self.assertRegex(
            overview_source,
            r"get_service_status\(self\.tenant, self\.service, polling=True\)",
        )
        self.assertRegex(
            overview_source,
            r"get_service_pods\([\s\S]{0,250}?polling=True\)",
        )
        self.assertGreaterEqual(len(re.findall(r"polling=True", event_view_source)), 4)
        self.assertIn("polling=polling", app_service_source)
        self.assertIn("polling=polling", event_service_source)
        self.assertIn("polling=polling", kubeblocks_source)


class KubeBlocksPollingFlowTests(PollingDeadlineTestCase):

    def setUp(self):
        super().setUp()
        self.region_info = mock.patch.object(
            self.client, "get_region_info", return_value=SimpleNamespace(url="https://region.example", token=""))
        self.region_info.start()
        self.addCleanup(self.region_info.stop)
        self.kb_api = mock.patch.object(kb_module, "region_api", self.client)
        self.kb_api.start()
        self.addCleanup(self.kb_api.stop)
        self.sync = mock.patch.object(kb_module.kubeblocks_service, "_sync_to_rainbond")
        self.sync.start()
        self.addCleanup(self.sync.stop)
        self.tenant = SimpleNamespace(tenant_name="team-a", tenant_id="tenant-id", enterprise_id="enterprise-a")
        self.service = SimpleNamespace(
            service_region="region-a", service_id="component-a", service_alias="alias-a",
            check_uuid="check-a", extend_method="kubeblocks_component")

    def test_kb_detail_view_only_enables_polling_for_explicit_true(self):
        from console.views.kubeblocks import KubeBlocksClusterDetailView

        bean = {"basic": {"status": "Running"}}
        for value in (None, "false", "true", "1", "invalid"):
            with self.subTest(polling=value), mock.patch.object(
                    self.client, "_get", return_value=({"status": 200}, {"bean": bean})) as request, mock.patch.object(
                    kb_module.kubeblocks_service, "get_cluster_detail",
                    wraps=kb_module.kubeblocks_service.get_cluster_detail) as detail:
                view = KubeBlocksClusterDetailView()
                view.service = self.service
                view.response_region = "region-a"
                query = {} if value is None else {"polling": value}
                response = view.get(Request(RequestFactory().get("/kubeblocks/detail", query)))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, {
                    "code": 200, "msg": "查询成功", "msg_show": "查询成功", "data": {"bean": bean, "list": []}})
                if value == "true":
                    detail.assert_called_once_with("region-a", "component-a", polling=True)
                    self.assert_polling_deadline(request, 5)
                else:
                    detail.assert_called_once_with("region-a", "component-a")
                    self.assert_legacy_deadline(request)

    def test_kb_detail_client_preserves_defaults_and_uses_polling_deadline(self):
        response = ({"status": 200}, {"bean": {"basic": {}}})
        for polling in (False, True):
            with self.subTest(polling=polling), mock.patch.object(self.client, "_get", return_value=response) as request:
                options = {"polling": True} if polling else {}
                result = self.client.get_kubeblocks_cluster_detail("region-a", "component-a", **options)
                self.assertEqual(result, response)
                self.assertEqual(request.call_args.args[0], "https://region.example/v2/cluster/kubeblocks/clusters/component-a")
                if polling:
                    self.assert_polling_deadline(request, 5)
                else:
                    self.assert_legacy_deadline(request)

    def test_kb_status_service_passes_polling_budget_to_real_client(self):
        bean = {"basic": {"status": {"status": "Running", "start_time": "started"}}}
        for polling in (False, True):
            with self.subTest(polling=polling), mock.patch.object(
                    self.client, "_get", return_value=({"status": 200}, {"bean": bean})) as request:
                options = {"polling": True} if polling else {}
                result = kb_module.kubeblocks_service.get_kubeblocks_service_status("region-a", "component-a", **options)
                self.assertEqual(result["status"], "running")
                self.assertEqual(result["start_time"], "started")
                if polling:
                    self.assert_polling_deadline(request, 5)
                else:
                    self.assert_legacy_deadline(request)

    def test_kb_status_with_supplied_detail_does_not_make_another_request(self):
        with mock.patch.object(self.client, "_get") as request:
            result = kb_module.kubeblocks_service.get_kubeblocks_service_status(
                "region-a", "component-a", cluster_detail={"basic": {"status": "Running"}}, polling=True)
        self.assertEqual(result["status"], "running")
        request.assert_not_called()

    def test_kb_events_default_budget_and_response_remain_unchanged(self):
        event = {"event_id": "kb-event", "message": "created"}
        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": [event], "number": 2})) as request:
            events, total, has_next = kb_module.kubeblocks_service.get_cluster_events(
                "region-a", "component-a", self.tenant, self.service, 1, 1)
        self.assert_legacy_deadline(request)
        self.assertEqual((total, has_next), (2, True))
        self.assertEqual(events[0]["event_id"], "kb-event")
        self.assertEqual(events[0]["target_id"], "component-a")

    def test_kb_event_merge_passes_polling_budget_to_both_real_clients(self):
        from console.services.app_actions import app_log

        for polling in (False, True):
            with self.subTest(polling=polling), mock.patch.object(app_log, "region_api", self.client), mock.patch.object(
                    self.client, "_get", side_effect=[
                        (SimpleNamespace(status=200), {
                            "list": [{"event_id": "region-event", "create_time": "2026-01-02"}], "number": 1}),
                        ({"status": 200}, {"list": [{"event_id": "kb-event", "create_time": "2026-01-01"}], "number": 1}),
                    ]) as request:
                result = kb_module.kubeblocks_service.merge_region_and_kb_events(
                    "service", "component-a", self.tenant, "region-a", self.service, 1, 6, polling=polling)
                self.assertEqual([event["event_id"] for event in result[0]], ["region-event", "kb-event"])
                self.assertEqual(result[1:], (2, False))
                self.assertEqual(request.call_count, 2)
                self.assertTrue(request.call_args_list[1].args[0].endswith("component-a/events?page=1&page_size=6"))
                for call in request.call_args_list:
                    if polling:
                        self.assertEqual({key: call.kwargs[key] for key in ("connect_timeout", "timeout", "retries")},
                                         {"connect_timeout": 3, "timeout": 8, "retries": 0})
                    else:
                        self.assertNotIn("retries", call.kwargs)
                        self.assertNotIn("connect_timeout", call.kwargs)
                if not polling:
                    self.assertEqual(request.call_args_list[0].kwargs["timeout"], 20)
                    self.assertNotIn("timeout", request.call_args_list[1].kwargs)

    def test_kb_failures_keep_existing_status_and_event_fallbacks(self):
        for response in (({"status": 503}, {"msg_show": "unavailable"}), RuntimeError("upstream unavailable")):
            options = {"side_effect": response} if isinstance(response, Exception) else {"return_value": response}
            with self.subTest(response=response), mock.patch.object(self.client, "_get", **options) as request:
                self.assertIsNone(kb_module.kubeblocks_service.get_kubeblocks_service_status(
                    "region-a", "component-a", polling=True))
                self.assert_polling_deadline(request, 5)
                self.assertEqual(kb_module.kubeblocks_service.get_cluster_events(
                    "region-a", "component-a", self.tenant, self.service, 1, 6, polling=True), ([], 0, False))
                self.assert_polling_deadline(request, 8)

    def call_status_view(self):
        view = overview_module.AppStatusView()
        view.tenant = self.tenant
        view.service = self.service
        with mock.patch.object(overview_module.platform_first_app_service, "safe_mark_if_running"):
            response = view.get(RequestFactory().get("/status"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        return response.data["data"]

    def test_status_view_uses_kb_polling_and_skips_duplicate_generic_read(self):
        with mock.patch.object(self.client, "_get", return_value=(
                {"status": 200}, {"bean": {"basic": {"status": "Running"}}})) as request, mock.patch.object(
                overview_module.app_service, "get_service_status") as generic:
            result = self.call_status_view()
        self.assertEqual(result["bean"]["status"], "running")
        self.assertEqual(result["bean"]["check_uuid"], "check-a")
        self.assertEqual(request.call_count, 1)
        self.assert_polling_deadline(request, 5)
        generic.assert_not_called()

    def test_status_view_falls_back_when_kb_detail_or_status_is_missing(self):
        for response in (({"status": 503}, {}), ({"status": 200}, {"bean": {}})):
            with self.subTest(response=response), mock.patch.object(
                    self.client, "_get", return_value=response), mock.patch.object(
                    overview_module.app_service, "get_service_status", return_value={"status": "unKnow"}) as generic:
                result = self.call_status_view()
            self.assertEqual(result["bean"]["status"], "unKnow")
            generic.assert_called_once_with(self.tenant, self.service, polling=True)

    def test_status_fallback_queries_kb_then_generic_with_bounded_budgets(self):
        from console.services import app as app_module

        for unavailable in (({"status": 503}, {}), RuntimeError("upstream unavailable")):
            with self.subTest(unavailable=unavailable), mock.patch.object(
                    app_module, "region_api", self.client), mock.patch.object(
                    self.client, "_get", side_effect=[
                        unavailable,
                        ({"status": 200}, {"bean": {"cur_status": "running", "start_time": "started"}}),
                    ]) as request:
                result = self.call_status_view()
            self.assertEqual(result["bean"]["status"], "running")
            self.assertEqual(result["bean"]["start_time"], "started")
            self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args_list[0].args[0],
                             "https://region.example/v2/cluster/kubeblocks/clusters/component-a")
            self.assertIn("/services/alias-a/status?", request.call_args_list[1].args[0])
            for call in request.call_args_list:
                self.assertEqual({key: call.kwargs[key] for key in ("connect_timeout", "timeout", "retries")},
                                 {"connect_timeout": 3, "timeout": 5, "retries": 0})

    def test_status_view_preserves_kb_unknown_mapping_without_generic_read(self):
        with mock.patch.object(self.client, "_get", return_value=(
                {"status": 200}, {"bean": {"basic": {"status": "UnrecognizedPhase"}}})), mock.patch.object(
                overview_module.app_service, "get_service_status") as generic:
            result = self.call_status_view()
        self.assertEqual(result["bean"]["status"], "unKnow")
        generic.assert_not_called()

    def test_non_kb_status_view_keeps_generic_polling_path(self):
        self.service.extend_method = "stateless"
        with mock.patch.object(kb_module.kubeblocks_service, "get_kubeblocks_service_status") as kb_status, mock.patch.object(
                overview_module.app_service, "get_service_status", return_value={"status": "running"}) as generic:
            result = self.call_status_view()
        self.assertEqual(result["bean"]["status"], "running")
        generic.assert_called_once_with(self.tenant, self.service, polling=True)
        kb_status.assert_not_called()
