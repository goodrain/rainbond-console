# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.team_resources import HelmReleasesView  # noqa: E402
from console.views import team_resources  # noqa: E402


class HelmReleasesViewTestCase(TestCase):
    def test_post_reuses_parsed_request_data_for_helm_install(self):
        payload = {
            "name": "demo-release",
            "chart_name": "apache",
            "version": "1.0.0",
            "values": {
                "replicaCount": 1
            }
        }
        view = HelmReleasesView()
        factory = APIRequestFactory()
        request = view.initialize_request(factory.post("/console/team-resources/helm/releases", payload, format="json"))

        # Simulate the permission preprocessing in TenantHeaderView.initial() that reads request.data first.
        self.assertEqual(request.data, payload)

        with mock.patch.object(team_resources.region_api,
                               "install_tenant_helm_release",
                               return_value=({}, {
                                   "bean": {
                                       "release_name": "demo-release"
                                   }
                               })) as install_mock:
            response = view.post(request, "demo-team", "demo-region")

        install_mock.assert_called_once_with("demo-region", "demo-team", payload)
        self.assertEqual(response.data["data"]["bean"]["release_name"], "demo-release")
