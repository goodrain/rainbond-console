# -*- coding: utf-8 -*-
import os
import sys
from types import ModuleType
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
from django.test import SimpleTestCase  # noqa: E402

django.setup()


class ComposeServiceArchTests(SimpleTestCase):

    def test_resolve_compose_arch_uses_single_arm64_cluster_arch_when_missing(self):
        from console.services.compose_service import compose_service

        with mock.patch("console.services.compose_service.region_api.get_cluster_nodes_arch",
                        return_value=(None, {"list": ["arm64", "arm64"]})):
            arch = compose_service._resolve_compose_arch("rainbond", None)

        self.assertEqual(arch, "arm64")

    def test_resolve_compose_arch_keeps_explicit_arch(self):
        from console.services.compose_service import compose_service

        with mock.patch("console.services.compose_service.region_api.get_cluster_nodes_arch") as get_arch:
            arch = compose_service._resolve_compose_arch("rainbond", "arm64")

        self.assertEqual(arch, "arm64")
        get_arch.assert_not_called()

    def test_resolve_compose_arch_keeps_amd64_default_for_multi_arch_cluster(self):
        from console.services.compose_service import compose_service

        with mock.patch("console.services.compose_service.region_api.get_cluster_nodes_arch",
                        return_value=(None, {"list": ["arm64", "amd64"]})):
            arch = compose_service._resolve_compose_arch("rainbond", None)

        self.assertEqual(arch, "amd64")
