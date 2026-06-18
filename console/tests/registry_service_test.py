# -*- coding: utf-8 -*-
import collections
import os
import sys
from types import ModuleType, SimpleNamespace
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
from console.exception.main import ServiceHandleException  # noqa: E402


class RegistryNamespaceServiceTestCase(TestCase):
    def test_parse_volcano_cr_domain_extracts_registry_and_region(self):
        registry, region = team_services._parse_volcano_cr_domain("https://zqq-cn-shanghai.cr.volces.com")

        self.assertEqual(registry, "zqq")
        self.assertEqual(region, "cn-shanghai")

    def test_parse_volcano_cr_domain_rejects_non_volcano_domain(self):
        with self.assertRaises(ServiceHandleException):
            team_services._parse_volcano_cr_domain("https://registry.example.com")

    def test_get_volcano_cr_namespaces_uses_cloud_api(self):
        api = mock.Mock()
        api.list_namespaces.return_value = SimpleNamespace(
            items=[SimpleNamespace(name="rainbond"), SimpleNamespace(name="demo")],
            total_count=2,
        )

        with mock.patch.object(team_services, "_volcano_cr_api", return_value=api) as api_factory:
            namespaces = team_services.get_cloud_registry_namespaces(
                domain="https://zqq-cn-shanghai.cr.volces.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="VolcanoCR",
            )

        api_factory.assert_called_once_with("cloud-ak", "cloud-sk", "cn-shanghai")
        request = api.list_namespaces.call_args[0][0]
        self.assertEqual(request.registry, "zqq")
        self.assertEqual(request.page_number, 1)
        self.assertEqual(request.page_size, 100)
        self.assertEqual(namespaces, ["rainbond", "demo"])

    def test_get_volcano_cr_images_uses_cloud_api(self):
        api = mock.Mock()
        api.list_repositories.return_value = SimpleNamespace(
            items=[
                SimpleNamespace(
                    name="nginx",
                    namespace="rainbond",
                    description="",
                    access_level="Private",
                    create_time="2026-06-18T00:00:00Z",
                    update_time="2026-06-18T01:00:00Z"),
            ],
            total_count=1,
        )

        with mock.patch.object(team_services, "_volcano_cr_api", return_value=api) as api_factory:
            data = team_services.get_cloud_registry_images(
                domain="https://zqq-cn-shanghai.cr.volces.com",
                access_key="cloud-ak",
                access_secret="cloud-sk",
                hub_type="VolcanoCR",
                namespace="rainbond",
                page=1,
                page_size=10,
            )

        api_factory.assert_called_once_with("cloud-ak", "cloud-sk", "cn-shanghai")
        request = api.list_repositories.call_args[0][0]
        self.assertEqual(request.registry, "zqq")
        self.assertEqual(request.filter.namespaces, ["rainbond"])
        self.assertEqual(data["images"][0]["name"], "nginx")
        self.assertEqual(data["images"][0]["namespace"], "rainbond")
        self.assertEqual(data["total"], 1)

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
