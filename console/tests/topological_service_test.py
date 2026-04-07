# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import TestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.topological_services import topological_service  # noqa: E402


class TopologicalServiceAppStatusTests(TestCase):
    # capability_id: console.app-status.closed-with-undeploy-components
    def test_closed_and_undeploy_components_make_app_closed(self):
        status = topological_service.get_app_status(["closed", "undeploy"])

        self.assertEqual(status, "CLOSED")

    # capability_id: console.app-status.waiting-is-starting
    def test_waiting_components_make_app_starting(self):
        status = topological_service.get_app_status(["waiting"])

        self.assertEqual(status, "STARTING")

    # capability_id: console.app-status.partial-abnormal-mixed-components
    def test_mixed_abnormal_components_make_app_partially_abnormal(self):
        status = topological_service.get_app_status(["running", "abnormal"])

        self.assertEqual(status, "PARTIAL_ABNORMAL")

    # capability_id: console.app-status.partial-abnormal-some-abnormal
    def test_some_abnormal_component_makes_app_partially_abnormal(self):
        status = topological_service.get_app_status(["some_abnormal"])

        self.assertEqual(status, "PARTIAL_ABNORMAL")
