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

from console.utils.urlutil import is_path_legal
from console.utils.urlutil import set_get_url


class UrlUtilTests(TestCase):
    # capability_id: console.url.path-legal
    def test_is_path_legal(self):
        self.assertTrue(is_path_legal("/foo/bar.txt"))
        self.assertTrue(is_path_legal("/foo-bar/baz_qux.yaml"))
        self.assertTrue(is_path_legal("/foo/../bar"))
        self.assertFalse(is_path_legal("foo/bar.txt"))

    # capability_id: console.url.query-build
    def test_set_get_url(self):
        url = set_get_url("/console/api", {"page": "1", "q": "demo"})
        self.assertEqual(url, "/console/api?page=1&q=demo")

    # capability_id: console.url.query-empty
    def test_set_get_url_with_empty_params(self):
        url = set_get_url("/console/api", {})
        self.assertEqual(url, "/console/api?")
