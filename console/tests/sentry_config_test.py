# -*- coding: utf-8 -*-
from unittest import mock

from django.db import OperationalError
import requests

from console.exception.exceptions import ConfigExistError
from goodrain_web import sentry_config


DEFAULT_POSTHOG_PROJECT_TOKEN = "phc_oCoPwcxutKCU9AZtUT63dMTNhWezUxCXCLtSZE6a4wvE"
DEFAULT_POSTHOG_API_HOST = "/console/posthog"
DEFAULT_POSTHOG_UI_HOST = "https://posthog.goodrain.com"
DEFAULT_SENTRY_TUNNEL = "/console/sentry"


def test_sentry_config_stays_disabled_without_dsn():
    config = sentry_config.get_sentry_config({})

    assert config["enabled"] is False


def test_sentry_config_reads_env_and_clamps_sample_rate():
    config = sentry_config.get_sentry_config({
        "RAINBOND_ERROR_REPORTING_DSN": "https://example.invalid/1",
        "RAINBOND_ERROR_REPORTING_ENVIRONMENT": "production",
        "RAINBOND_ERROR_REPORTING_RELEASE": "v6.9.1-dev",
        "SENTRY_TRACES_SAMPLE_RATE": "3",
    })

    assert config == {
        "enabled": True,
        "dsn": "https://example.invalid/1",
        "environment": "production",
        "release": "v6.9.1-dev",
        "traces_sample_rate": 1.0,
    }


def test_console_dsn_takes_precedence_over_backend_and_shared_dsn():
    config = sentry_config.get_sentry_config({
        "RAINBOND_ERROR_REPORTING_DSN": "https://shared.example.invalid/1",
        "RAINBOND_ERROR_REPORTING_BACKEND_DSN": "https://backend.example.invalid/2",
        "RAINBOND_ERROR_REPORTING_CONSOLE_DSN": "https://console.example.invalid/3",
    })

    assert config["enabled"] is True
    assert config["dsn"] == "https://console.example.invalid/3"


def test_console_scoped_disable_wins_over_backend_dsn():
    config = sentry_config.get_sentry_config({
        "RAINBOND_ERROR_REPORTING_CONSOLE_ENABLED": "false",
        "RAINBOND_ERROR_REPORTING_BACKEND_DSN": "https://backend.example.invalid/2",
    })

    assert config["enabled"] is False


def test_telemetry_disabled_switch_wins():
    config = sentry_config.get_sentry_config({
        "RAINBOND_TELEMETRY_DISABLED": "true",
        "RAINBOND_ERROR_REPORTING_DSN": "https://example.invalid/1",
    })

    assert config["enabled"] is False


def test_before_send_filters_sensitive_request_data():
    event = {
        "request": {
            "url": (
                "https://rainbond.example.com/console/teams/team-a/"
                "apps/app-1/overview?token=abc&page=1"
            ),
            "query_string": "token=abc&page=1",
            "headers": {"Authorization": "secret", "X-Team": "team-a"},
            "data": {"password": "pw", "name": "app"},
            "method": "GET",
        },
        "message": "authorization=Bearer abc token=def name=app",
    }

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        sanitized = sentry_config.before_send(event, {})

    assert sanitized["request"] == {
        "method": "GET",
        "url": "/console/teams/:id/apps/:id/overview?[Filtered]",
    }
    assert sanitized["message"] == "authorization=[Filtered] token=[Filtered] name=app"


def test_before_send_drops_events_when_platform_telemetry_is_disabled():
    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=False):
        assert sentry_config.before_send({"message": "error"}, {}) is None


# capability_id: console.sentry.expected-region-frequent-error
def test_before_send_drops_region_api_frequent_operation_exception():
    frequent_error_type = type(
        "CallApiFrequentError",
        (Exception, ),
        {"__module__": "www.apiclient.regionapibaseclient"},
    )
    error = frequent_error_type("operation too frequent")

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        result = sentry_config.before_send(
            {"message": "operation too frequent"},
            {"exc_info": (frequent_error_type, error, None)},
        )
        type_only_result = sentry_config.before_send(
            {"message": "operation too frequent"},
            {"exc_info": (frequent_error_type, None, None)},
        )

    assert result is None
    assert type_only_result is None


def test_before_send_keeps_same_exception_name_from_other_modules():
    other_error_type = type(
        "CallApiFrequentError",
        (Exception, ),
        {"__module__": "tests.fake_region_client"},
    )
    error = other_error_type("unexpected frequent error")

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        result = sentry_config.before_send(
            {"message": "unexpected frequent error"},
            {"exc_info": (other_error_type, error, None)},
        )

    assert result == {"message": "unexpected frequent error"}


# capability_id: console.sentry.expected-not-found-errors
def test_before_send_drops_expected_not_found_exceptions():
    http404_type = type("Http404", (Exception, ), {"__module__": "django.http.response"})
    service_error_type = type(
        "ServiceHandleException",
        (Exception, ),
        {"__module__": "console.exception.main"},
    )
    region_error_type = type(
        "CallApiError",
        (Exception, ),
        {"__module__": "www.apiclient.regionapibaseclient"},
    )
    errors = [
        http404_type("not found"),
        service_error_type("application not found"),
        region_error_type("region resource not found"),
    ]
    errors[1].status_code = 404
    errors[2].status = 404

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        results = [
            sentry_config.before_send(
                {"message": str(error)},
                {"exc_info": (error.__class__, error, None)},
            )
            for error in errors
        ]

    assert results == [None, None, None]


