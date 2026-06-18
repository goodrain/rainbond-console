# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from openapi.services.app_service import app_service  # noqa: E402


# capability_id: openapi.app-service.team-not-found
class AppServiceTeamNotFoundTest(TestCase):

    @mock.patch("openapi.services.app_service.base_service")
    @mock.patch("openapi.services.app_service.team_services")
    @mock.patch("openapi.services.app_service.group_service")
    def test_get_app_services_and_status_raises_when_team_not_found(self, mock_group_svc, mock_team_svc, mock_base_svc):
        mock_group_svc.get_group_services.return_value = [mock.Mock(service_id="s1")]
        mock_team_svc.get_team_by_team_id.return_value = None

        app = mock.Mock(tenant_id="t1", region_name="r1", ID=1)

        with self.assertRaises(ServiceHandleException) as ctx:
            app_service.get_app_services_and_status(app)

        self.assertIn("team associated with the app is not found", str(ctx.exception))

    @mock.patch("openapi.services.app_service.base_service")
    @mock.patch("openapi.services.app_service.team_services")
    @mock.patch("openapi.services.app_service.group_service")
    def test_get_app_services_and_status_succeeds_when_team_exists(self, mock_group_svc, mock_team_svc, mock_base_svc):
        mock_group_svc.get_group_services.return_value = []
        mock_team_svc.get_team_by_team_id.return_value = mock.Mock(tenant_name="tn", enterprise_id="e1")
        mock_base_svc.status_multi_service.return_value = []

        app = mock.Mock(tenant_id="t1", region_name="r1", ID=1)

        result = app_service.get_app_services_and_status(app)

        self.assertEqual(result, [])
