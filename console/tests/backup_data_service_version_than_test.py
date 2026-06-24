# -*- coding: utf-8 -*-
import collections
import collections.abc
import os
import sys
import tempfile
from types import ModuleType
from unittest import TestCase, mock

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from console.services.backup_data_service import PlatformDataBackupServices  # noqa: E402


# capability_id: console.app-backup.version-check
class VersionThanTests(TestCase):
    def setUp(self):
        self.service = PlatformDataBackupServices()

    def _write_version(self, backup_path, content):
        with open(os.path.join(backup_path, "version"), "w") as f:
            f.write(content)

    def test_matching_version_does_not_raise(self):
        with tempfile.TemporaryDirectory() as backup_path:
            self._write_version(backup_path, "v1.2.3")
            with mock.patch("console.services.backup_data_service.settings") as settings_mock:
                settings_mock.VERSION = "v1.2.3"
                # Should not raise.
                self.assertIsNone(self.service.version_than(backup_path))

    def test_mismatched_version_raises_service_handle_exception(self):
        with tempfile.TemporaryDirectory() as backup_path:
            self._write_version(backup_path, "v0.0.1")
            with mock.patch("console.services.backup_data_service.settings") as settings_mock:
                settings_mock.VERSION = "v9.9.9"
                with self.assertRaises(ServiceHandleException):
                    self.service.version_than(backup_path)
