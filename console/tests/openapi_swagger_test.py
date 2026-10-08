# coding: utf-8
import os
import sys
from types import ModuleType
from unittest import TestCase

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from openapi.serializer.app_serializer import HelmChartSerializer  # noqa: E402
from openapi.views.apps.apps import HelmChart  # noqa: E402


class OpenAPISwaggerMetadataTests(TestCase):
    # capability_id: console.openapi.helm-chart-query-schema
    def test_helm_chart_get_declares_query_serializer_without_request_body(self):
        swagger_metadata = HelmChart.get._swagger_auto_schema

        self.assertNotIn("request_body", swagger_metadata)
        self.assertIs(swagger_metadata["query_serializer"], HelmChartSerializer)
