# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType
from unittest import TestCase, mock
try:
    from urllib.parse import parse_qs, urlparse
except ImportError:
    from urlparse import parse_qs, urlparse

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.services.team_services import team_services  # noqa: E402


class RegistryNamespaceServiceTestCase(TestCase):
    def test_get_harbor_namespaces_fetches_all_pages(self):
        names = ["project-{}".format(i) for i in range(205)]

        def harbor_projects_response(url, *args, **kwargs):
            query = parse_qs(urlparse(url).query)
            page = int(query.get("page", ["1"])[0])
            page_size = int(query.get("page_size", ["10"])[0])
            start = (page - 1) * page_size
            page_names = names[start:start + page_size]
            response = mock.Mock(status_code=200, headers={"X-Total-Count": str(len(names))})
            response.json.return_value = [{"name": name} for name in page_names]
            return response

        with mock.patch("console.services.team_services.requests.get", side_effect=harbor_projects_response) as get_mock:
            result = team_services.get_registry_namespaces(
                domain="https://harbor.example.com",
                username="demo-user",
                password="demo-password",
                hub_type="Harbor",
            )

        self.assertEqual(result, names)
        self.assertEqual(get_mock.call_count, 3)

    def test_get_harbor_namespaces_fetches_until_short_page_without_total_header(self):
        names = ["project-{}".format(i) for i in range(120)]

        def harbor_projects_response(url, *args, **kwargs):
            query = parse_qs(urlparse(url).query)
            page = int(query.get("page", ["1"])[0])
            page_size = int(query.get("page_size", ["10"])[0])
            start = (page - 1) * page_size
            page_names = names[start:start + page_size]
            response = mock.Mock(status_code=200, headers={})
            response.json.return_value = [{"name": name} for name in page_names]
            return response

        with mock.patch("console.services.team_services.requests.get", side_effect=harbor_projects_response) as get_mock:
            result = team_services.get_registry_namespaces(
                domain="https://harbor.example.com",
                username="demo-user",
                password="demo-password",
                hub_type="Harbor",
            )

        self.assertEqual(result, names)
        self.assertEqual(get_mock.call_count, 2)
