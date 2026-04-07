# coding: utf-8
from unittest import TestCase

import os
import sys
from datetime import datetime
from types import ModuleType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django

django.setup()

from console.utils.timeutil import str_to_time
from console.utils.timeutil import current_time
from console.utils.timeutil import current_time_str
from console.utils.timeutil import current_time_to_str
from console.utils.timeutil import time_to_str


class TimeUtilTests(TestCase):
    # capability_id: console.timeutil.format
    def test_time_to_str(self):
        dt = datetime(2026, 3, 29, 10, 30)
        self.assertEqual(time_to_str(dt), "2026-03-29 10:30")

    # capability_id: console.timeutil.parse
    def test_str_to_time(self):
        dt = str_to_time("2026-03-29 10:30")
        self.assertEqual(dt, datetime(2026, 3, 29, 10, 30))

    # capability_id: console.timeutil.current-time
    def test_current_time(self):
        now = current_time()
        self.assertIsInstance(now, datetime)

    # capability_id: console.timeutil.current-time-str
    def test_current_time_str(self):
        value = current_time_str()
        self.assertIsInstance(value, str)
        self.assertEqual(len(value), 16)

    # capability_id: console.timeutil.current-date-str
    def test_current_time_to_str(self):
        value = current_time_to_str()
        self.assertIsInstance(value, str)
        self.assertEqual(len(value), 10)
