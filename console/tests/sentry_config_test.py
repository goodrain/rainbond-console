# -*- coding: utf-8 -*-
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

    sanitized = sentry_config.before_send(event, {})

    assert sanitized["request"] == {
        "method": "GET",
        "url": "/console/teams/:id/apps/:id/overview?[Filtered]",
    }
    assert sanitized["message"] == "authorization=[Filtered] token=[Filtered] name=app"


def test_get_path_pattern_removes_dynamic_segments_and_query():
    assert (
        sentry_config.get_path_pattern(
            "/console/teams/team-a/apps/123456/overview?token=abc"
        )
        == "/console/teams/:id/apps/:id/overview?[Filtered]"
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
