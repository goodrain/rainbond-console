# -*- coding: utf8 -*-
"""CNB build env helpers."""

CNB_BUILD_ENV_NAMES = (
    "CNB_FRAMEWORK",
    "CNB_BUILD_SCRIPT",
    "CNB_OUTPUT_DIR",
    "CNB_NODE_VERSION",
    "CNB_NODE_ENV",
    "CNB_PACKAGE_TOOL",
    "CNB_MIRROR_SOURCE",
    "CNB_MIRROR_NPMRC",
    "CNB_MIRROR_YARNRC",
    "CNB_MIRROR_PNPMRC",
    "CNB_START_SCRIPT",
    "BUILD_HAS_NPMRC",
    "BUILD_HAS_YARNRC",
)

CNB_BUILD_ENV_ALIASES = (
    "TYPE",
    "HAS_NPMRC",
    "HAS_YARNRC",
)

CNB_PARAMS_FOR_BUILD_TYPE = (
    "CNB_FRAMEWORK",
    "CNB_BUILD_SCRIPT",
    "CNB_OUTPUT_DIR",
    "CNB_NODE_VERSION",
    "CNB_NODE_ENV",
    "CNB_MIRROR_SOURCE",
    "CNB_MIRROR_NPMRC",
    "CNB_MIRROR_YARNRC",
    "CNB_MIRROR_PNPMRC",
    "CNB_START_SCRIPT",
)


def normalize_language(language):
    return (language or "").replace(".", "").strip().lower()


def is_nodejs_cnb_language(language):
    normalized = normalize_language(language)
    return "dockerfile" not in normalized and "nodejs" in normalized


def is_cnb_language(language):
    normalized = normalize_language(language)
    if "dockerfile" in normalized:
        return False
    return is_nodejs_cnb_language(normalized) or normalized == "static"


def has_cnb_build_params(build_env_dict, language):
    if not is_cnb_language(language):
        return False
    return any(key in (build_env_dict or {}) for key in CNB_PARAMS_FOR_BUILD_TYPE)


def sanitize_build_env_dict_for_language(build_env_dict, language):
    sanitized = dict(build_env_dict or {})
    if is_cnb_language(language):
        return sanitized

    for key in CNB_BUILD_ENV_NAMES:
        sanitized.pop(key, None)
    for key in CNB_BUILD_ENV_ALIASES:
        sanitized.pop(key, None)
    if str(sanitized.get("BUILD_TYPE", "")).lower() == "cnb":
        sanitized.pop("BUILD_TYPE", None)
    if str(sanitized.get("TYPE", "")).lower() == "cnb":
        sanitized.pop("TYPE", None)
    return sanitized


def extract_cnb_envs_from_runtime_info(runtime_info):
    if not isinstance(runtime_info, dict):
        return {}

    language = runtime_info.get("language", "")
    if not is_cnb_language(language):
        return {}

    cnb_envs = {}

    framework = runtime_info.get("framework") or {}
    framework_name = framework.get("name", "")
    if framework_name:
        cnb_envs["CNB_FRAMEWORK"] = framework_name

    build_config = runtime_info.get("build_config") or {}
    output_dir = build_config.get("output_dir", "")
    if output_dir:
        cnb_envs["CNB_OUTPUT_DIR"] = output_dir
    build_command = build_config.get("build_command", "")
    if build_command:
        cnb_envs["CNB_BUILD_SCRIPT"] = build_command

    if not is_nodejs_cnb_language(language):
        return cnb_envs

    language_version = runtime_info.get("language_version", "")
    if language_version:
        cnb_envs["CNB_NODE_VERSION"] = language_version

    package_manager = runtime_info.get("package_manager") or {}
    package_manager_name = package_manager.get("name", "")
    if package_manager_name:
        cnb_envs["CNB_PACKAGE_TOOL"] = package_manager_name

    config_files = runtime_info.get("config_files") or {}
    has_npmrc = config_files.get("has_npmrc")
    has_yarnrc = config_files.get("has_yarnrc")
    if has_npmrc:
        cnb_envs["BUILD_HAS_NPMRC"] = "true"
    if has_yarnrc:
        cnb_envs["BUILD_HAS_YARNRC"] = "true"
    cnb_envs["CNB_MIRROR_SOURCE"] = "project" if (has_npmrc or has_yarnrc) else "global"

    return cnb_envs
