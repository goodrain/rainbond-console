# -*- coding: utf-8 -*-
import json

from django.test import TestCase
from django.utils import timezone

from console.models.main import ConsoleSysConfig
from console.services.telemetry import (
    HEARTBEAT_KEY_PREFIX,
    INSTANCE_ID_KEY,
    REGISTERED_KEY,
    RainbondTelemetryService,
    hash_identifier,
    sanitize_properties,
)


class FakeTransport(object):
    def __init__(self):
        self.requests = []

    def post(self, url, data=None, json=None, headers=None, timeout=None):
        self.requests.append({
            "url": url,
            "data": data,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        })
        return type("Response", (), {"status_code": 200})()


class RainbondTelemetryServiceTests(TestCase):
    def test_get_or_create_instance_id_is_stable_and_anonymous(self):
        service = RainbondTelemetryService(env={"RAINBOND_POSTHOG_ENABLED": "true"})

        first = service.get_or_create_instance_id()
        second = service.get_or_create_instance_id()

        self.assertEqual(first, second)
        self.assertEqual(len(first), 32)
        self.assertEqual(ConsoleSysConfig.objects.filter(key=INSTANCE_ID_KEY).count(), 1)

    def test_sanitize_properties_filters_sensitive_values(self):
        sanitized = sanitize_properties({
            "module": "app_store",
            "token": "abc",
            "nested": {
                "git_url": "https://example.com/repo.git",
                "message": "authorization=Bearer secret token=abc",
            },
        })

        self.assertEqual(sanitized["module"], "app_store")
        self.assertEqual(sanitized["token"], "[Filtered]")
        self.assertEqual(sanitized["nested"]["git_url"], "[Filtered]")
        self.assertEqual(sanitized["nested"]["message"], "authorization=[Filtered] token=[Filtered]")

    def test_capture_posts_batch_payload_with_public_token(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={
                "RAINBOND_POSTHOG_ENABLED": "true",
                "RAINBOND_POSTHOG_API_HOST": "https://posthog.example.com",
            },
            transport=transport,
            now=lambda: timezone.datetime(2026, 6, 14, 1, 2, 3, tzinfo=timezone.utc),
        )

        sent = service.capture("rainbond_component_created", {
            "source_type": "image",
            "image": "private.example.com/app:latest",
        })

        self.assertTrue(sent)
        self.assertEqual(len(transport.requests), 1)
        request = transport.requests[0]
        self.assertEqual(request["url"], "https://posthog.example.com/batch/")
        payload = request["json"]
        self.assertIn("api_key", payload)
        self.assertEqual(payload["batch"][0]["event"], "rainbond_component_created")
        self.assertEqual(payload["batch"][0]["distinct_id"], service.get_or_create_instance_id())
        self.assertEqual(payload["batch"][0]["properties"]["source_type"], "image")
        self.assertEqual(payload["batch"][0]["properties"]["image"], "[Filtered]")

    def test_capture_is_disabled_by_global_switch_and_never_raises_on_transport_error(self):
        class BrokenTransport(object):
            def post(self, *args, **kwargs):
                raise RuntimeError("network down")

        disabled = RainbondTelemetryService(env={"RAINBOND_TELEMETRY_DISABLED": "true"}, transport=BrokenTransport())
        enabled = RainbondTelemetryService(env={"RAINBOND_POSTHOG_ENABLED": "true"}, transport=BrokenTransport())

        self.assertFalse(disabled.capture("rainbond_app_created", {}))
        self.assertFalse(enabled.capture("rainbond_app_created", {}))

    def test_track_registration_and_heartbeat_are_idempotent(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            transport=transport,
            now=lambda: timezone.datetime(2026, 6, 14, 1, 2, 3, tzinfo=timezone.utc),
        )

        self.assertTrue(service.track_instance_registered())
        self.assertFalse(service.track_instance_registered())
        self.assertTrue(service.track_instance_heartbeat())
        self.assertFalse(service.track_instance_heartbeat())

        events = [request["json"]["batch"][0]["event"] for request in transport.requests]
        self.assertEqual(events, ["rainbond_instance_registered", "rainbond_instance_heartbeat"])
        self.assertTrue(ConsoleSysConfig.objects.filter(key=REGISTERED_KEY).exists())
        self.assertTrue(ConsoleSysConfig.objects.filter(key=HEARTBEAT_KEY_PREFIX + "20260614").exists())

    def test_hash_identifier_is_instance_scoped(self):
        self.assertNotEqual(hash_identifier("instance-a", 1), hash_identifier("instance-b", 1))
        self.assertEqual(hash_identifier("instance-a", 1), hash_identifier("instance-a", "1"))

    def test_frontend_posthog_config_includes_instance_metadata(self):
        from goodrain_web import sentry_config

        raw = sentry_config.get_frontend_posthog_config_json({"RAINBOND_POSTHOG_ENABLED": "true"})
        config = json.loads(raw)

        self.assertEqual(config["instanceId"], ConsoleSysConfig.objects.get(key=INSTANCE_ID_KEY).value)
        self.assertEqual(config["instanceProperties"]["instance_id"], config["instanceId"])
        self.assertIn("console_version", config["instanceProperties"])
