from unittest import TestCase, mock

from console.exception.main import ServiceHandleException
from console.services.agent_access_service import AgentAccessService, agent_access_service


class AgentAccessServiceTests(TestCase):
    def _user(self, user_id=1, enterprise_id="eid"):
        user = mock.Mock()
        user.user_id = user_id
        user.enterprise_id = enterprise_id
        return user

    def test_open_source_allows_initial_enterprise_admin(self):
        user = self._user(user_id=1)
        marker = mock.Mock()
        marker.user_id = 1

        with mock.patch.object(agent_access_service, "get_platform_edition", return_value="open_source"), \
                mock.patch.object(agent_access_service, "ensure_initial_enterprise_admin_marker", return_value=marker), \
                mock.patch("console.services.agent_access_service.enterprise_user_perm_repo.is_admin",
                           return_value=True):
            access = agent_access_service.get_agent_access(user)

        self.assertTrue(access["can_open_agent"])
        self.assertTrue(access["is_initial_enterprise_admin"])
        self.assertEqual("", access["deny_reason"])

    def test_open_source_rejects_non_initial_enterprise_admin(self):
        user = self._user(user_id=2)
        marker = mock.Mock()
        marker.user_id = 1

        with mock.patch.object(agent_access_service, "get_platform_edition", return_value="open_source"), \
                mock.patch.object(agent_access_service, "ensure_initial_enterprise_admin_marker", return_value=marker), \
                mock.patch("console.services.agent_access_service.enterprise_user_perm_repo.is_admin",
                           return_value=True):
            access = agent_access_service.get_agent_access(user)

        self.assertFalse(access["can_open_agent"])
        self.assertFalse(access["is_initial_enterprise_admin"])
        self.assertEqual("open_source_requires_enterprise", access["deny_reason"])

    def test_open_source_rejects_non_admin(self):
        user = self._user(user_id=2)
        marker = mock.Mock()
        marker.user_id = 1

        with mock.patch.object(agent_access_service, "get_platform_edition", return_value="open_source"), \
                mock.patch.object(agent_access_service, "ensure_initial_enterprise_admin_marker", return_value=marker), \
                mock.patch("console.services.agent_access_service.enterprise_user_perm_repo.is_admin",
                           return_value=False):
            access = agent_access_service.get_agent_access(user)

        self.assertFalse(access["can_open_agent"])
        self.assertEqual("not_enterprise_admin", access["deny_reason"])

    def test_enterprise_allows_and_reports_initial_marker(self):
        user = self._user(user_id=1)
        marker = mock.Mock()
        marker.user_id = 1

        with mock.patch.object(agent_access_service, "get_platform_edition", return_value="enterprise"), \
                mock.patch.object(agent_access_service, "ensure_initial_enterprise_admin_marker", return_value=marker):
            access = agent_access_service.get_agent_access(user)

        self.assertTrue(access["can_open_agent"])
        self.assertEqual("enterprise", access["edition"])
        self.assertTrue(access["is_initial_enterprise_admin"])

    def test_enterprise_allows_non_initial_user(self):
        user = self._user(user_id=2)
        marker = mock.Mock()
        marker.user_id = 1

        with mock.patch.object(agent_access_service, "get_platform_edition", return_value="enterprise"), \
                mock.patch.object(agent_access_service, "ensure_initial_enterprise_admin_marker", return_value=marker):
            access = agent_access_service.get_agent_access(user)

        self.assertTrue(access["can_open_agent"])
        self.assertFalse(access["is_initial_enterprise_admin"])
        self.assertEqual("", access["deny_reason"])

    def test_saas_allows_and_reports_initial_marker(self):
        user = self._user(user_id=2)
        marker = mock.Mock()
        marker.user_id = 1

        with mock.patch.object(agent_access_service, "get_platform_edition", return_value="saas"), \
                mock.patch.object(agent_access_service, "ensure_initial_enterprise_admin_marker", return_value=marker):
            access = agent_access_service.get_agent_access(user)

        self.assertTrue(access["can_open_agent"])
        self.assertEqual("saas", access["edition"])
        self.assertFalse(access["is_initial_enterprise_admin"])

    def test_platform_edition_uses_existing_conditions(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(agent_access_service, "has_enterprise_base_plugin", return_value=False):
            self.assertEqual("open_source", agent_access_service.get_platform_edition("eid"))

        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(agent_access_service, "has_enterprise_base_plugin", return_value=True):
            self.assertEqual("enterprise", agent_access_service.get_platform_edition("eid"))

        with mock.patch.dict("os.environ", {"USE_SAAS": "true"}, clear=True), \
                mock.patch.object(agent_access_service, "has_enterprise_base_plugin", return_value=False):
            self.assertEqual("saas", agent_access_service.get_platform_edition("eid"))

        with mock.patch.dict("os.environ", {"USE_SAAS": "true"}, clear=True), \
                mock.patch.object(agent_access_service, "has_enterprise_base_plugin", return_value=True):
            self.assertEqual("enterprise_saas", agent_access_service.get_platform_edition("eid"))


class HasEnterpriseBasePluginTests(TestCase):
    def setUp(self):
        self.service = AgentAccessService()
        self.region = mock.Mock()
        self.region.region_name = "rg"

    def test_region_probe_true_short_circuits(self):
        with mock.patch("console.services.agent_access_service.region_repo.get_usable_regions",
                        return_value=[self.region]), \
                mock.patch("console.services.agent_access_service.region_api.cluster_plugin_exists",
                           return_value=True) as probe:
            self.assertTrue(self.service.has_enterprise_base_plugin("eid"))
        probe.assert_called_once_with("eid", "rg", "rainbond-enterprise-base")

    def test_region_probe_404_falls_back_to_listing(self):
        body = {"list": [{"name": "rainbond-enterprise-base"}]}
        with mock.patch("console.services.agent_access_service.region_repo.get_usable_regions",
                        return_value=[self.region]), \
                mock.patch("console.services.agent_access_service.region_api.cluster_plugin_exists",
                           side_effect=ServiceHandleException(msg="not found", status_code=404)), \
                mock.patch("console.services.agent_access_service.region_api.list_plugins",
                           return_value=(None, body)) as list_plugins:
            self.assertTrue(self.service.has_enterprise_base_plugin("eid"))
        list_plugins.assert_called_once_with("eid", "rg", True)

    def test_region_probe_transport_error_returns_false(self):
        with mock.patch("console.services.agent_access_service.region_repo.get_usable_regions",
                        return_value=[self.region]), \
                mock.patch("console.services.agent_access_service.region_api.cluster_plugin_exists",
                           side_effect=ServiceHandleException(msg="unreachable", status_code=400)):
            self.assertFalse(self.service.has_enterprise_base_plugin("eid"))

    def test_result_is_cached_within_ttl(self):
        with mock.patch("console.services.agent_access_service.region_repo.get_usable_regions",
                        return_value=[self.region]), \
                mock.patch("console.services.agent_access_service.region_api.cluster_plugin_exists",
                           return_value=True) as probe:
            self.assertTrue(self.service.has_enterprise_base_plugin("eid"))
            self.assertTrue(self.service.has_enterprise_base_plugin("eid"))
        probe.assert_called_once()
