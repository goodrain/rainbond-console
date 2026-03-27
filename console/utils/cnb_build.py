# -*- coding: utf8 -*-
"""CNB build env helpers."""
import re

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

CNB_POLICY_DEFINITIONS = (
    {
        "policy_key": "java",
        "runtime_key": "jdk",
        "lang_key": "openJDK",
    },
    {
        "policy_key": "python",
        "runtime_key": "cpython",
        "lang_key": "python",
    },
    {
        "policy_key": "golang",
        "runtime_key": "go",
        "lang_key": "golang",
    },
    {
        "policy_key": "php",
        "runtime_key": "php",
        "lang_key": "php",
    },
    {
        "policy_key": "nodejs",
        "runtime_key": "nodejs",
        "lang_key": "node",
    },
)

DEFAULT_CNB_BUILDER_IMAGE = "registry.cn-hangzhou.aliyuncs.com/goodrain/ubuntu-noble-builder:0.0.72"
DEFAULT_PHP_CNB_BUILDER_IMAGE = "docker.io/paketobuildpacks/builder-jammy-full:latest"


def normalize_language(language):
    return (language or "").replace(".", "").strip().lower()


def get_cnb_policy_definition(language):
    normalized = normalize_language(language)
    compact = normalized.replace("-", "").replace("_", "").replace(" ", "")
    if "dockerfile" in normalized:
        return None
    if compact == "static" or "nodejs" in compact:
        return CNB_POLICY_DEFINITIONS[4]
    if "java" in compact:
        return CNB_POLICY_DEFINITIONS[0]
    if "python" in compact:
        return CNB_POLICY_DEFINITIONS[1]
    if compact == "go" or "golang" in compact:
        return CNB_POLICY_DEFINITIONS[2]
    if "php" in compact:
        return CNB_POLICY_DEFINITIONS[3]
    return None


def supports_cnb_build_strategy(language):
    normalized = normalize_language(language)
    compact = normalized.replace("-", "").replace("_", "").replace(" ", "")
    if "dockerfile" in normalized:
        return False
    if compact in ("netcore", "dotnet", "dotnetcore"):
        return True
    return get_cnb_policy_definition(language) is not None


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
    if str(sanitized.get("TYPE", "")).lower() == "cnb":
        sanitized.pop("TYPE", None)
    if _is_java_cnb_language(language):
        sanitized.pop("BUILD_RUNTIMES_MAVEN", None)
    if not supports_cnb_build_strategy(language) and str(sanitized.get("BUILD_TYPE", "")).lower() == "cnb":
        sanitized.pop("BUILD_TYPE", None)
    return sanitized


def resolve_lang_update_build_strategy(language, service_build_strategy=""):
    current = (service_build_strategy or "").strip().lower()
    if supports_cnb_build_strategy(language):
        return current or "cnb"
    return ""


def compose_build_env_response(build_env_dict, build_strategy="", cnb_version_policy=None):
    bean = dict(build_env_dict or {})
    build_strategy = (build_strategy or "").strip().lower()
    if build_strategy:
        bean["build_strategy"] = build_strategy
    if build_strategy == "cnb" and cnb_version_policy:
        bean["cnb_version_policy"] = cnb_version_policy
    return bean


def resolve_build_strategy(service_build_strategy="", build_env_dict=None):
    build_strategy = (service_build_strategy or "").strip().lower()
    if build_strategy:
        return build_strategy
    build_env_dict = build_env_dict or {}
    return str(build_env_dict.get("BUILD_TYPE", "") or build_env_dict.get("TYPE", "")).strip().lower()


def should_backfill_build_strategy(service_build_strategy="", build_env_dict=None):
    return not (service_build_strategy or "").strip() and resolve_build_strategy("", build_env_dict) == "cnb"


