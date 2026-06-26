"""
M3 Phase 1b: Sanitize snapshot template using **None:group** placeholders.

Instead of emptying sensitive env values (requiring post-install injection),
this version uses **None:group_name** so the platform auto-generates consistent
secrets at install time — enabling true one-click install.

Usage:
    python sanitize_snapshot_template_v2.py < snapshot_template.json > share_service_list.json
"""

import json
import sys

SECRET_GROUPS = {
    "SECRET_KEY": "**None:secret_key**",
    "POSTGRES_PASSWORD": "**None:db_password**",
    "DB_PASSWORD": "**None:db_password**",
    "WEAVIATE_API_KEY": "**None:weaviate_key**",
    "AUTHENTICATION_APIKEY_ALLOWED_KEYS": "**None:weaviate_key**",
    "API_KEY": "**None:sandbox_key**",
    "CODE_EXECUTION_API_KEY": "**None:sandbox_key**",
    "PLUGIN_DAEMON_KEY": "**None:daemon_key**",
    "SERVER_KEY": "**None:daemon_key**",
    "INNER_API_KEY_FOR_PLUGIN": "**None:inner_key**",
    "PLUGIN_DIFY_INNER_API_KEY": "**None:inner_key**",
    "DIFY_INNER_API_KEY": "**None:inner_key**",
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
        if attr_name in SECRET_GROUPS:
            placeholder = SECRET_GROUPS[attr_name]
            changes.append(f"  {component_name}.{attr_name} -> {placeholder}")
            env = dict(env, attr_value=placeholder)
        elif attr_name in GATEWAY_URL_ENV_NAMES:
            changes.append(f"  {component_name}.{attr_name} -> ''")
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

    print(f"Parameterized {len(changes)} env values:", file=sys.stderr)
    for change in changes:
        print(change, file=sys.stderr)

    json.dump(sanitized_apps, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
