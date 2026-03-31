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

from console.utils.runner_util import is_runner
from console.utils.slug_util import is_slug


class ImageClassifyTests(TestCase):
    # capability_id: console.image.slug-detect
    def test_is_slug(self):
        self.assertTrue(is_slug("goodrain.me/runner:latest", "python"))
        self.assertFalse(is_slug("goodrain.me/runner:latest", "dockerfile"))
        self.assertFalse(is_slug("example.com/custom:latest", "python"))

    # capability_id: console.image.runner-detect
    def test_is_runner(self):
        self.assertTrue(is_runner("goodrain.me/runner:latest"))
        self.assertFalse(is_runner("example.com/custom:latest"))