def resolve_requested_build_strategy(service_build_strategy="", current_build_env_dict=None,
                                     request_build_strategy="", request_build_env_dict=None):
    requested_strategy = (request_build_strategy or "").strip().lower()
    if requested_strategy:
        return requested_strategy

    request_build_env_dict = request_build_env_dict or {}
    request_legacy_strategy = resolve_build_strategy("", {
        "BUILD_TYPE": request_build_env_dict.get("BUILD_TYPE", ""),
        "TYPE": request_build_env_dict.get("TYPE", ""),
    })
    if request_legacy_strategy:
        return request_legacy_strategy

    return resolve_build_strategy(service_build_strategy, current_build_env_dict)


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


def build_cnb_version_policy(language, records, fallback_versions):
    definition = get_cnb_policy_definition(language)
    if not definition:
        return {}

    visible_versions = []
    allowed_versions = []
    default_version = ""

    for record in records or []:
        if not isinstance(record, dict):
            continue
        if str(record.get("build_strategy") or "").lower() != "cnb":
            continue

        normalized_version = _normalize_cnb_policy_version(definition, record.get("version", ""))
        if not normalized_version:
            continue

        if _is_truthy(record.get("show", record.get("is_show", True))):
            _append_unique(visible_versions, normalized_version)
        if _is_truthy(record.get("is_allowed", True)):
            _append_unique(allowed_versions, normalized_version)
        if _is_truthy(record.get("first_choice")):
            default_version = normalized_version

    if not visible_versions and not allowed_versions:
        visible_versions, allowed_versions, default_version = _build_fallback_policy(definition, fallback_versions)

    return {
        definition["policy_key"]: {
            definition["runtime_key"]: {
                "visible_versions": visible_versions,
                "allowed_versions": allowed_versions,
                "default_version": default_version,
            }
        }
    }


def policy_summary_to_snapshot(language, summary):
    definition = get_cnb_policy_definition(language)
    if not definition or not isinstance(summary, dict):
        return {}

    runtime_block = summary.get(definition["policy_key"], {}).get(definition["runtime_key"], {})
    if not runtime_block:
        return {}

    return {
        "version": 1,
        "languages": {
            definition["policy_key"]: {
                "lang_key": definition["lang_key"],
                "visible_versions": list(runtime_block.get("visible_versions", [])),
                "allowed_versions": list(runtime_block.get("allowed_versions", [])),
                "default_version": runtime_block.get("default_version", ""),
            }
        }
    }


def normalize_source_build_config(language,
                                  package_tool="",
                                  dist="",
                                  build_strategy="",
                                  build_env_dict=None,
                                  compat_payload=None,
                                  default_to_cnb=True):
    envs = sanitize_build_env_dict_for_language(build_env_dict or {}, language)
    compat_payload = compat_payload or {}

    compat_aliases = (
        ("cnb_framework", "CNB_FRAMEWORK"),
        ("cnb_build_script", "CNB_BUILD_SCRIPT"),
        ("cnb_output_dir", "CNB_OUTPUT_DIR"),
        ("cnb_node_version", "CNB_NODE_VERSION"),
        ("cnb_node_env", "CNB_NODE_ENV"),
        ("cnb_start_script", "CNB_START_SCRIPT"),
        ("cnb_mirror_source", "CNB_MIRROR_SOURCE"),
        ("cnb_mirror_npmrc", "CNB_MIRROR_NPMRC"),
        ("cnb_mirror_yarnrc", "CNB_MIRROR_YARNRC"),
        ("has_npmrc", "BUILD_HAS_NPMRC"),
        ("has_yarnrc", "BUILD_HAS_YARNRC"),
    )
    for source_key, target_key in compat_aliases:
        if compat_payload.get(source_key) and target_key not in envs:
            envs[target_key] = compat_payload[source_key]

    if package_tool:
        envs.setdefault("BUILD_PACKAGE_TOOL", package_tool)
        if supports_cnb_build_strategy(language):
            envs.setdefault("CNB_PACKAGE_TOOL", package_tool)
    if dist and (is_nodejs_cnb_language(language) or normalize_language(language) == "static"):
        envs.setdefault("BUILD_DIST_DIR", dist)

    normalized_strategy = resolve_build_strategy(build_strategy, envs)
    if default_to_cnb and not normalized_strategy and supports_cnb_build_strategy(language):
        normalized_strategy = "cnb"
    return normalized_strategy, envs


