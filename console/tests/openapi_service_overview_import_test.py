# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from openapi.views import enterprise_view as enterprise_view_module  # noqa: E402


# capability_id: openapi.enterprise.service-overview
class ServiceOverviewImportTest(TestCase):
    def test_service_overview_singleton_is_resolvable(self):
        # ServiceOverview.get referenced `service_overview` without importing it -> NameError.
        self.assertTrue(hasattr(enterprise_view_module, "service_overview"))
        from console.services.service_overview import service_overview
        self.assertIs(enterprise_view_module.service_overview, service_overview)
