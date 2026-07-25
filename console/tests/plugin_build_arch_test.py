import collections
import collections.abc
import os
import sys
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402
django.setup()

from console.services import plugin_build_arch  # noqa: E402


# capability_id: console.plugin-build.infer-arch
class PluginBuildArchTests(TestCase):

    def test_infers_single_chaos_arch_when_request_omits_arch(self):
        with mock.patch.object(plugin_build_arch.region_api, "get_cluster_nodes_arch",
                               return_value=(200, {"list": ["arm64"]})):
            arch = plugin_build_arch.resolve_plugin_build_arch("", "region-a")

        self.assertEqual("arm64", arch)

    def test_preserves_explicit_request_arch(self):
        with mock.patch.object(plugin_build_arch.region_api, "get_cluster_nodes_arch") as get_cluster_nodes_arch:
            arch = plugin_build_arch.resolve_plugin_build_arch("arm64", "region-a")

        self.assertEqual("arm64", arch)
        get_cluster_nodes_arch.assert_not_called()

    def test_keeps_amd64_default_for_multi_arch_cluster_without_request_arch(self):
        with mock.patch.object(plugin_build_arch.region_api, "get_cluster_nodes_arch",
                               return_value=(200, {"list": ["arm64", "amd64"]})):
            arch = plugin_build_arch.resolve_plugin_build_arch(None, "region-a")

        self.assertEqual("amd64", arch)
