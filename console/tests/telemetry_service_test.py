# -*- coding: utf-8 -*-
import datetime
import hashlib
import json

from django.test import TestCase
from django.utils import timezone
from unittest import mock

from console.models.main import ConsoleSysConfig
from console.services import telemetry as telemetry_module
from console.services.telemetry import (
    COMPONENT_BUILD_RESULT_KEY_PREFIX,
    FIRST_APP_DEPLOY_SUCCESS_KEY,
    HEARTBEAT_KEY_PREFIX,
    INSTANCE_ID_KEY,
    REGISTERED_KEY,
    RainbondTelemetryService,
    _get_enterprise_id,
    hash_identifier,
    sanitize_properties,
)
from console.services.telemetry_switch import (
    EXTERNAL_TELEMETRY_ENABLED_KEY,
    invalidate_external_telemetry_cache,
)
from www.models.main import TenantEnterprise


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


class ImmediateDispatcher(object):
    def submit(self, callback):
        return callback()


class DeferredDispatcher(object):
    def __init__(self):
        self.callback = None

    def submit(self, callback):
        self.callback = callback
        return True


class RainbondTelemetryServiceTests(TestCase):
    def setUp(self):
        ConsoleSysConfig.objects.filter(
            key=EXTERNAL_TELEMETRY_ENABLED_KEY,
        ).delete()
        ConsoleSysConfig.objects.filter(key__startswith=COMPONENT_BUILD_RESULT_KEY_PREFIX).delete()
        ConsoleSysConfig.objects.filter(key=FIRST_APP_DEPLOY_SUCCESS_KEY).delete()
        telemetry_module._enterprise_id_cache = None
        invalidate_external_telemetry_cache()

    def tearDown(self):
        ConsoleSysConfig.objects.filter(key__startswith=COMPONENT_BUILD_RESULT_KEY_PREFIX).delete()
        ConsoleSysConfig.objects.filter(key=FIRST_APP_DEPLOY_SUCCESS_KEY).delete()
        telemetry_module._enterprise_id_cache = None
        invalidate_external_telemetry_cache()

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

    def test_sanitize_properties_filters_posthog_group_key(self):
        sanitized = sanitize_properties({
            "$group_key": "a" * 32,
            "team_name": "private-team",
        })

        self.assertEqual(sanitized["$group_key"], "[Filtered]")
        self.assertEqual(sanitized["team_name"], "[Filtered]")

    def test_sanitize_properties_filters_non_anonymous_posthog_group_key(self):
        sanitized = sanitize_properties({"$group_key": "private-team"})

        self.assertEqual(sanitized["$group_key"], "[Filtered]")

    def test_build_payload_converts_local_timestamp_and_protects_instance_group(self):
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            now=lambda: datetime.datetime(2026, 6, 14, 1, 2, 3),
        )

        payload = service.build_payload("rainbond_instance_registered", {"$groups": {"instance": "other-instance"}})
        event = payload["batch"][0]

        self.assertEqual(event["timestamp"], "2026-06-13T17:02:03+00:00")
        self.assertEqual(event["properties"]["$groups"], {"instance": event["distinct_id"]})

    def test_build_payload_converts_aware_timestamp_to_utc(self):
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            now=lambda: datetime.datetime(2026, 6, 14, 1, 2, 3, tzinfo=datetime.timezone(datetime.timedelta(hours=8))),
        )

        payload = service.build_payload("rainbond_instance_registered")

        self.assertEqual(payload["batch"][0]["timestamp"], "2026-06-13T17:02:03+00:00")

    def test_instance_properties_include_anonymous_platform_metadata(self):
        TenantEnterprise.objects.create(enterprise_id="enterprise-a", enterprise_name="enterprise-a")
        service = RainbondTelemetryService(
            env={
                "RAINBOND_POSTHOG_ENABLED": "true",
                "RAINBOND_ARCH": "x86-64",
                "ENTERPRISE_ID": "environment-enterprise-id",
            },
        )

        properties = service.get_instance_properties()

        self.assertEqual(properties["enterprise_id_hash"], hashlib.md5(b"enterprise-a").hexdigest())
        self.assertEqual(properties["instance_arch"], "amd64")
        self.assertEqual(properties["edition"], "open_source")
        self.assertEqual(properties["telemetry_schema_version"], 2)
        self.assertNotIn("installation_method", properties)

    def test_get_enterprise_id_uses_creation_time_then_primary_key(self):
        null_time = TenantEnterprise.objects.create(enterprise_id="enterprise-null", enterprise_name="enterprise-null")
        first = TenantEnterprise.objects.create(enterprise_id="enterprise-a", enterprise_name="enterprise-a")
        second = TenantEnterprise.objects.create(enterprise_id="enterprise-b", enterprise_name="enterprise-b")
        create_time = datetime.datetime(2026, 6, 14, 1, 2, 3)
        TenantEnterprise.objects.filter(pk=null_time.pk).update(create_time=None)
        TenantEnterprise.objects.filter(pk=first.pk).update(create_time=create_time)
        TenantEnterprise.objects.filter(pk=second.pk).update(create_time=create_time)

        self.assertEqual(_get_enterprise_id(), "enterprise-a")

    def test_instance_properties_strips_enterprise_id_before_hashing(self):
        TenantEnterprise.objects.create(enterprise_id=" enterprise-a\n", enterprise_name="enterprise-a")
        service = RainbondTelemetryService(env={"RAINBOND_POSTHOG_ENABLED": "true"})

        properties = service.get_instance_properties()

        self.assertEqual(properties["enterprise_id_hash"], hashlib.md5(b"enterprise-a").hexdigest())

    def test_enterprise_id_query_failure_keeps_other_instance_properties(self):
        service = RainbondTelemetryService(env={"RAINBOND_POSTHOG_ENABLED": "true"})

        with mock.patch(
            "console.services.telemetry.TenantEnterprise.objects.order_by",
            side_effect=RuntimeError("database unavailable"),
        ), mock.patch("console.services.telemetry.logger.debug") as debug:
            properties = service.get_instance_properties()

        self.assertEqual(properties["instance_id"], service.get_or_create_instance_id())
        self.assertIn("console_version", properties)
        self.assertNotIn("enterprise_id_hash", properties)
        debug.assert_called_once()

    def test_enterprise_id_query_caches_found_value_but_not_missing_value(self):
        enterprise = mock.Mock(enterprise_id="enterprise-a")
        queryset = mock.Mock()
        queryset.first.return_value = enterprise

        with mock.patch("console.services.telemetry.TenantEnterprise.objects.order_by", return_value=queryset) as order_by:
            self.assertEqual(_get_enterprise_id(), "enterprise-a")
            self.assertEqual(_get_enterprise_id(), "enterprise-a")

        order_by.assert_called_once()
        telemetry_module._enterprise_id_cache = None
        queryset.first.return_value = None
        with mock.patch("console.services.telemetry.TenantEnterprise.objects.order_by", return_value=queryset) as order_by:
            self.assertEqual(_get_enterprise_id(), "")
            self.assertEqual(_get_enterprise_id(), "")

        self.assertEqual(order_by.call_count, 2)

    def test_instance_properties_use_enterprise_edition_and_omit_missing_enterprise_id(self):
        service = RainbondTelemetryService(
            env={
                "RAINBOND_POSTHOG_ENABLED": "true",
                "IS_ENTERPRISE_EDITION": "true",
                "RAINBOND_ARCH": "aarch64",
                "ENTERPRISE_ID": "environment-enterprise-id",
            },
        )

        properties = service.get_instance_properties()

        self.assertEqual(properties["edition"], "enterprise")
        self.assertEqual(properties["instance_arch"], "arm64")
        self.assertNotIn("enterprise_id_hash", properties)

    def test_unknown_environment_arch_falls_back_to_platform_architecture(self):
        service = RainbondTelemetryService(
            env={
                "RAINBOND_POSTHOG_ENABLED": "true",
                "RAINBOND_ARCH": "unsupported",
            },
        )

        with mock.patch("console.services.telemetry.platform.machine", return_value="aarch64"):
            properties = service.get_instance_properties()

        self.assertEqual(properties["instance_arch"], "arm64")

    def test_install_time_converts_to_utc(self):
        service = RainbondTelemetryService(env={"RAINBOND_POSTHOG_ENABLED": "true"})
        instance_id = service.get_or_create_instance_id()
        create_time = datetime.datetime(2026, 6, 14, 1, 2, 3)
        ConsoleSysConfig.objects.filter(key=INSTANCE_ID_KEY).update(create_time=create_time)

        self.assertEqual(service.get_install_time(), "2026-06-13T17:02:03+00:00")
        self.assertEqual(instance_id, service.get_or_create_instance_id())

    def test_install_time_converts_aware_value_to_utc(self):
        service = RainbondTelemetryService(env={"RAINBOND_POSTHOG_ENABLED": "true"})
        record = mock.Mock(create_time=datetime.datetime(
            2026,
            6,
            14,
            1,
            2,
            3,
            tzinfo=datetime.timezone(datetime.timedelta(hours=8)),
        ))
        queryset = mock.Mock()
        queryset.first.return_value = record

        with mock.patch("console.services.telemetry.ConsoleSysConfig.objects.filter", return_value=queryset):
            self.assertEqual(service.get_install_time(), "2026-06-13T17:02:03+00:00")

    def test_component_event_preserves_instance_and_component_architectures(self):
        transport = FakeTransport()
        component = type("Component", (), {
            "service_source": "",
            "category": "",
            "service_type": "",
            "language": "",
            "arch": "arm64",
        })()
        service = RainbondTelemetryService(
            env={
                "RAINBOND_POSTHOG_ENABLED": "true",
                "RAINBOND_ARCH": "x86_64",
            },
            transport=transport,
            dispatcher=ImmediateDispatcher(),
        )

        self.assertTrue(service.track_component_created(component=component))

        properties = transport.requests[0]["json"]["batch"][0]["properties"]
        self.assertEqual(properties["instance_arch"], "amd64")
        self.assertEqual(properties["arch"], "arm64")

    def test_capture_posts_batch_payload_with_public_token(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={
                "RAINBOND_POSTHOG_ENABLED": "true",
                "RAINBOND_POSTHOG_API_HOST": "https://posthog.example.com",
            },
            transport=transport,
            now=lambda: timezone.datetime(2026, 6, 14, 1, 2, 3, tzinfo=datetime.timezone.utc),
            dispatcher=ImmediateDispatcher(),
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
        enabled = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            transport=BrokenTransport(),
            dispatcher=ImmediateDispatcher(),
        )

        self.assertFalse(disabled.capture("rainbond_app_created", {}))
        self.assertFalse(enabled.capture("rainbond_app_created", {}))

    def test_capture_is_disabled_in_offline_mode_without_transport_request(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={"DISABLE_DEFAULT_APP_MARKET": "true"},
            transport=transport,
        )

        self.assertFalse(service.capture("rainbond_app_created", {}))
        self.assertEqual(transport.requests, [])

    def test_capture_is_disabled_by_platform_setting_without_transport_request(self):
        ConsoleSysConfig.objects.create(
            key=EXTERNAL_TELEMETRY_ENABLED_KEY,
            type="boolean",
            value="",
            enable=False,
            enterprise_id="",
        )
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            transport=transport,
        )

        self.assertFalse(service.capture("rainbond_app_created", {}))
        self.assertEqual(transport.requests, [])

    def test_track_registration_and_heartbeat_are_idempotent(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            transport=transport,
            now=lambda: timezone.datetime(2026, 6, 14, 1, 2, 3, tzinfo=datetime.timezone.utc),
            dispatcher=ImmediateDispatcher(),
        )

        self.assertTrue(service.track_instance_registered())
        self.assertFalse(service.track_instance_registered())
        self.assertTrue(service.track_instance_heartbeat())
        self.assertFalse(service.track_instance_heartbeat())

        events = [request["json"]["batch"][0]["event"] for request in transport.requests]
        self.assertEqual(events, ["rainbond_instance_registered", "rainbond_instance_heartbeat"])
        self.assertTrue(ConsoleSysConfig.objects.filter(key=REGISTERED_KEY).exists())
        self.assertTrue(ConsoleSysConfig.objects.filter(key=HEARTBEAT_KEY_PREFIX + "20260614").exists())

    def test_component_build_result_is_idempotent_and_uses_whitelisted_properties(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            transport=transport,
            dispatcher=ImmediateDispatcher(),
        )

        with mock.patch("console.services.telemetry.get_external_telemetry_enabled", return_value=True):
            self.assertTrue(service.track_first_component_build_result(
                service_id="service-1",
                attempt_id="attempt-1",
                deploy_type="source_code",
                language="java",
                success=False,
                error_code="compile_failed",
                attempt_id_source="frontend",
            ))
            self.assertFalse(RainbondTelemetryService(
                env={"RAINBOND_POSTHOG_ENABLED": "true"},
                transport=transport,
                dispatcher=ImmediateDispatcher(),
            ).track_first_component_build_result(
                service_id="service-1",
                attempt_id="attempt-2",
                deploy_type="unknown-source",
                language="private-language",
                success=False,
                error_code="untrusted error message",
            ))
            self.assertTrue(service.track_first_component_build_result(
                service_id="service-2",
                attempt_id="attempt-3",
                deploy_type="unknown-source",
                language="private-language",
                success=False,
                error_code="untrusted error message",
            ))

        properties = transport.requests[0]["json"]["batch"][0]["properties"]
        self.assertEqual(transport.requests[0]["json"]["batch"][0]["event"], "first_component_build_result")
        self.assertEqual(properties["attempt_id"], "attempt-1")
        self.assertEqual(properties["deploy_type"], "source_code")
        self.assertEqual(properties["language"], "java")
        self.assertFalse(properties["success"])
        self.assertEqual(properties["source"], "backend")
        self.assertEqual(properties["attempt_id_source"], "frontend")
        self.assertNotIn("stage", properties)
        self.assertEqual(properties["error_code"], "compile_failed")
        self.assertNotIn("service_id", properties)
        unknown_properties = transport.requests[1]["json"]["batch"][0]["properties"]
        self.assertEqual(unknown_properties["deploy_type"], "other")
        self.assertNotIn("language", unknown_properties)
        self.assertNotIn("stage", unknown_properties)
        self.assertEqual(unknown_properties["error_code"], "unknown")

    def test_component_build_result_preserves_production_language_values(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"}, transport=transport, dispatcher=ImmediateDispatcher())

        with mock.patch("console.services.telemetry.get_external_telemetry_enabled", return_value=True):
            self.assertTrue(service.track_first_component_build_result(
                service_id="service-language", attempt_id="attempt-language", deploy_type="source_code",
                language="Java-maven", success=True))

        properties = transport.requests[0]["json"]["batch"][0]["properties"]
        self.assertEqual(properties["language"], "java-maven")

    def test_component_build_result_preserves_additional_builder_languages(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"}, transport=transport, dispatcher=ImmediateDispatcher())

        with mock.patch("console.services.telemetry.get_external_telemetry_enabled", return_value=True):
            for index, language in enumerate(("docker", "NodeJSDockerfile", "Clojure", "Grails", "OSS")):
                self.assertTrue(service.track_first_component_build_result(
                    service_id="service-language-{}".format(index), attempt_id="attempt-{}".format(index),
                    deploy_type="source_code", language=language, success=True))

        languages = [request["json"]["batch"][0]["properties"]["language"] for request in transport.requests]
        self.assertEqual(languages, ["docker", "nodejsdockerfile", "clojure", "grails", "oss"])

    def test_first_app_deploy_success_is_idempotent_across_service_instances(self):
        transport = FakeTransport()
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            transport=transport,
            dispatcher=ImmediateDispatcher(),
        )

        with mock.patch("console.services.telemetry.get_external_telemetry_enabled", return_value=True):
            self.assertTrue(service.track_first_app_deploy_success(
                attempt_id="attempt-1",
                deploy_type="image",
                language="",
            ))
            self.assertFalse(RainbondTelemetryService(
                env={"RAINBOND_POSTHOG_ENABLED": "true"},
                transport=transport,
                dispatcher=ImmediateDispatcher(),
            ).track_first_app_deploy_success(
                attempt_id="attempt-2",
                deploy_type="image",
                language="",
            ))

        events = [request["json"]["batch"][0]["event"] for request in transport.requests]
        self.assertEqual(events, ["first_app_deploy_success", "meaningful_active"])
        meaningful_properties = transport.requests[1]["json"]["batch"][0]["properties"]
        self.assertEqual(meaningful_properties["action_type"], "first_app_deploy")

    def test_capture_queues_network_send_after_business_request(self):
        transport = FakeTransport()
        dispatcher = DeferredDispatcher()
        service = RainbondTelemetryService(
            env={"RAINBOND_POSTHOG_ENABLED": "true"},
            transport=transport,
            dispatcher=dispatcher,
        )

        self.assertTrue(service.capture("rainbond_component_created", {}))
        self.assertEqual(transport.requests, [])
        dispatcher.callback()
        self.assertEqual(len(transport.requests), 1)

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