# capability_id: console.config.expected-conflict
def test_before_send_drops_expected_config_conflict():
    error = ConfigExistError("配置GLOBAL_IMAGE_REGISTRY已存在")

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        result = sentry_config.before_send(
            {"message": str(error)},
            {"exc_info": (ConfigExistError, error, None)},
        )

    assert result is None


def test_before_send_keeps_server_side_service_and_region_errors():
    service_error_type = type(
        "ServiceHandleException",
        (Exception, ),
        {"__module__": "console.exception.main"},
    )
    region_error_type = type(
        "CallApiError",
        (Exception, ),
        {"__module__": "www.apiclient.regionapibaseclient"},
    )
    service_error = service_error_type("service failed")
    service_error.status_code = 500
    region_error = region_error_type("region failed")
    region_error.status = 500

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        service_result = sentry_config.before_send(
            {"message": "service failed"},
            {"exc_info": (service_error_type, service_error, None)},
        )
        region_result = sentry_config.before_send(
            {"message": "region failed"},
            {"exc_info": (region_error_type, region_error, None)},
        )

    assert service_result == {"message": "service failed"}
    assert region_result == {
        "message": "region failed",
        "fingerprint": ["region-upstream-error", "unknown"],
    }


# capability_id: console.region-api.upstream-server-error
def test_before_send_groups_region_server_errors_by_normalized_upstream_path():
    region_error_type = type(
        "CallApiError",
        (Exception, ),
        {"__module__": "www.apiclient.regionapibaseclient"},
    )
    error = region_error_type("plugin unavailable")
    error.status = 500
    error.url = "https://rbd-api-api:8443/v2/tenants/demo/services/gr123456/pods/pod-abc/detail"

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        result = sentry_config.before_send(
            {"message": "plugin unavailable"},
            {"exc_info": (region_error_type, error, None)},
        )

    assert result["fingerprint"] == [
        "region-upstream-error",
        "/v2/tenants/:id/services/:id/pods/pod-abc/detail",
    ]


# capability_id: console.database.transient-unavailable
def test_before_send_groups_transient_database_outages_with_stable_fingerprint():
    error = OperationalError(2006, "Server has gone away")
    event = {
        "message": "Server has gone away",
        "request": {
            "url": "/console/teams/demo/apps",
            "method": "GET",
        },
    }

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        result = sentry_config.before_send(
            event,
            {"exc_info": (OperationalError, error, None)},
        )

    assert result["fingerprint"] == ["database-unavailable"]
    assert result["request"]["url"] == "/console/teams/:id/apps"

    schema_error = OperationalError(1051, "Unknown table 'console_ci.mcp_device_authorization'")
    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        schema_result = sentry_config.before_send(
            {"message": "Unknown table"},
            {"exc_info": (OperationalError, schema_error, None)},
        )
    assert "fingerprint" not in schema_result


# capability_id: console.external-http.unavailable-response
def test_before_send_groups_external_http_failures_by_host_and_path():
    error = requests.exceptions.SSLError("bad tls")
    error.request = mock.Mock(url="https://ghcr.io/v2/_catalog?last=demo/image")

    with mock.patch("goodrain_web.sentry_config.is_external_telemetry_enabled", return_value=True):
        result = sentry_config.before_send(
            {"message": "bad tls"},
            {"exc_info": (requests.exceptions.SSLError, error, None)},
        )

    assert result["fingerprint"] == [
        "external-http-unavailable",
        "ghcr.io",
        "/v2/_catalog?[Filtered]",
    ]


def test_get_path_pattern_removes_dynamic_segments_and_query():
    assert (
        sentry_config.get_path_pattern(
            "/console/teams/team-a/apps/123456/overview?token=abc"
        )
        == "/console/teams/:id/apps/:id/overview?[Filtered]"
    )
    assert (
        sentry_config.get_path_pattern(
            "/console/team/team-a/region/bj/apps/app-1/overview?token=abc"
        )
        == "/console/team/:id/region/:id/apps/:id/overview?[Filtered]"
    )


def test_frontend_config_only_exposes_dsn_when_enabled():
    disabled = sentry_config.get_frontend_sentry_config({
        "RAINBOND_ERROR_REPORTING_ENABLED": "false",
        "RAINBOND_ERROR_REPORTING_DSN": "https://example.invalid/1",
    })
    enabled = sentry_config.get_frontend_sentry_config({
        "RAINBOND_ERROR_REPORTING_DSN": "https://example.invalid/1",
        "SENTRY_TRACES_SAMPLE_RATE": "0.2",
    })

    assert disabled["dsn"] == ""
    assert enabled["dsn"] == "https://example.invalid/1"
    assert enabled["tunnel"] == DEFAULT_SENTRY_TUNNEL
    assert enabled["tracesSampleRate"] == 0.2


