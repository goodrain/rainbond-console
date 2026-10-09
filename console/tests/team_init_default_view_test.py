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

django.setup()

from django.test import RequestFactory  # noqa: E402

from console.views.team import InitDefaultInfoView  # noqa: E402


class InitDefaultInfoViewTestCase(TestCase):
    # capability_id: console.enterprise-init.empty-region
    def test_post_returns_null_default_region_when_enterprise_has_no_regions(self):
        view = InitDefaultInfoView()
        view.enterprise = mock.Mock(enterprise_id="enterprise-id")
        enterprise = mock.Mock()
        enterprise.to_dict.return_value = {"enterprise_id": "enterprise-id"}

        with mock.patch("console.views.team.enterprise_repo.get_enterprise_by_enterprise_id", return_value=enterprise), \
                mock.patch("console.views.team.region_repo.get_regions_by_enterprise_id", return_value=[]):
            response = view.post(RequestFactory().post("/console/enterprise/init"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["data"]["bean"]["default_region"])

    def test_post_keeps_the_first_region_as_default_when_available(self):
        view = InitDefaultInfoView()
        view.enterprise = mock.Mock(enterprise_id="enterprise-id")
        enterprise = mock.Mock()
        enterprise.to_dict.return_value = {"enterprise_id": "enterprise-id"}
        region = mock.Mock()
        region.to_dict.return_value = {"region_name": "rainbond"}

        with mock.patch("console.views.team.enterprise_repo.get_enterprise_by_enterprise_id", return_value=enterprise), \
                mock.patch("console.views.team.region_repo.get_regions_by_enterprise_id", return_value=[region]):
            response = view.post(RequestFactory().post("/console/enterprise/init"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["bean"]["default_region"], {"region_name": "rainbond"})
