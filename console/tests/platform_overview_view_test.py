# -*- coding: utf-8 -*-
import collections
import os
import sys
from contextlib import ExitStack
from types import ModuleType, SimpleNamespace
from unittest import mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
if "openapi_client" not in sys.modules:
    openapi_client_module = ModuleType("openapi_client")
    openapi_client_module.ApiClient = object
    openapi_client_module.MarketOpenapiApi = object
    configuration_module = ModuleType("openapi_client.configuration")
    configuration_module.Configuration = type("Configuration", (), {})
    rest_module = ModuleType("openapi_client.rest")
    rest_module.ApiException = type("ApiException", (Exception, ), {})
    sys.modules["openapi_client"] = openapi_client_module
    sys.modules["openapi_client.configuration"] = configuration_module
    sys.modules["openapi_client.rest"] = rest_module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402
from django.urls import Resolver404, resolve  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

django.setup()

from console.views.platform_overview import (  # noqa: E402
    PlatformOverviewMetricsView, PlatformOverviewRuntimeView, PlatformOverviewShellView, PlatformOverviewSnapshotView)
from console.services.platform_overview_service import PlatformOverviewRegionNotFound  # noqa: E402

# capability_id: console.platform-overview.http-api


class PlatformOverviewViewTest(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @staticmethod
    def _user(enterprise_id="eid"):
        return SimpleNamespace(
            user_id=1,
            nick_name="admin",
            enterprise_id=enterprise_id,
            sys_admin=False,
            is_authenticated=True,
        )

    def _get(self,
             view_class,
             path,
             *,
             enterprise_id="eid",
             user_enterprise_id="eid",
             region_name=None,
             query=None,
             is_admin=True):
        request = self.factory.get(path, query or {})
        force_authenticate(request, user=self._user(user_enterprise_id))
        kwargs = {"enterprise_id": enterprise_id}
        if region_name:
            kwargs["region_name"] = region_name
        stack = ExitStack()
        enterprise_filter = stack.enter_context(mock.patch("console.views.base.TenantEnterprise.objects.filter"))
        enterprise_filter.return_value.first.return_value = SimpleNamespace(enterprise_id=user_enterprise_id)
        stack.enter_context(mock.patch("console.views.base.enterprise_user_perm_repo.is_admin", return_value=is_admin))
        stack.enter_context(mock.patch("console.views.base.user_services.list_roles", return_value=[]))
        stack.enter_context(mock.patch("console.views.base.perms.list_enterprise_perm_codes_by_roles", return_value=[]))
        with stack:
            return view_class.as_view()(request, **kwargs)

    def test_urls_resolve_to_overview_views(self):
        routes = {
            "/console/enterprise/eid/platform-overview": PlatformOverviewShellView,
            "/console/enterprise/eid/platform-overview/runtime": PlatformOverviewRuntimeView,
            "/console/enterprise/eid/regions/r1/platform-overview": PlatformOverviewSnapshotView,
            "/console/enterprise/eid/regions/r1/platform-overview/metrics": PlatformOverviewMetricsView,
        }
        for path, expected in routes.items():
            with self.subTest(path=path):
                self.assertIs(resolve(path).func.view_class, expected)
        with self.assertRaises(Resolver404):
            resolve("/console/enterprise/eid/platform-overview/runtime-extra")

    @mock.patch("console.views.platform_overview.platform_overview_service.get_metrics")
    def test_metrics_accepts_allowlisted_arguments(self, get_metrics):
        get_metrics.return_value = {
            "status": "ok",
            "metric": "network",
            "range": "24h",
            "unit": "bytes_per_second",
            "series": [],
        }

        response = self._get(
            PlatformOverviewMetricsView,
            "/console/enterprise/eid/regions/r1/platform-overview/metrics",
            region_name="r1",
            query={
                "metric": "network",
                "range": "24h"
            },
        )

        self.assertEqual(200, response.status_code)
        get_metrics.assert_called_once_with("eid", "r1", "network", "24h")

    @mock.patch("console.views.platform_overview.platform_overview_service.get_metrics")
    def test_metrics_rejects_arbitrary_promql(self, get_metrics):
        response = self._get(
            PlatformOverviewMetricsView,
            "/console/enterprise/eid/regions/r1/platform-overview/metrics",
            region_name="r1",
            query={
                "metric": "up{}",
                "range": "6h"
            },
        )

        self.assertEqual(400, response.status_code)
        get_metrics.assert_not_called()

    @mock.patch("console.views.platform_overview.platform_overview_service.get_shell")
    def test_view_rejects_enterprise_outside_jwt_scope(self, get_shell):
        response = self._get(
            PlatformOverviewShellView,
            "/console/enterprise/other/platform-overview",
            enterprise_id="other",
            user_enterprise_id="eid",
        )

        self.assertEqual(403, response.status_code)
        get_shell.assert_not_called()

    @mock.patch("console.views.platform_overview.platform_overview_service.get_shell")
    def test_view_rejects_same_enterprise_non_admin(self, get_shell):
        response = self._get(
            PlatformOverviewShellView,
            "/console/enterprise/eid/platform-overview",
            is_admin=False,
        )

        self.assertEqual(403, response.status_code)
        get_shell.assert_not_called()

    @mock.patch("console.views.platform_overview.platform_overview_service.get_cluster_overview")
    def test_snapshot_returns_partial_payload_with_http_200(self, get_snapshot):
        get_snapshot.return_value = {
            "status": "partial",
            "generated_at": "2026-10-19T00:00:00+00:00",
            "sections": {
                "nodes": {
                    "status": "unavailable",
                    "data": None
                }
            },
        }
        response = self._get(
            PlatformOverviewSnapshotView,
            "/console/enterprise/eid/regions/r1/platform-overview",
            region_name="r1",
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual("partial", response.data["data"]["bean"]["status"])

    @mock.patch("console.views.platform_overview.platform_overview_service.get_cluster_overview")
    def test_snapshot_returns_404_for_foreign_region(self, get_snapshot):
        get_snapshot.side_effect = PlatformOverviewRegionNotFound("foreign")

        response = self._get(
            PlatformOverviewSnapshotView,
            "/console/enterprise/eid/regions/foreign/platform-overview",
            region_name="foreign",
        )

        self.assertEqual(404, response.status_code)
