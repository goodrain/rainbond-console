# coding: utf-8
from unittest import TestCase

import os
import sys
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django

django.setup()

from console.utils.version import compare_version
from console.utils.version import get_new_versions
from console.utils.version import sorted_versions


class VersionUtilsTests(TestCase):
    # capability_id: console.version.compare
    def test_compare_version(self):
        self.assertEqual(compare_version("1.1.1", "1.0.1"), 1)
        self.assertEqual(compare_version("1.1.10", "1.2.1"), -1)
        self.assertEqual(compare_version("1.1.1", "1.1.1"), 0)

    # capability_id: console.version.sort-desc
    def test_sorted_versions(self):
        versions = ["1.8", "1.1", "2.0", "1.7", "0.19", "3.0", "1.8.1"]
        self.assertEqual(sorted_versions(versions), ["3.0", "2.0", "1.8.1", "1.8", "1.7", "1.1", "0.19"])

    # capability_id: console.version.newer-filter
    def test_get_new_versions(self):
        self.assertEqual(get_new_versions("1.8", "1.1", "2.0", "1.7", "0.19", "3.0", "1.8", "1.8.1"), ['2.0', '3.0', '1.8.1'])
