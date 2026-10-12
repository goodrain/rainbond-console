# coding: utf-8
import os
import sys
from types import ModuleType
from unittest import TestCase

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
pil_module = ModuleType("PIL")
pil_module.Image = ModuleType("PIL.Image")
pil_module.ImageDraw = ModuleType("PIL.ImageDraw")
pil_module.ImageFont = ModuleType("PIL.ImageFont")
sys.modules.setdefault("PIL", pil_module)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.urls import Resolver404, resolve  # noqa: E402

django.setup()

from console.views.group import TenantGroupOperationView  # noqa: E402


class GroupRouteTests(TestCase):
    # capability_id: console.app-route.numeric-id
    def test_group_detail_route_accepts_numeric_id(self):
        match = resolve("/console/teams/demo-team/groups/42")

        self.assertIs(match.func.view_class, TenantGroupOperationView)
        self.assertEqual(match.kwargs["app_id"], "42")

    # capability_id: console.app-route.numeric-id
    def test_group_detail_route_rejects_reserved_word_as_id(self):
        with self.assertRaises(Resolver404):
            resolve("/console/teams/demo-team/groups/overview")