def compose_source_code_info(service, envs, build_strategy, cnb_policy_snapshot, repo_url, branch):
    build_strategy = (build_strategy or "").strip().lower()
    build_type = str((envs or {}).get("BUILD_TYPE", "") or (envs or {}).get("TYPE", "")).strip().lower()
    if build_strategy:
        build_type = build_strategy

    code_info = {
        "repo_url": repo_url,
        "branch": branch,
        "server_type": service.server_type,
        "lang": service.language,
        "cmd": "" if build_type == "cnb" else service.cmd,
        "build_type": build_type,
    }
    if build_strategy:
        code_info["build_strategy"] = build_strategy
    if build_strategy == "cnb" and cnb_policy_snapshot:
        code_info["cnb_version_policy"] = cnb_policy_snapshot
    if getattr(service, "language", "") == "dockerfile" and getattr(service, "dockerfile", ""):
        code_info["dockerfile_path"] = service.dockerfile
    return code_info


def get_cnb_builder_image(language):
    definition = get_cnb_policy_definition(language)
    if not definition:
        return ""
    if definition["policy_key"] == "php":
        return DEFAULT_PHP_CNB_BUILDER_IMAGE
    return DEFAULT_CNB_BUILDER_IMAGE


def summarize_build_env(language, build_strategy, build_env_dict):
    build_strategy = (build_strategy or "").strip().lower()
    build_env_dict = dict(build_env_dict or {})
    summary = {
        "builder_image": "",
        "yaml_observable": {},
        "start_command_source": ""
    }
    if build_strategy != "cnb":
        return summary

    definition = get_cnb_policy_definition(language)
    if not definition:
        return summary

    summary["builder_image"] = get_cnb_builder_image(language)
    summary["start_command_source"] = "procfile" if build_env_dict.get("BUILD_PROCFILE") else "buildpack-default"
    yaml_observable = {
        "build_type": "cnb",
        "annotations": {
            "rainbond.io/cnb-language": definition["policy_key"]
        }
    }

    if definition["policy_key"] == "java":
        if build_env_dict.get("BUILD_RUNTIMES"):
            yaml_observable["annotations"]["cnb-bp-jvm-version"] = build_env_dict.get("BUILD_RUNTIMES")
        if build_env_dict.get("BUILD_MAVEN_CUSTOM_GOALS"):
            yaml_observable["annotations"]["cnb-bp-maven-build-arguments"] = build_env_dict.get(
                "BUILD_MAVEN_CUSTOM_GOALS")
        if build_env_dict.get("BUILD_MAVEN_CUSTOM_OPTS"):
            yaml_observable["annotations"]["cnb-bp-maven-additional-build-arguments"] = build_env_dict.get(
                "BUILD_MAVEN_CUSTOM_OPTS")
        if build_env_dict.get("BUILD_RUNTIMES_SERVER"):
            yaml_observable["annotations"]["cnb-bp-java-app-server"] = build_env_dict.get("BUILD_RUNTIMES_SERVER")
        if build_env_dict.get("BUILD_GRADLE_BUILD_ARGUMENTS"):
            yaml_observable["annotations"]["cnb-bp-gradle-build-arguments"] = build_env_dict.get(
                "BUILD_GRADLE_BUILD_ARGUMENTS")
        if build_env_dict.get("BUILD_GRADLE_ADDITIONAL_BUILD_ARGUMENTS"):
            yaml_observable["annotations"]["cnb-bp-gradle-additional-build-arguments"] = build_env_dict.get(
                "BUILD_GRADLE_ADDITIONAL_BUILD_ARGUMENTS")
        if build_env_dict.get("BUILD_MAVEN_BUILT_MODULE"):
            yaml_observable["annotations"]["cnb-bp-maven-built-module"] = build_env_dict.get(
                "BUILD_MAVEN_BUILT_MODULE")
        if build_env_dict.get("BUILD_MAVEN_BUILT_ARTIFACT"):
            yaml_observable["annotations"]["cnb-bp-maven-built-artifact"] = build_env_dict.get(
                "BUILD_MAVEN_BUILT_ARTIFACT")
        if build_env_dict.get("BUILD_GRADLE_BUILT_MODULE"):
            yaml_observable["annotations"]["cnb-bp-gradle-built-module"] = build_env_dict.get(
                "BUILD_GRADLE_BUILT_MODULE")
        if build_env_dict.get("BUILD_GRADLE_BUILT_ARTIFACT"):
            yaml_observable["annotations"]["cnb-bp-gradle-built-artifact"] = build_env_dict.get(
                "BUILD_GRADLE_BUILT_ARTIFACT")
    elif definition["policy_key"] == "python":
        if build_env_dict.get("BUILD_RUNTIMES"):
            yaml_observable["annotations"]["cnb-bp-cpython-version"] = build_env_dict.get("BUILD_RUNTIMES")
        if build_env_dict.get("BUILD_CONDA_SOLVER"):
            yaml_observable["annotations"]["cnb-bp-conda-solver"] = build_env_dict.get("BUILD_CONDA_SOLVER")
        if build_env_dict.get("BUILD_LIVE_RELOAD_ENABLED"):
            yaml_observable["annotations"]["cnb-bp-live-reload-enabled"] = _bool_to_string(
                build_env_dict.get("BUILD_LIVE_RELOAD_ENABLED"))
    elif definition["policy_key"] == "golang":
        if build_env_dict.get("BUILD_GOVERSION"):
            yaml_observable["annotations"]["cnb-bp-go-version"] = build_env_dict.get("BUILD_GOVERSION")
        if build_env_dict.get("BUILD_GO_INSTALL_PACKAGE_SPEC"):
            yaml_observable["annotations"]["cnb-bp-go-targets"] = build_env_dict.get("BUILD_GO_INSTALL_PACKAGE_SPEC")
        if build_env_dict.get("BUILD_GO_BUILD_FLAGS"):
            yaml_observable["annotations"]["cnb-bp-go-build-flags"] = build_env_dict.get("BUILD_GO_BUILD_FLAGS")
        if build_env_dict.get("BUILD_GO_BUILD_LDFLAGS"):
            yaml_observable["annotations"]["cnb-bp-go-build-ldflags"] = build_env_dict.get("BUILD_GO_BUILD_LDFLAGS")
        if build_env_dict.get("BUILD_GO_BUILD_IMPORT_PATH"):
            yaml_observable["annotations"]["cnb-bp-go-build-import-path"] = build_env_dict.get(
                "BUILD_GO_BUILD_IMPORT_PATH")
        if build_env_dict.get("BUILD_GO_KEEP_FILES"):
            yaml_observable["annotations"]["cnb-bp-keep-files"] = build_env_dict.get("BUILD_GO_KEEP_FILES")
        if build_env_dict.get("BUILD_GO_WORK_USE"):
            yaml_observable["annotations"]["cnb-bp-go-work-use"] = build_env_dict.get("BUILD_GO_WORK_USE")
        if build_env_dict.get("BUILD_LIVE_RELOAD_ENABLED"):
            yaml_observable["annotations"]["cnb-bp-live-reload-enabled"] = _bool_to_string(
                build_env_dict.get("BUILD_LIVE_RELOAD_ENABLED"))
    elif definition["policy_key"] == "php":
        if build_env_dict.get("BUILD_RUNTIMES"):
            yaml_observable["annotations"]["cnb-bp-php-version"] = build_env_dict.get("BUILD_RUNTIMES")
        if build_env_dict.get("BUILD_RUNTIMES_SERVER"):
            yaml_observable["annotations"]["cnb-bp-php-server"] = build_env_dict.get("BUILD_RUNTIMES_SERVER")
        if build_env_dict.get("BUILD_COMPOSER_VERSION"):
            yaml_observable["annotations"]["cnb-bp-composer-version"] = build_env_dict.get("BUILD_COMPOSER_VERSION")
        if build_env_dict.get("BUILD_COMPOSER_INSTALL_OPTIONS"):
            yaml_observable["annotations"]["cnb-bp-composer-install-options"] = build_env_dict.get(
                "BUILD_COMPOSER_INSTALL_OPTIONS")
        if build_env_dict.get("BUILD_COMPOSER_INSTALL_GLOBAL"):
            yaml_observable["annotations"]["cnb-bp-composer-install-global"] = _bool_to_string(
                build_env_dict.get("BUILD_COMPOSER_INSTALL_GLOBAL"))
        if build_env_dict.get("BUILD_PHP_WEB_DIR"):
            yaml_observable["annotations"]["cnb-bp-php-web-dir"] = build_env_dict.get("BUILD_PHP_WEB_DIR")
        if build_env_dict.get("BUILD_PHP_NGINX_ENABLE_HTTPS"):
            yaml_observable["annotations"]["cnb-bp-php-nginx-enable-https"] = _bool_to_string(
                build_env_dict.get("BUILD_PHP_NGINX_ENABLE_HTTPS"))
        if build_env_dict.get("BUILD_PHP_ENABLE_HTTPS_REDIRECT"):
            yaml_observable["annotations"]["cnb-bp-php-enable-https-redirect"] = _bool_to_string(
                build_env_dict.get("BUILD_PHP_ENABLE_HTTPS_REDIRECT"))
    elif definition["policy_key"] == "nodejs":
        if build_env_dict.get("CNB_NODE_VERSION"):
            yaml_observable["annotations"]["cnb-bp-node-version"] = build_env_dict.get("CNB_NODE_VERSION")

    summary["yaml_observable"] = yaml_observable
    return summary


