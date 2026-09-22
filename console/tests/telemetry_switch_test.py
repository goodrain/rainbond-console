# -*- coding: utf-8 -*-
import os

from django.db import OperationalError
from django.test import TestCase
from unittest import mock

from console.models.main import ConsoleSysConfig
from console.services.telemetry_switch import (
    EXTERNAL_TELEMETRY_ENABLED_KEY,
    get_external_telemetry_enabled,
    invalidate_external_telemetry_cache,
    set_external_telemetry_enabled,
)


class ExternalTelemetrySwitchTests(TestCase):
    def setUp(self):
        ConsoleSysConfig.objects.filter(
            key=EXTERNAL_TELEMETRY_ENABLED_KEY,
        ).delete()
        invalidate_external_telemetry_cache()

    def tearDown(self):
        invalidate_external_telemetry_cache()

    def test_missing_setting_defaults_to_enabled(self):
        self.assertTrue(get_external_telemetry_enabled({}))

    def test_setting_can_disable_external_telemetry(self):
        set_external_telemetry_enabled(False)

        self.assertFalse(get_external_telemetry_enabled({}))

    def test_environment_switch_overrides_database_setting(self):
        set_external_telemetry_enabled(True)

        with mock.patch.dict(
                os.environ,
                {"RAINBOND_TELEMETRY_DISABLED": "true"},
                clear=True,
        ):
            self.assertFalse(get_external_telemetry_enabled())

    def test_database_error_fails_closed(self):
        with mock.patch(
            "console.services.telemetry_switch._load_external_telemetry_setting",
            side_effect=RuntimeError("database unavailable"),
        ):
            self.assertFalse(get_external_telemetry_enabled({}))

    def test_operational_error_retries_after_closing_connections(self):
        setting = mock.Mock(enable=True)

        with mock.patch(
            "console.services.telemetry_switch._load_external_telemetry_setting",
            side_effect=[OperationalError(2006, "Server has gone away"), setting],
        ) as mock_load, mock.patch(
            "console.services.telemetry_switch.connections.close_all",
        ) as mock_close_all:
            self.assertTrue(get_external_telemetry_enabled({}))

        self.assertEqual(mock_load.call_count, 2)
        mock_close_all.assert_called_once_with()

    def test_repeated_operational_error_fails_closed(self):
        with mock.patch(
            "console.services.telemetry_switch._load_external_telemetry_setting",
            side_effect=[
                OperationalError(2006, "Server has gone away"),
                OperationalError(2013, "Lost connection to MySQL server"),
            ],
        ) as mock_load, mock.patch(
            "console.services.telemetry_switch.connections.close_all",
        ) as mock_close_all:
            self.assertFalse(get_external_telemetry_enabled({}))

        self.assertEqual(mock_load.call_count, 2)
        self.assertEqual(mock_close_all.call_count, 2)
