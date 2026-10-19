# -*- coding: utf-8 -*-
# capability_id: console.region-api.polling-deadlines
import os
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from django.test import SimpleTestCase  # noqa: E402

from www.apiclient.regionapi import RegionInvokeApi  # noqa: E402


class RegionApiPollingDeadlineTests(SimpleTestCase):

    def setUp(self):
        self.client = RegionInvokeApi()
        self.access = mock.patch.object(
            self.client,
            "_RegionInvokeApi__get_region_access_info",
            return_value=("https://region.example", "region-token"),
        )
        self.tenant_region = mock.patch.object(
            self.client,
            "_RegionInvokeApi__get_tenant_region_info",
            return_value=SimpleNamespace(region_tenant_name="tenant-a"),
        )
        self.access.start()
        self.tenant_region.start()
        self.addCleanup(self.access.stop)
        self.addCleanup(self.tenant_region.stop)

    def assert_polling_deadline(self, request, read_timeout):
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["connect_timeout"], 3)
        self.assertEqual(kwargs["timeout"], read_timeout)
        self.assertEqual(kwargs["retries"], 0)

    def assert_legacy_deadline(self, request, read_timeout=None):
        kwargs = request.call_args.kwargs
        self.assertNotIn("connect_timeout", kwargs)
        self.assertNotIn("retries", kwargs)
        if read_timeout is None:
            self.assertNotIn("timeout", kwargs)
        else:
            self.assertEqual(kwargs["timeout"], read_timeout)

    def test_default_calls_preserve_legacy_deadlines(self):
        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"bean": {}})) as request:
            self.client.check_service_status("region-a", "team-a", "component-a", "enterprise-a")
        self.assert_legacy_deadline(request)

        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": []})) as request:
            self.client.get_service_pods("region-a", "team-a", "component-a", "enterprise-a")
        self.assert_legacy_deadline(request, 15)

        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": []})) as request:
            self.client.get_target_events_list("region-a", "team-a", "service", "service-id", 1, 6)
        self.assert_legacy_deadline(request, 20)

    def test_polling_calls_use_bounded_deadlines(self):
        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"bean": {}})) as request:
            self.client.check_service_status("region-a", "team-a", "component-a", "enterprise-a", polling=True)
        self.assert_polling_deadline(request, 5)

        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": []})) as request:
            self.client.get_service_pods("region-a", "team-a", "component-a", "enterprise-a", polling=True)
        self.assert_polling_deadline(request, 8)

        with mock.patch.object(self.client, "_get", return_value=({"status": 200}, {"list": []})) as request:
            self.client.get_target_events_list("region-a", "team-a", "service", "service-id", 1, 6, polling=True)
        self.assert_polling_deadline(request, 8)

    def test_http_polling_entrypoints_enable_bounded_deadlines(self):
        repo_root = Path(__file__).resolve().parents[2]
        overview_source = (repo_root / "console/views/app_overview.py").read_text()
        event_view_source = (repo_root / "console/views/app_event.py").read_text()
        app_service_source = (repo_root / "console/services/app.py").read_text()
        event_service_source = (repo_root / "console/services/app_actions/app_log.py").read_text()
        kubeblocks_source = (repo_root / "console/services/kubeblocks_service.py").read_text()

        self.assertRegex(
            overview_source,
            r"get_service_status\(self\.tenant, self\.service, polling=True\)",
        )
        self.assertRegex(
            overview_source,
            r"get_service_pods\([\s\S]{0,250}?polling=True\)",
        )
        self.assertGreaterEqual(len(re.findall(r"polling=True", event_view_source)), 4)
        self.assertIn("polling=polling", app_service_source)
        self.assertIn("polling=polling", event_service_source)
        self.assertIn("polling=polling", kubeblocks_source)