def test_frontend_dsn_takes_precedence_over_shared_dsn():
    config = sentry_config.get_frontend_sentry_config({
        "RAINBOND_ERROR_REPORTING_DSN": "https://shared.example.invalid/1",
        "RAINBOND_ERROR_REPORTING_FRONTEND_DSN": "https://browser.example.invalid/2",
    })

    assert config["enabled"] is True
    assert config["dsn"] == "https://browser.example.invalid/2"


def test_offline_mode_disables_frontend_and_console_sentry():
    env = {
        "DISABLE_DEFAULT_APP_MARKET": "true",
        "RAINBOND_ERROR_REPORTING_DSN": "https://example.invalid/1",
    }

    frontend_config = sentry_config.get_frontend_sentry_config(env)
    console_config = sentry_config.get_sentry_config(env)

    assert frontend_config["enabled"] is False
    assert frontend_config["dsn"] == ""
    assert console_config["enabled"] is False
    assert console_config["dsn"] == "https://example.invalid/1"


def test_cloud_market_disable_does_not_disable_frontend_sentry():
    config = sentry_config.get_frontend_sentry_config({
        "DISABLE_CLOUD_MARKET": "true",
        "RAINBOND_ERROR_REPORTING_DSN": "https://example.invalid/1",
    })

    assert config["enabled"] is True
    assert config["dsn"] == "https://example.invalid/1"


def test_frontend_sentry_tunnel_can_be_overridden():
    config = sentry_config.get_frontend_sentry_config({
        "RAINBOND_ERROR_REPORTING_DSN": "https://example.invalid/1",
        "RAINBOND_ERROR_REPORTING_FRONTEND_TUNNEL": "/custom/sentry",
    })

    assert config["enabled"] is True
    assert config["tunnel"] == "/custom/sentry"


def test_frontend_config_json_is_valid_json():
    raw = sentry_config.get_frontend_sentry_config_json({
        "RAINBOND_ERROR_REPORTING_DSN": "https://example.invalid/1",
    })

    assert '"dsn":"https://example.invalid/1"' in raw
    assert '"tunnel":"/console/sentry"' in raw


def test_frontend_posthog_config_defaults_to_enabled_without_env_token():
    config = sentry_config.get_frontend_posthog_config({})

    assert config["enabled"] is True
    assert config["projectToken"] == DEFAULT_POSTHOG_PROJECT_TOKEN
    assert config["apiHost"] == DEFAULT_POSTHOG_API_HOST
    assert config["uiHost"] == DEFAULT_POSTHOG_UI_HOST
    assert config["personProfiles"] == "identified_only"
    assert config["maskAllText"] is False
    assert config["maskAllElementAttributes"] is True
    assert config["disableFlags"] is True


def test_frontend_posthog_config_ignores_env_project_token():
    config = sentry_config.get_frontend_posthog_config({
        "RAINBOND_POSTHOG_PROJECT_TOKEN": "project-token",
    })

    assert config["enabled"] is True
    assert config["projectToken"] == DEFAULT_POSTHOG_PROJECT_TOKEN
    assert config["apiHost"] == DEFAULT_POSTHOG_API_HOST
    assert config["uiHost"] == DEFAULT_POSTHOG_UI_HOST
    assert config["personProfiles"] == "identified_only"
    assert config["maskAllText"] is False
    assert config["maskAllElementAttributes"] is True
    assert config["disableFlags"] is True


def test_frontend_posthog_config_respects_disabled_switches():
    config = sentry_config.get_frontend_posthog_config({
        "RAINBOND_TELEMETRY_DISABLED": "true",
        "RAINBOND_POSTHOG_PROJECT_TOKEN": "project-token",
    })
    scoped_config = sentry_config.get_frontend_posthog_config({
        "RAINBOND_POSTHOG_DISABLED": "true",
        "RAINBOND_POSTHOG_PROJECT_TOKEN": "project-token",
    })

    assert config["enabled"] is False
    assert config["projectToken"] == ""
    assert scoped_config["enabled"] is False


def test_frontend_posthog_config_is_disabled_in_offline_mode():
    config = sentry_config.get_frontend_posthog_config({
        "DISABLE_DEFAULT_APP_MARKET": "true",
    })

    assert config["enabled"] is False
    assert config["projectToken"] == ""


def test_frontend_posthog_config_can_mask_click_text_when_requested():
    config = sentry_config.get_frontend_posthog_config({
        "RAINBOND_POSTHOG_PROJECT_TOKEN": "project-token",
        "RAINBOND_POSTHOG_MASK_ALL_TEXT": "true",
    })

    assert config["maskAllText"] is True


def test_frontend_posthog_config_json_escapes_script_sensitive_chars():
    raw = sentry_config.get_frontend_posthog_config_json({
        "RAINBOND_POSTHOG_PROJECT_TOKEN": "project-token",
        "RAINBOND_POSTHOG_API_HOST": "https://posthog.example.com/<tag>",
    })

    assert "\\u003ctag\\u003e" in raw
