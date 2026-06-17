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

from openapi.views.apps import apps as apps_module  # noqa: E402
from openapi.views.apps.apps import TeamAppsCloseView  # noqa: E402


# capability_id: openapi.app.team-apps-close
class TeamAppsCloseTest(TestCase):
    def test_post_unpacks_three_return_values_from_batch_action(self):
        view = TeamAppsCloseView()
        view.region_name = "rg"
        view.team = mock.Mock(tenant_id="tenant-1")
        view.user = mock.Mock()
        view.oauth_instance = mock.Mock()
        request = mock.Mock()
        request.data = {}

        services = mock.Mock()
        services.values_list.return_value = ["svc-1"]

        with mock.patch.object(apps_module, "service_repo") as service_repo, \
                mock.patch.object(apps_module, "app_manage_service") as app_manage_service:
            service_repo.get_tenant_region_services.return_value = services
            # batch_action returns (code, msg, services) -> unpacking only 2 raised ValueError.
            app_manage_service.batch_action.return_value = (200, "ok", ["svc-1"])
            response = view.post(request, team_id="tenant-1", region_name="rg")

        self.assertEqual(response.status_code, 200)
        app_manage_service.batch_action.assert_called_once()
