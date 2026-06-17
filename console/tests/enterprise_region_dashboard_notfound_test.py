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
from rest_framework.response import Response  # noqa: E402

django.setup()

from console.views import enterprise as enterprise_module  # noqa: E402
from console.views.enterprise import EnterpriseRegionDashboard  # noqa: E402


# capability_id: console.enterprise.region-dashboard-not-found
class EnterpriseRegionDashboardNotFoundTest(TestCase):
    def test_missing_region_returns_clean_404(self):
        view = EnterpriseRegionDashboard()
        request = mock.Mock()
        view.initialize_request = mock.Mock(return_value=request)
        view.initial = mock.Mock()
        view.finalize_response = mock.Mock(side_effect=lambda req, resp, *a, **k: resp)
        # If the 404 branch raised (status.HTTP_404_NOTFOUND typo -> AttributeError),
        # it would be caught here and surfaced as a 500-style error response.
        view.handle_exception = mock.Mock(return_value=Response({}, status=500))

        with mock.patch.object(enterprise_module, "region_services") as region_services:
            region_services.get_enterprise_region.return_value = None
            response = view.dispatch(request, "ent-1", "region-1")

        self.assertEqual(response.status_code, 404)
        view.handle_exception.assert_not_called()
