# -*- coding: utf-8 -*-
import collections
import os
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

from console.views.enterprise import Enterprises  # noqa: E402


class EnterprisesViewTestCase(TestCase):
    def test_get_includes_team_resource_view_flag_in_enterprise_list(self):
        view = Enterprises()
        request = APIRequestFactory().get("/console/enterprises")
        request.user = mock.Mock(user_id=7)
        enterprise = mock.Mock(
            ID=1,
            enterprise_alias="demo",
            enterprise_name="Demo Enterprise",
            is_active=1,
            enterprise_id="eid-demo",
            enterprise_token="demo-token",
            create_time="2026-04-01 00:00:00",
            enable_team_resource_view=True,
        )

        with mock.patch("console.views.enterprise.enterprise_repo.get_enterprises_by_user_id", return_value=[enterprise]):
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["list"][0]["enable_team_resource_view"], True)