def _bool_to_string(value):
    return "true" if _is_truthy(value) else "false"


def _is_java_cnb_language(language):
    normalized = normalize_language(language)
    compact = normalized.replace("-", "").replace("_", "").replace(" ", "")
    return "java" in compact or "gradle" in compact


def _build_fallback_policy(definition, fallback_versions):
    visible_versions = []
    allowed_versions = []
    default_version = ""

    for item in fallback_versions or []:
        version = item.get("version", "") if isinstance(item, dict) else item
        normalized_version = _normalize_cnb_policy_version(definition, version)
        if not normalized_version:
            continue
        _append_unique(visible_versions, normalized_version)
        _append_unique(allowed_versions, normalized_version)
        if isinstance(item, dict) and item.get("default"):
            default_version = normalized_version

    return visible_versions, allowed_versions, default_version


def _normalize_cnb_policy_version(definition, version):
    value = str(version or "").strip()
    if not value:
        return ""

    policy_key = definition["policy_key"]
    if policy_key == "java":
        if value.startswith("1."):
            value = value[2:]
        return value.split(".", 1)[0]
    if policy_key == "python":
        if value.startswith("python-"):
            value = value[len("python-"):]
        parts = value.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:2])
        return value
    if policy_key == "golang":
        if value.startswith("go"):
            value = value[2:]
        parts = value.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:2])
        return value
    if policy_key == "php":
        parts = value.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:2])
        return value
    return value


def _append_unique(items, value):
    if value and value not in items:
        items.append(value)


def _is_truthy(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in ("1", "true", "yes", "on")
