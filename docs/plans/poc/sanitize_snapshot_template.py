"""
M3 Phase 1: Sanitize a Dify snapshot template for safe, portable publishing.

Reads the snapshot template JSON (from get_app_version_snapshot_detail),
replaces sensitive env values and gateway-specific URLs with empty strings,
and outputs the modified share_service_list ready for create_app_version_snapshot.

Usage:
    python sanitize_snapshot_template.py < snapshot_template.json > share_service_list.json
"""

import json
import sys

SENSITIVE_ENV_NAMES = {
    "SECRET_KEY",
    "POSTGRES_PASSWORD",
    "DB_PASSWORD",
    "WEAVIATE_API_KEY",
    "AUTHENTICATION_APIKEY_ALLOWED_KEYS",
    "API_KEY",
    "CODE_EXECUTION_API_KEY",
    "PLUGIN_DAEMON_KEY",
    "SERVER_KEY",
    "INNER_API_KEY_FOR_PLUGIN",
    "PLUGIN_DIFY_INNER_API_KEY",
    "DIFY_INNER_API_KEY",
}

GATEWAY_URL_ENV_NAMES = {
    "CONSOLE_WEB_URL",
    "APP_WEB_URL",
    "CONSOLE_API_URL",
    "APP_API_URL",
}


def sanitize_envs(env_list, component_name):
    sanitized = []
    changes = []
    for env in env_list:
        attr_name = env.get("attr_name", "")
        if attr_name in SENSITIVE_ENV_NAMES:
            changes.append(f"  {component_name}.{attr_name}: '{env['attr_value'][:8]}...' -> ''")
            env = dict(env, attr_value="")
        elif attr_name in GATEWAY_URL_ENV_NAMES:
            changes.append(f"  {component_name}.{attr_name}: '{env['attr_value']}' -> ''")
            env = dict(env, attr_value="")
        sanitized.append(env)
    return sanitized, changes


def sanitize_template(template):
    apps = template.get("apps", [])
    all_changes = []
    sanitized_apps = []

    for app in apps:
        component_name = app.get("service_cname", app.get("service_alias", "unknown"))
        modified = dict(app)

        inner_envs, changes1 = sanitize_envs(
            modified.get("service_env_map_list", []), component_name
        )
        modified["service_env_map_list"] = inner_envs
        all_changes.extend(changes1)

        outer_envs, changes2 = sanitize_envs(
            modified.get("service_connect_info_map_list", []), component_name
        )
        modified["service_connect_info_map_list"] = outer_envs
        all_changes.extend(changes2)

        sanitized_apps.append(modified)

    return sanitized_apps, all_changes


def main():
    template = json.load(sys.stdin)
    sanitized_apps, changes = sanitize_template(template)

    print(f"Sanitized {len(changes)} env values:", file=sys.stderr)
    for change in changes:
        print(change, file=sys.stderr)

    json.dump(sanitized_apps, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
