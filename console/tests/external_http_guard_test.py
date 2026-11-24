# -*- coding: utf-8 -*-
# capability_id: console.tests.external-http-guard
import os

import requests

from django.test import SimpleTestCase
from console.utils.offline import is_external_telemetry_disabled
from goodrain_web.sentry_config import get_frontend_posthog_config, get_sentry_config


class ExternalHttpGuardTests(SimpleTestCase):

    def test_disables_external_telemetry(self):
        sentry_env = dict(os.environ, SENTRY_DSN="https://sentry.example.invalid/1")

        self.assertTrue(is_external_telemetry_disabled())
        self.assertFalse(get_sentry_config(sentry_env)["enabled"])
        self.assertFalse(get_frontend_posthog_config()["enabled"])

    def test_blocks_external_requests_before_transport(self):
        with self.assertRaisesRegex(RuntimeError, "external HTTP requests are disabled during tests"):
            requests.get("https://example.invalid")
