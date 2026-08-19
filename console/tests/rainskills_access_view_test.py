from unittest import TestCase, mock

from django.urls import resolve

from console.views.rainskills_access import RainSkillsAccessView


class RainSkillsAccessViewTests(TestCase):
    def test_route_resolves_to_rainskills_access_view(self):
        match = resolve("/console/rainskills/access")

        self.assertIs(match.func.view_class, RainSkillsAccessView)

    def test_get_returns_access_bean_contract(self):
        access = {
            "can_authorize_rainskills": True,
            "enterprise_licensed": True,
            "is_initial_enterprise_admin": False,
            "deny_reason": "",
        }
        view = RainSkillsAccessView()
        view.user = mock.Mock()

        with mock.patch(
                "console.views.rainskills_access.rainskills_access_service.get_rainskills_access",
                return_value=access) as get_access:
            response = view.get(mock.Mock())

        self.assertEqual(200, response.status_code)
        self.assertEqual(access, response.data["data"]["bean"])
        get_access.assert_called_once_with(view.user)
