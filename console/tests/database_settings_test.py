# -*- coding: utf-8 -*-
import importlib
import os
import unittest
from contextlib import contextmanager
from unittest import mock

from goodrain_web import settings


# capability_id: console.database.dm-settings-selection
class DatabaseSettingsTests(unittest.TestCase):

    @contextmanager
    def settings_with_environment(self, environment):
        with mock.patch.dict(os.environ, environment, clear=True):
            yield importlib.reload(settings)
        importlib.reload(settings)

    def test_dm_uses_generic_database_environment(self):
        environment = {
            "DB_TYPE": "dm",
            "DB_NAME": "console_dm",
            "DB_USER": "console_user",
            "DB_PASSWORD": "$TEST_DB_PASSWORD",
            "DB_HOST": "dm.example.invalid",
            "DB_PORT": "5236",
            "MYSQL_DB": "legacy_console",
            "MYSQL_USER": "legacy_user",
            "MYSQL_PASS": "$LEGACY_DB_PASSWORD",
            "MYSQL_HOST": "legacy.example.invalid",
            "MYSQL_PORT": "3306",
        }

        with self.settings_with_environment(environment) as configured_settings:
            database = configured_settings.DATABASES["default"]

        self.assertEqual(database["ENGINE"], "dmDjango")
        self.assertEqual(database["NAME"], "console_dm")
        self.assertEqual(database["USER"], "console_user")
        self.assertEqual(database["PASSWORD"], "$TEST_DB_PASSWORD")
        self.assertEqual(database["HOST"], "dm.example.invalid")
        self.assertEqual(database["PORT"], "5236")
        self.assertEqual(database["OPTIONS"], {"schema": "CONSOLE_DM"})

    def test_dm_falls_back_to_legacy_mysql_environment(self):
        environment = {
            "DB_TYPE": "dm",
            "MYSQL_DB": "legacy_console",
            "MYSQL_USER": "legacy_user",
            "MYSQL_PASS": "$LEGACY_DB_PASSWORD",
            "MYSQL_HOST": "legacy.example.invalid",
            "MYSQL_PORT": "3306",
        }

        with self.settings_with_environment(environment) as configured_settings:
            database = configured_settings.DATABASES["default"]

        self.assertEqual(database["ENGINE"], "dmDjango")
        self.assertEqual(database["NAME"], "legacy_console")
        self.assertEqual(database["USER"], "legacy_user")
        self.assertEqual(database["PASSWORD"], "$LEGACY_DB_PASSWORD")
        self.assertEqual(database["HOST"], "legacy.example.invalid")
        self.assertEqual(database["PORT"], "3306")
        self.assertEqual(database["OPTIONS"], {"schema": "LEGACY_CONSOLE"})

    def test_mysql_configuration_remains_unchanged(self):
        environment = {
            "DB_TYPE": "mysql",
            "MYSQL_DB": "console_mysql",
            "MYSQL_USER": "console_user",
            "MYSQL_PASS": "$TEST_DB_PASSWORD",
            "MYSQL_HOST": "mysql.example.invalid",
            "MYSQL_PORT": "3306",
        }

        with self.settings_with_environment(environment) as configured_settings:
            database = configured_settings.DATABASES["default"]

        self.assertEqual(database["ENGINE"], "django.db.backends.mysql")
        self.assertEqual(database["NAME"], "console_mysql")
        self.assertEqual(database["USER"], "console_user")
        self.assertEqual(database["PASSWORD"], "$TEST_DB_PASSWORD")
        self.assertEqual(database["HOST"], "mysql.example.invalid")
        self.assertEqual(database["PORT"], "3306")


if __name__ == "__main__":
    unittest.main()
