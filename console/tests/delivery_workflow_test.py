"""Keep delivery SQLite settings isolated from the rest of the Django suite."""
import subprocess
import sys
import unittest
from pathlib import Path


class DeliveryWorkflowTest(unittest.TestCase):
    def test_independent_delivery_workflow(self):
        result = subprocess.run([sys.executable, "-m", "console.tests.isolated_delivery_workflow"],
                                cwd=Path(__file__).parents[2],
                                capture_output=True,
                                text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_existing_app_model_endpoints_accept_delivery_source(self):
        from types import SimpleNamespace
        from unittest import mock
        from rest_framework.response import Response
        from console.views.center_pool.apps import CenterAppCLView, CenterAppUDView
        request = SimpleNamespace(META={},
                                  data={"delivery_source": {
                                      "team_name": "team",
                                      "region_name": "region",
                                      "app_id": "123"
                                  }})
        with mock.patch("console.views.center_pool.apps.save_delivery_profile", return_value=Response({"ok": True})) as save:
            create_view = CenterAppCLView()
            create_view.post(request, "enterprise")
            save.assert_called_once_with(create_view, request, "enterprise")
            save.reset_mock()
            edit_view = CenterAppUDView()
            edit_view.put(request, "enterprise", "template-id")
            save.assert_called_once_with(edit_view, request, "enterprise", "template-id")

    def test_existing_catalog_creation_without_source_uses_original_service(self):
        from types import SimpleNamespace
        from unittest import mock
        from console.views.center_pool.apps import CenterAppCLView
        request = SimpleNamespace(META={}, data={"name": "CatalogTemplate", "scope": "team", "create_team": "team"})
        view = CenterAppCLView()
        view.user = SimpleNamespace(enterprise_id="enterprise")
        with mock.patch("console.views.center_pool.apps.save_delivery_profile") as delivery, \
             mock.patch("console.views.center_pool.apps.market_app_service") as market, \
             mock.patch("console.views.center_pool.apps.app_tag_repo") as tags, \
             mock.patch("console.views.center_pool.apps.operation_log_service"):
            tags.get_tags.return_value = []
            market.json_rainbond_app.return_value = "{}"
            response = view.post(request, "enterprise")
        self.assertEqual(response.status_code, 200)
        market.create_rainbond_app.assert_called_once()
        delivery.assert_not_called()
