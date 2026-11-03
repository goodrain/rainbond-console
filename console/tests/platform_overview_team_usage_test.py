# capability_id: console.platform-overview.team-usage
from unittest import TestCase, mock
from urllib.parse import parse_qs

from console.tests.platform_overview_service_test import MemoryCache, PlatformOverviewService, overview_module


class PlatformOverviewTeamUsageTest(TestCase):
    def setUp(self):
        self.api = mock.Mock()
        self.service = PlatformOverviewService(cache_backend=MemoryCache(), region_api=self.api)
        self.teams = [{"tenant_id": "t1", "tenant_name": "dev", "tenant_alias": "Development", "namespace": "dev-ns"},
                      {"tenant_id": "t2", "tenant_name": "prod", "tenant_alias": "Production", "namespace": "prod-ns"}]
        self.sampled_at = 1800000000

    def point(self, namespace, metric, value):
        return {"metric": {"namespace": namespace, "team_metric": metric}, "values": [[self.sampled_at, value]]}

    def fetch(self, rows):
        self.api.get_query_range_data.return_value = ({"status": 200}, {"status": "success", "data": {"result": rows}})
        memberships = mock.Mock(return_value=["t1", "t2"])
        teams = mock.Mock()
        teams.values.return_value = self.teams
        groups = mock.Mock()
        groups.values.return_value.annotate.return_value = [
            {"tenant_id": "t1", "total": 30}, {"tenant_id": "t2", "total": 15}
        ]
        with mock.patch.object(self.service, "_tenant_ids", memberships), \
                mock.patch.object(overview_module.Tenants.objects, "filter", return_value=teams) as team_filter, \
                mock.patch.object(overview_module.ServiceGroup.objects, "filter", return_value=groups) as group_filter, \
                mock.patch.object(overview_module.TenantServiceInfo.objects, "filter") as configured, \
                mock.patch.object(overview_module.timezone, "now") as now:
            now.return_value.timestamp.return_value = self.sampled_at
            result = self.service._fetch_team_ranking("enterprise", "region")
        memberships.assert_called_once_with("enterprise", "region")
        team_filter.assert_called_once_with(tenant_id__in=["t1", "t2"])
        group_filter.assert_called_once_with(tenant_id__in=["t1", "t2"], region_name="region")
        configured.assert_not_called()
        return result

    def test_reads_actual_usage_in_one_scoped_query_with_shared_sample_time(self):
        result = self.fetch([self.point("dev-ns", "memory", str(44.1 * 1024**3)),
                             self.point("prod-ns", "memory", str(10 * 1024**3)),
                             self.point("dev-ns", "cpu", "0.866"), self.point("prod-ns", "cpu", "0.1")])
        self.assertEqual("actual_usage", result["scope"])
        self.assertFalse(result["includes_inactive_components"])
        self.assertAlmostEqual(44.1, result["memory"][0]["memory_gib"])
        self.assertEqual(0.866, result["cpu"][0]["cpu_cores"])
        self.assertEqual(45, result["totals"]["applications"])
        self.assertEqual({"cpu": "ok", "memory": "ok"}, result["metric_status"])
        self.assertIsNotNone(result["sampled_at"])
        self.api.get_query_range_data.assert_called_once()
        args, kwargs = self.api.get_query_range_data.call_args
        params = parse_qs(args[2].lstrip("?"))
        self.assertEqual([str(self.sampled_at)], params["start"])
        self.assertEqual(params["start"], params["end"])
        self.assertEqual(("region", ""), args[:2])
        self.assertEqual(0, kwargs["retries"])
        self.assertLessEqual(kwargs["timeout"] + kwargs["connect_timeout"], 5)
        query = params["query"][0]
        for required in ('namespace=~"dev\\-ns|prod\\-ns"', 'container!="POD"', 'container!=""',
                         'container_memory_working_set_bytes', 'rate(', '[5m]', 'max by (namespace,pod,container)',
                         'min(up{job="cadvisor"}) == 1', 'timestamp(', '<= 120'):
            # PromQL string literals double the regex backslash.
            self.assertIn(required.replace('\\-', '\\\\-'), query)

    def test_missing_metric_stays_unknown_and_observed_zero_stays_zero(self):
        result = self.fetch([self.point("dev-ns", "memory", "0"), self.point("prod-ns", "cpu", "0")])
        self.assertEqual("partial", result["metric_status"]["memory"])
        self.assertEqual(0, result["memory"][0]["memory_gib"])
        self.assertIsNone(result["memory"][1]["memory_gib"])
        self.assertEqual(0, result["cpu"][0]["cpu_cores"])
        self.assertIsNone(result["totals"]["memory_gib"])

    def test_timeout_preserves_application_ranking_and_never_substitutes_configuration(self):
        self.api.get_query_range_data.side_effect = TimeoutError()
        result = self.fetch([])
        self.assertEqual("unavailable", result["metric_status"]["memory"])
        self.assertIsNone(result["sampled_at"])
        self.assertEqual([30, 15], [item["applications"] for item in result["applications"]])
        self.assertTrue(all(item["memory_gib"] is None for item in result["memory"]))

    def test_duplicate_invalid_stale_and_foreign_series_are_not_trusted(self):
        for bad_value in ("NaN", "Inf", "-1", True, None):
            with self.subTest(bad_value=bad_value):
                result = self.fetch([self.point("dev-ns", "memory", bad_value)])
                self.assertIsNone(result["memory"][0]["memory_gib"])
        for rows in ([self.point("dev-ns", "memory", "5"), self.point("dev-ns", "memory", "6")],
                     [{"metric": {"namespace": "dev-ns", "team_metric": "memory"},
                       "values": [[self.sampled_at - 60, "5"]]}],
                     [self.point("other-enterprise", "memory", "9")],
                     [{"metric": [], "values": []}]):
            with self.subTest(rows=rows):
                result = self.fetch(rows)
                self.assertEqual("unavailable", result["metric_status"]["memory"])
                self.assertIsNone(result["sampled_at"])

    def test_empty_or_malformed_monitor_response_remains_unknown(self):
        for body in (None, {"status": "error"}, {"status": "success", "data": {"result": {}}}):
            self.api.get_query_range_data.side_effect = lambda *_args, **_kwargs: ({"status": 200}, body)
            result = self.fetch([])
            self.assertEqual("unavailable", result["metric_status"]["cpu"])
        self.api.get_query_range_data.side_effect = None
        self.assertEqual("unavailable", self.fetch([])["metric_status"]["memory"])

    def test_missing_namespace_does_not_issue_a_broad_query(self):
        for team in self.teams:
            team["namespace"] = ""
        result = self.fetch([])
        self.api.get_query_range_data.assert_not_called()
        self.assertEqual("unavailable", result["metric_status"]["memory"])

    def test_no_initialized_teams_does_not_query_monitor(self):
        self.service._tenant_ids = mock.Mock(return_value=[])
        result = self.service._fetch_team_ranking("enterprise", "region")
        self.assertEqual([], result["memory"])
        self.assertEqual(0, result["totals"]["applications"])
        self.api.get_query_range_data.assert_not_called()

    def test_totals_include_teams_outside_top_five(self):
        teams = [{"tenant_id": str(i), "tenant_name": str(i), "tenant_alias": str(i)} for i in range(6)]
        resources = [{"tenant_id": str(i), "cpu_cores": i, "memory_gib": i} for i in range(6)]
        result = self.service._build_team_rankings(teams, resources, [])
        self.assertEqual(15, result["totals"]["cpu_cores"])
        self.assertEqual([5, 4, 3, 2, 1], [item["cpu_cores"] for item in result["cpu"]])

    def test_namespace_regex_is_literal_and_promql_escaped(self):
        query = self.service._team_usage_query({'team.a', 'team"b'})
        self.assertIn('team\\\\.a', query)
        self.assertIn('team\\"b', query)
