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
from openapi.views import team_view as team_view_module  # noqa: E402
from openapi.views.team_view import TeamInfo  # noqa: E402


# capability_id: openapi.team.delete-error-propagation
class TeamDeleteExceptTest(TestCase):
    def test_service_error_propagates_instead_of_typeerror(self):
        # The `except PermRelTenant` clause (a Django model, not an exception) raised a
        # TypeError that masked the real ServiceHandleException as a 500.
        view = TeamInfo()
        view.user = mock.Mock()
        view.team = mock.Mock()
        request = mock.Mock()

        with mock.patch.object(team_view_module.team_services, "delete_by_tenant_id",
                               side_effect=ServiceHandleException(msg="boom")):
            with self.assertRaises(ServiceHandleException):
                view.delete(request, "team-1")
