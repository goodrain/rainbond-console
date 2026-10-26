# capability_id: console.platform-overview.absolute-metrics
from unittest import TestCase, mock
from urllib.parse import parse_qs

from console.tests.platform_overview_service_test import MemoryCache, PlatformOverviewService


def measurement(stat, values):
    return {"metric": {"overview_stat": stat}, "values": values}


class AbsoluteMetricsTest(TestCase):
    def test_invalid_role_metadata_preserves_valid_percent(self):
        for role in ([], {}):
            result, _ = self.query([measurement("percent", [[1, "20"]]), measurement(role, [[1, "8"]])])
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["series"][0]["values"], [[1, "20"]])
            self.assertEqual(result["absolute"]["samples"], [])

    def query(self, rows, metric="cpu"):
        api = mock.Mock()
        api.get_query_range_data.return_value = ({"status": 200}, {"status": "success", "data": {"result": rows}})
        service = PlatformOverviewService(cache_backend=MemoryCache(), region_api=api)
        service._metric_tenant_name = mock.Mock(return_value="team")
        result = service._query_metrics("eid", "region", metric, "1h")
        return result, api

    def test_historical_expansion_keeps_exact_capacities(self):
        result, api = self.query([
            measurement("percent", [[1, "20"], [2, "25"]]),
            measurement("used", [[1, "1.6"], [2, "4"]]),
            measurement("capacity", [[1, "8"], [2, "16"]])
        ])
        self.assertEqual(result["absolute"], {
            "unit": "cores",
            "samples": [{
                "timestamp": 1,
                "used": 1.6,
                "capacity": 8
            }, {
                "timestamp": 2,
                "used": 4,
                "capacity": 16
            }]
        })
        self.assertEqual(api.get_query_range_data.call_count, 1)

    def test_invalid_absolute_points_preserve_percent(self):
        for used, capacity in (("NaN", "8"), ("Inf", "8"), ("-1", "8"), (True, "8"), ("2", "0"), ("2", "8")):
            with self.subTest(used=used, capacity=capacity):
                result, _ = self.query([
                    measurement("percent", [[1, "20"]]),
                    measurement("used", [[1, used]]),
                    measurement("capacity", [[1, capacity]])
                ])
                self.assertEqual(result["absolute"]["samples"], [])
                self.assertEqual(len(result["series"]), 1)

    def test_mismatched_and_duplicate_timestamps_are_not_paired(self):
        for used in ([[2, "1.6"]], [[1, "1.6"], [1, "1.7"]]):
            result, _ = self.query(
                [measurement("percent", [[1, "20"]]),
                 measurement("used", used),
                 measurement("capacity", [[1, "8"]])])
            self.assertEqual(result["absolute"]["samples"], [])

    def test_invalid_timestamp_and_missing_values_do_not_break_percent(self):
        cases = [None, [[True, "1.6"]], [["NaN", "1.6"]], [[-1, "1.6"]], [[1, None]], [[1]], ["bad"], [[1, "1.6"], [1, "NaN"]]]
        for points in cases:
            result, _ = self.query(
                [measurement("percent", [[1, "20"]]),
                 measurement("used", points),
                 measurement("capacity", [[1, "8"]])])
            self.assertEqual(result["absolute"]["samples"], [])
            self.assertEqual(result["status"], "ok")

    def test_zero_is_real_and_memory_uses_bytes(self):
        result, _ = self.query(
            [measurement("percent", [[1, "0"]]),
             measurement("used", [[1, "0"]]),
             measurement("capacity", [[1, "1024"]])], "memory")
        self.assertEqual(result["absolute"], {"unit": "bytes", "samples": [{"timestamp": 1, "used": 0, "capacity": 1024}]})

    def test_legacy_and_network_keep_original_series(self):
        for metric in ("cpu", "network"):
            rows = [{"metric": {}, "values": [[1, "20"]]}]
            result, _ = self.query(rows, metric)
            self.assertEqual(result["series"], rows)
            self.assertNotIn("absolute", result)

    def test_duplicate_roles_and_missing_capacity_fail_closed(self):
        for extra in ([], [measurement("used", [[1, "1.6"]])]):
            rows = [measurement("percent", [[1, "20"]]), measurement("used", [[1, "1.6"]])] + extra
            result, _ = self.query(rows)
            self.assertEqual(result["absolute"]["samples"], [])

    def test_fallback_never_combines_primary_absolute_with_other_source(self):
        api = mock.Mock()
        primary = [measurement("used", [[1, "2"]])]
        fallback = [measurement("percent", [[1, "25"]]), measurement("capacity", [[1, "8"]])]
        api.get_query_range_data.side_effect = [
            ({"status": 200}, {"status": "success", "data": {"result": primary}}),
            ({"status": 200}, {"status": "success", "data": {"result": fallback}}),
        ]
        service = PlatformOverviewService(cache_backend=MemoryCache(), region_api=api)
        service._metric_tenant_name = mock.Mock(return_value="team")
        result = service._query_metrics("eid", "region", "memory", "1h")
        self.assertEqual(result["source"], "cadvisor_root")
        self.assertEqual(result["semantics"], "host_memory_working_set")
        self.assertEqual(result["absolute"]["samples"], [])
        self.assertEqual(api.get_query_range_data.call_count, 2)

    def test_cadvisor_returns_working_set_bytes_from_same_historical_query(self):
        api = mock.Mock()
        fallback = [measurement("percent", [[1, "25"]]), measurement("used", [[1, "1024"]]),
                    measurement("capacity", [[1, "4096"]])]
        api.get_query_range_data.side_effect = [
            ({"status": 200}, {"status": "success", "data": {"result": []}}),
            ({"status": 200}, {"status": "success", "data": {"result": fallback}}),
        ]
        service = PlatformOverviewService(cache_backend=MemoryCache(), region_api=api)
        service._metric_tenant_name = mock.Mock(return_value="team")
        result = service._query_metrics("eid", "region", "memory", "1h")
        self.assertEqual(result["absolute"], {"unit": "bytes", "samples": [
            {"timestamp": 1, "used": 1024, "capacity": 4096}]})
        query = parse_qs(api.get_query_range_data.call_args.args[2].lstrip("?"))["query"][0]
        self.assertIn("container_memory_working_set_bytes", query)
        self.assertNotIn("node_memory", query)

    def test_primary_percent_without_details_does_not_force_fallback(self):
        result, api = self.query([measurement("percent", [[1, "20"]])])
        self.assertEqual(result["source"], "node_exporter")
        self.assertEqual(result["absolute"]["samples"], [])
        self.assertEqual(api.get_query_range_data.call_count, 1)

    def test_queries_bundle_three_roles_and_guard_identity(self):
        for metric in ("cpu", "memory"):
            for source in ("node_exporter", "cadvisor_root"):
                query = PlatformOverviewService._metric_bundle_query(metric, source)
                self.assertEqual(query.count('"overview_stat"'), 3)
                if source == "node_exporter":
                    self.assertIn("count by (instance", query)
                    self.assertIn('instance!=""', query)
                else:
                    self.assertIn('id="/"', query)
                    self.assertIn('pod=""', query)
                    self.assertIn('namespace=""', query)
                    self.assertIn(" and on () ", query)
                    if metric == "memory":
                        self.assertIn("container_memory_working_set_bytes", query)
        self.assertEqual(PlatformOverviewService._metric_bundle_query("network", "node_exporter"),
                         PlatformOverviewService.METRIC_QUERIES["network"])

    def test_query_is_one_request_and_keeps_timeouts(self):
        _, api = self.query([measurement("percent", [[1, "20"]])])
        args, kwargs = api.get_query_range_data.call_args
        query = parse_qs(args[2].lstrip("?"))["query"][0]
        self.assertIn('"overview_stat", "used"', query)
        self.assertEqual(kwargs["retries"], 0)
        self.assertLessEqual(kwargs["connect_timeout"] + kwargs["timeout"], 5)

    def test_payload_serializes_in_drf_envelope(self):
        import json
        from rest_framework.renderers import JSONRenderer
        from console.tests.platform_overview_view_test import PlatformOverviewViewTest, PlatformOverviewMetricsView

        result, _ = self.query(
            [measurement("percent", [[1, "20"]]),
             measurement("used", [[1, "1.6"]]),
             measurement("capacity", [[1, "8"]])])
        case = PlatformOverviewViewTest()
        case.setUp()
        with mock.patch("console.views.platform_overview.platform_overview_service.get_metrics", return_value=result):
            response = case._get(PlatformOverviewMetricsView,
                                 "/console/enterprise/eid/regions/r/platform-overview/metrics",
                                 region_name="r",
                                 query={
                                     "metric": "cpu",
                                     "range": "1h"
                                 })
        rendered = json.loads(JSONRenderer().render(response.data))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(rendered["data"]["bean"]["absolute"], result["absolute"])
