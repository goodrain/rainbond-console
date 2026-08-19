from unittest import TestCase, mock

from console.services.rainskills_access_service import RainSkillsAccessService


class RainSkillsAccessServiceTests(TestCase):
    def setUp(self):
        self.license_service = mock.Mock()
        self.region_repo = mock.Mock()
        self.enterprise_user_perm_repo = mock.Mock()
        self.enterprise_user_perm_model = mock.Mock()
        self.user_model = mock.Mock()
        self.service = RainSkillsAccessService(
            license_service_instance=self.license_service,
            region_repo_instance=self.region_repo,
            enterprise_user_perm_repo_instance=self.enterprise_user_perm_repo,
            enterprise_user_perm_model=self.enterprise_user_perm_model,
            user_model=self.user_model,
        )
        region = mock.Mock()
        region.region_name = "region-1"
        self.region_repo.get_usable_regions.return_value = [region]
        self.enterprise_user_perm_model.objects.filter.return_value.first.return_value = None

    @staticmethod
    def _user(user_id=1, enterprise_id="eid"):
        user = mock.Mock()
        user.user_id = user_id
        user.enterprise_id = enterprise_id
        return user

    def test_valid_enterprise_license_allows_any_user_without_agent_plugin(self):
        self.license_service.get_license_status.return_value = {"bean": {"valid": True}}

        access = self.service.get_rainskills_access(self._user(user_id=2))

        self.assertTrue(access["can_authorize_rainskills"])
        self.assertTrue(access["enterprise_licensed"])
        self.assertEqual("", access["deny_reason"])
        self.enterprise_user_perm_model.objects.filter.assert_not_called()
        self.user_model.objects.filter.assert_not_called()

    def test_community_allows_initial_enterprise_admin(self):
        marker = mock.Mock(user_id=1)
        self.license_service.get_license_status.return_value = {"bean": {"valid": False}}
        self.enterprise_user_perm_model.objects.filter.return_value.first.return_value = marker
        self.enterprise_user_perm_repo.is_admin.return_value = True

        access = self.service.get_rainskills_access(self._user(user_id=1))

        self.assertTrue(access["can_authorize_rainskills"])
        self.assertFalse(access["enterprise_licensed"])
        self.assertTrue(access["is_initial_enterprise_admin"])
        self.assertEqual("", access["deny_reason"])

    def test_community_rejects_non_initial_enterprise_admin(self):
        marker = mock.Mock(user_id=1)
        self.license_service.get_license_status.return_value = {"bean": {"valid": False}}
        self.enterprise_user_perm_model.objects.filter.return_value.first.return_value = marker
        self.enterprise_user_perm_repo.is_admin.return_value = True

        access = self.service.get_rainskills_access(self._user(user_id=2))

        self.assertFalse(access["can_authorize_rainskills"])
        self.assertFalse(access["is_initial_enterprise_admin"])
        self.assertEqual("open_source_requires_enterprise", access["deny_reason"])

    def test_community_rejects_non_admin(self):
        marker = mock.Mock(user_id=1)
        self.license_service.get_license_status.return_value = {"bean": {"valid": False}}
        self.enterprise_user_perm_model.objects.filter.return_value.first.return_value = marker
        self.enterprise_user_perm_repo.is_admin.return_value = False

        access = self.service.get_rainskills_access(self._user(user_id=2))

        self.assertFalse(access["can_authorize_rainskills"])
        self.assertEqual("not_enterprise_admin", access["deny_reason"])

    def test_license_lookup_failure_fails_closed(self):
        self.license_service.get_license_status.side_effect = RuntimeError("region unavailable")

        access = self.service.get_rainskills_access(self._user())

        self.assertFalse(access["can_authorize_rainskills"])
        self.assertFalse(access["enterprise_licensed"])
        self.assertEqual("license_check_failed", access["deny_reason"])
        self.enterprise_user_perm_model.objects.filter.assert_not_called()

    def test_only_boolean_true_counts_as_valid_enterprise_license(self):
        marker = mock.Mock(user_id=1)
        self.license_service.get_license_status.return_value = {"bean": {"valid": 1}}
        self.enterprise_user_perm_model.objects.filter.return_value.first.return_value = marker
        self.enterprise_user_perm_repo.is_admin.return_value = True

        access = self.service.get_rainskills_access(self._user(user_id=2))

        self.assertFalse(access["can_authorize_rainskills"])
        self.assertFalse(access["enterprise_licensed"])

    def test_no_usable_region_uses_community_rule(self):
        marker = mock.Mock(user_id=1)
        self.region_repo.get_usable_regions.return_value = []
        self.enterprise_user_perm_model.objects.filter.return_value.first.return_value = marker
        self.enterprise_user_perm_repo.is_admin.return_value = True

        access = self.service.get_rainskills_access(self._user(user_id=1))

        self.assertTrue(access["can_authorize_rainskills"])
        self.assertFalse(access["enterprise_licensed"])
        self.license_service.get_license_status.assert_not_called()
