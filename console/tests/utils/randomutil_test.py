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

from console.utils.randomutil import make_default_version


class RandomUtilTests(TestCase):
    # capability_id: console.random.default-version
    def test_make_default_version(self):
        version = make_default_version()
        self.assertEqual(len(version), 8)
        self.assertTrue(version.isalnum())
