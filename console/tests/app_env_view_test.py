# -*- coding: utf-8 -*-
import collections
import os
import re
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

django.setup()

from console.views.app_config.app_env import AppEnvView  # noqa: E402


class AppEnvViewPaginationTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = AppEnvView()
        self.view.service = mock.Mock(tenant_id="tenant-id", service_id="service-id")

    @staticmethod
    def _build_cursor(rows=None, executed_sql=None):
        cursor = mock.Mock()
        cursor.fetchall.return_value = rows or []
        if executed_sql is not None:

            def execute(sql):
                executed_sql.append(sql)
                if re.search(r"LIMIT\s+\d+\s*,\s*-\d+", sql):
                    raise AssertionError("negative LIMIT should not be executed")

            cursor.execute.side_effect = execute
        return cursor

    def test_get_returns_empty_list_when_requested_page_exceeds_inner_env_total(self):
        request = self.factory.get("/console/teams/demo-team/apps/demo-service/envs",
                                   {"env_type": "inner", "page": 2, "page_size": 10})
        count_cursor = self._build_cursor(rows=[(8, )])
        executed_sql = []
        list_cursor = self._build_cursor(executed_sql=executed_sql)

        with mock.patch("console.views.app_config.app_env.connection.cursor", side_effect=[count_cursor, list_cursor]):
            response = self.view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["total"], 8)
        self.assertEqual(response.data["data"]["list"], [])
        if executed_sql:
            self.assertNotRegex(executed_sql[0], r"LIMIT\s+\d+\s*,\s*-\d+")
