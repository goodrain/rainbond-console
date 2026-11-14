from types import SimpleNamespace
from unittest import TestCase, mock

from console.exception.main import AbortRequest
from console.repositories.team_repo import team_repo
from console.services.team_services import TeamService
from console.views.app_config.app_volume import ensure_volume_mode
from openapi.views.apps import apps


# capability_id: console.registry.official-image-name
class OfficialRegistryImageNameTests(TestCase):
    def test_docker_official_library_image_has_name_and_tag(self):
        self.assertEqual(TeamService().get_full_image_name("https://hub.docker.com", "Docker", "library", "nginx", "1.27"),
                         "nginx:1.27")

    def test_other_namespaces_and_private_hosts_keep_existing_names(self):
        service = TeamService()
        self.assertEqual(service.get_full_image_name("https://hub.docker.com", "Docker", "example", "web", "stable"),
                         "example/web:stable")
        self.assertEqual(service.get_full_image_name("https://registry.example.test", "Harbor", "library", "web", "stable"),
                         "registry.example.test/library/web:stable")


# capability_id: console.openapi.region-service-inspection
class RegionServiceInspectionTests(TestCase):
    def test_region_services_use_enterprise_team_aliases(self):
        records = [
            SimpleNamespace(service_id="service-a", tenant_id="team-a", service_cname="first"),
            SimpleNamespace(service_id="service-b", tenant_id="team-b", service_cname="second")
        ]
        teams = [
            SimpleNamespace(tenant_id="team-a", tenant_alias="team one"),
            SimpleNamespace(tenant_id="team-b", tenant_alias="team two")
        ]
        with mock.patch.object(apps.service_repo, "get_service_by_region", return_value=records) as services:
            with mock.patch.object(team_repo, "get_team_by_enterprise_id") as enterprise_teams:
                enterprise_teams.return_value.all.return_value = teams
                response = apps.GetServiceInfoView().get(SimpleNamespace(), "enterprise-a", "region-a")
        services.assert_called_once_with("enterprise-a", "region-a")
        enterprise_teams.assert_called_once_with("enterprise-a")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"], [
            {
                "service_id": "service-a",
                "team_alias": "team one",
                "service_cname": "first"
            },
            {
                "service_id": "service-b",
                "team_alias": "team two",
                "service_cname": "second"
            },
        ])


# capability_id: console.volume.exact-integer-mode
class ExactVolumeModeTests(TestCase):
    def test_mode_keeps_exact_integer_policy_including_bool_rejection(self):
        class DerivedInt(int):
            pass

        for value in (0, 755, 777):
            self.assertEqual(ensure_volume_mode(value), value)
        for value in (True, False, DerivedInt(755), "755", -1, 888, 1000):
            with self.subTest(value=value):
                with self.assertRaises(AbortRequest):
                    ensure_volume_mode(value)
