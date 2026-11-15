# capability_id: console.platform-overview.team-usage-compatibility
from unittest import TestCase, mock

from console.tests.platform_overview_service_test import MemoryCache, PlatformOverviewService


class PlatformOverviewTeamUsageCompatibilityTests(TestCase):
    def test_main_configured_units_and_actual_unknowns_keep_their_distinct_meaning(self):
        service = PlatformOverviewService(cache_backend=MemoryCache(), region_api=mock.Mock())
        teams = [{'tenant_id': 'a', 'tenant_name': 'team-a', 'tenant_alias': 'Team A'}]
        configured = service._build_team_rankings(teams, [{'tenant_id': 'a', 'cpu_millicores': 3500, 'memory_mib': 5120}], [])
        self.assertEqual(configured['scope'], 'configured_resources')
        self.assertEqual(configured['cpu'][0]['cpu_cores'], 3.5)
        self.assertEqual(configured['memory'][0]['memory_gib'], 5)
        actual = service._build_team_rankings(teams, [{'tenant_id': 'a', 'cpu_cores': None, 'memory_gib': 0}], [])
        self.assertEqual(actual['scope'], 'actual_usage')
        self.assertIsNone(actual['cpu'][0]['cpu_cores'])
        self.assertEqual(actual['memory'][0]['memory_gib'], 0)
        self.assertEqual(actual['metric_status'], {'cpu': 'unavailable', 'memory': 'ok'})

    def test_mixed_configuration_and_observation_never_become_a_usage_total(self):
        service = PlatformOverviewService(cache_backend=MemoryCache(), region_api=mock.Mock())
        with self.assertRaises(ValueError):
            service._build_team_rankings([], [{
                'tenant_id': 'a',
                'cpu_millicores': 1000
            }, {
                'tenant_id': 'b',
                'cpu_cores': 1
            }], [])
