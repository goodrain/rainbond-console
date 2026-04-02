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
    {
        "policy_key": "dotnet",
        "runtime_key": "framework",
        "lang_key": "dotnet",
    },
)

CNB_POLICY_VERSION_CONSTRAINTS = {
    "golang": {
        "supported_versions": ("1.24", "1.25"),
        "default_version": "1.25",
    }
}

DEFAULT_CNB_BUILDER_IMAGE = "registry.cn-hangzhou.aliyuncs.com/goodrain/ubuntu-noble-builder:0.0.72"
DEFAULT_PHP_CNB_BUILDER_IMAGE = "docker.io/paketobuildpacks/builder-jammy-full:latest"

JAVA_CNB_LEGACY_TO_BP_ALIASES = (
    ("BUILD_RUNTIMES", "BP_JVM_VERSION"),
    ("RUNTIMES", "BP_JVM_VERSION"),
    ("BUILD_MAVEN_CUSTOM_GOALS", "BP_MAVEN_BUILD_ARGUMENTS"),
    ("BUILD_MAVEN_CUSTOM_OPTS", "BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS"),
    ("BUILD_MAVEN_BUILT_MODULE", "BP_MAVEN_BUILT_MODULE"),
    ("BUILD_MAVEN_BUILT_ARTIFACT", "BP_MAVEN_BUILT_ARTIFACT"),
    ("BUILD_GRADLE_BUILD_ARGUMENTS", "BP_GRADLE_BUILD_ARGUMENTS"),
    ("BUILD_GRADLE_ADDITIONAL_BUILD_ARGUMENTS", "BP_GRADLE_ADDITIONAL_BUILD_ARGUMENTS"),
    ("BUILD_GRADLE_BUILT_MODULE", "BP_GRADLE_BUILT_MODULE"),
    ("BUILD_GRADLE_BUILT_ARTIFACT", "BP_GRADLE_BUILT_ARTIFACT"),
    ("BUILD_RUNTIMES_SERVER", "BP_JAVA_APP_SERVER"),
)

JAVA_CNB_BP_KEYS = (
    "BP_EXECUTABLE_JAR_LOCATION",
    "BP_GRADLE_ADDITIONAL_BUILD_ARGUMENTS",
    "BP_GRADLE_BUILD_ARGUMENTS",
    "BP_GRADLE_BUILT_ARTIFACT",
    "BP_GRADLE_BUILT_MODULE",
    "BP_JAVA_APP_SERVER",
    "BP_JVM_TYPE",
    "BP_JVM_VERSION",
    "BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS",
    "BP_MAVEN_BUILD_ARGUMENTS",
    "BP_MAVEN_BUILT_ARTIFACT",
    "BP_MAVEN_BUILT_MODULE",
    "BP_MAVEN_SETTINGS_PATH",
)

GOLANG_CNB_LEGACY_TO_CURRENT_ALIASES = (
    ("BUILD_GOVERSION", "BP_GO_VERSION"),
    ("GOVERSION", "BP_GO_VERSION"),
    ("BUILD_GO_INSTALL_PACKAGE_SPEC", "BP_GO_TARGETS"),
    ("BUILD_GO_BUILD_FLAGS", "BP_GO_BUILD_FLAGS"),
    ("BUILD_GO_BUILD_LDFLAGS", "BP_GO_BUILD_LDFLAGS"),
    ("BUILD_GOPROXY", "GOPROXY"),
    ("BUILD_GOPRIVATE", "GOPRIVATE"),
)

GOLANG_CNB_CURRENT_KEYS = (
    "BP_GO_VERSION",
    "BP_GO_TARGETS",
    "BP_GO_BUILD_FLAGS",
    "BP_GO_BUILD_LDFLAGS",
    "GOPROXY",
    "GOPRIVATE",
)

PHP_CNB_LEGACY_TO_CURRENT_ALIASES = (
    ("BUILD_RUNTIMES", "BP_PHP_VERSION"),
    ("RUNTIMES", "BP_PHP_VERSION"),
    ("BUILD_COMPOSER_INSTALL_OPTIONS", "BP_COMPOSER_INSTALL_OPTIONS"),
    ("BUILD_PHP_WEB_DIR", "BP_PHP_WEB_DIR"),
)

PHP_CNB_CURRENT_KEYS = (
    "BP_PHP_VERSION",
    "BP_COMPOSER_INSTALL_OPTIONS",
    "BP_PHP_WEB_DIR",
)

DOTNET_CNB_LEGACY_TO_CURRENT_ALIASES = (
    ("BUILD_DOTNET_SDK_VERSION", "BP_DOTNET_FRAMEWORK_VERSION"),
    ("BUILD_DOTNET_RUNTIME_VERSION", "BP_DOTNET_FRAMEWORK_VERSION"),
    ("BUILD_DOTNET_PUBLISH_FLAGS", "BP_DOTNET_PUBLISH_FLAGS"),
)

DOTNET_CNB_CURRENT_KEYS = (
    "BP_DOTNET_FRAMEWORK_VERSION",
    "BP_DOTNET_PROJECT_PATH",
    "BP_DOTNET_PUBLISH_FLAGS",
    "BUILD_NUGET_CONFIG_NAME",
)

PYTHON_CNB_INTERNAL_KEYS = (
    "BUILD_AUTO_PROCFILE",
    "START_COMMAND_SOURCE",
)

PYTHON_CNB_READONLY_KEYS = (
    "BUILD_PYTHON_PACKAGE_MANAGER",
    "start_command_source",
)


def normalize_language(language):
    return (language or "").replace(".", "").strip().lower()


def get_cnb_policy_definition(language):
    normalized = normalize_language(language)
    compact = normalized.replace("-", "").replace("_", "").replace(" ", "")
    if "dockerfile" in normalized:
        return None
    if compact in ("netcore", "dotnet", "dotnetcore"):
        return CNB_POLICY_DEFINITIONS[5]
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


def normalize_java_cnb_env_dict_for_response(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    if str(build_strategy or "").strip().lower() != "cnb" or not _is_java_cnb_language(language):
        return envs

    _normalize_java_cnb_legacy_aliases(envs)
    _drop_java_legacy_aliases(envs)
    _drop_legacy_cnb_type_markers(envs)
    return envs


def normalize_java_cnb_env_dict_for_save(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    if not _is_java_cnb_language(language):
        return envs

    normalized_strategy = str(build_strategy or "").strip().lower()
    if normalized_strategy == "cnb":
        _normalize_java_cnb_legacy_aliases(envs)
        _drop_java_legacy_aliases(envs)
        _drop_legacy_cnb_type_markers(envs)
        return envs

    for key in JAVA_CNB_BP_KEYS:
        envs.pop(key, None)
    _drop_legacy_cnb_type_markers(envs)
    return envs


def normalize_python_cnb_env_dict_for_response(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    if str(build_strategy or "").strip().lower() != "cnb" or normalize_language(language) != "python":
        return envs

    manager = _first_non_empty(envs, "BUILD_PYTHON_PACKAGE_MANAGER") or "pip"
    if not _first_non_empty(envs, "BUILD_PROCFILE") and _first_non_empty(envs, "BUILD_AUTO_PROCFILE"):
        envs["BUILD_PROCFILE"] = _first_non_empty(envs, "BUILD_AUTO_PROCFILE")
    if _first_non_empty(envs, "START_COMMAND_SOURCE"):
        envs["start_command_source"] = _first_non_empty(envs, "START_COMMAND_SOURCE")
    elif _first_non_empty(envs, "BUILD_PROCFILE"):
        envs["start_command_source"] = "user"

    _strip_python_manager_specific_keys(envs, manager)
    for key in PYTHON_CNB_INTERNAL_KEYS:
        envs.pop(key, None)
    return envs


def normalize_python_cnb_env_dict_for_save(build_env_dict, language, build_strategy="", current_build_env_dict=None):
    envs = dict(build_env_dict or {})
    if normalize_language(language) != "python":
        return envs

    current_envs = dict(current_build_env_dict or {})
    normalized_strategy = str(build_strategy or "").strip().lower()
    if normalized_strategy != "cnb":
        envs.pop("BUILD_PYTHON_PACKAGE_MANAGER", None)
        envs.pop("start_command_source", None)
        return envs

    manager = _first_non_empty(current_envs, "BUILD_PYTHON_PACKAGE_MANAGER") or _first_non_empty(envs, "BUILD_PYTHON_PACKAGE_MANAGER") or "pip"
    envs["BUILD_PYTHON_PACKAGE_MANAGER"] = manager

    current_start_command = _first_non_empty(current_envs, "BUILD_PROCFILE", "BUILD_AUTO_PROCFILE")
    if isinstance(envs.get("BUILD_PROCFILE"), str) and envs.get("BUILD_PROCFILE", "").strip() == "":
        envs.pop("BUILD_PROCFILE", None)
    if _first_non_empty(envs, "BUILD_PROCFILE"):
        if _first_non_empty(envs, "BUILD_PROCFILE") == current_start_command and _first_non_empty(current_envs, "START_COMMAND_SOURCE"):
            envs["START_COMMAND_SOURCE"] = _first_non_empty(current_envs, "START_COMMAND_SOURCE")
        else:
            envs["START_COMMAND_SOURCE"] = "user"
    else:
        if _first_non_empty(current_envs, "BUILD_AUTO_PROCFILE"):
            envs["BUILD_AUTO_PROCFILE"] = _first_non_empty(current_envs, "BUILD_AUTO_PROCFILE")
        if _first_non_empty(current_envs, "START_COMMAND_SOURCE"):
            envs["START_COMMAND_SOURCE"] = _first_non_empty(current_envs, "START_COMMAND_SOURCE")

    envs.pop("start_command_source", None)
    _strip_python_manager_specific_keys(envs, manager)
    return envs


def normalize_golang_cnb_env_dict_for_response(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    if str(build_strategy or "").strip().lower() != "cnb" or normalize_language(language) not in ("go", "golang"):
        return envs

    _normalize_golang_cnb_legacy_aliases(envs)
    _drop_golang_legacy_aliases(envs)
    _drop_legacy_cnb_type_markers(envs)
    return envs


def normalize_golang_cnb_env_dict_for_save(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    if normalize_language(language) not in ("go", "golang"):
        return envs

    normalized_strategy = str(build_strategy or "").strip().lower()
    if normalized_strategy == "cnb":
        _normalize_golang_cnb_legacy_aliases(envs)
        _drop_golang_legacy_aliases(envs)
        _drop_legacy_cnb_type_markers(envs)
        return envs

    for key in GOLANG_CNB_CURRENT_KEYS:
        envs.pop(key, None)
    _drop_legacy_cnb_type_markers(envs)
    return envs


def normalize_php_cnb_env_dict_for_response(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    if str(build_strategy or "").strip().lower() != "cnb" or normalize_language(language) != "php":
        return envs

    _normalize_php_cnb_legacy_aliases(envs)
    _drop_php_legacy_aliases(envs)
    _strip_php_cnb_hidden_keys(envs)
    envs["BUILD_RUNTIMES_SERVER"] = "nginx"
    _drop_legacy_cnb_type_markers(envs)
    return envs


def normalize_php_cnb_env_dict_for_save(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    if normalize_language(language) != "php":
        return envs

    normalized_strategy = str(build_strategy or "").strip().lower()
    if normalized_strategy == "cnb":
        _normalize_php_cnb_legacy_aliases(envs)
        _drop_php_legacy_aliases(envs)
        _strip_php_cnb_hidden_keys(envs)
        envs["BUILD_RUNTIMES_SERVER"] = "nginx"
        envs["BUILD_COMPOSER_VERSION"] = "2.7.9"
        _drop_legacy_cnb_type_markers(envs)
        return envs

    for key in PHP_CNB_CURRENT_KEYS:
        envs.pop(key, None)
    _drop_legacy_cnb_type_markers(envs)
    return envs


def normalize_dotnet_cnb_env_dict_for_response(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    if str(build_strategy or "").strip().lower() != "cnb":
        return envs
    normalized_language = normalize_language(language)
    if normalized_language not in ("netcore", "dotnet", "dotnetcore"):
        return envs

    _normalize_dotnet_cnb_legacy_aliases(envs)
    _drop_dotnet_legacy_aliases(envs)
    _drop_legacy_cnb_type_markers(envs)
    return envs


def normalize_dotnet_cnb_env_dict_for_save(build_env_dict, language, build_strategy=""):
    envs = dict(build_env_dict or {})
    normalized_language = normalize_language(language)
    if normalized_language not in ("netcore", "dotnet", "dotnetcore"):
        return envs

    normalized_strategy = str(build_strategy or "").strip().lower()
    if normalized_strategy == "cnb":
        _normalize_dotnet_cnb_legacy_aliases(envs)
        _drop_dotnet_legacy_aliases(envs)
        _drop_legacy_cnb_type_markers(envs)
        return envs

    for key in DOTNET_CNB_CURRENT_KEYS:
        envs.pop(key, None)
    envs.pop("BUILD_PROCFILE", None)
    _drop_legacy_cnb_type_markers(envs)
    return envs


def compose_build_env_response(build_env_dict, build_strategy="", cnb_version_policy=None):
    bean = {}
    for key, value in dict(build_env_dict or {}).items():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        bean[key] = value
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
    definition = get_cnb_policy_definition(language)
    if not definition:
        return {}

    cnb_envs = {}

    build_config = runtime_info.get("build_config") or {}
    if definition["policy_key"] == "python":
        package_manager = runtime_info.get("package_manager") or {}
        package_manager_name = package_manager.get("name", "")
        if package_manager_name:
            cnb_envs["BUILD_PYTHON_PACKAGE_MANAGER"] = package_manager_name

        start_command = build_config.get("start_command", "")
        if start_command:
            cnb_envs["BUILD_AUTO_PROCFILE"] = start_command
            config_files = runtime_info.get("config_files") or {}
            cnb_envs["START_COMMAND_SOURCE"] = "procfile" if config_files.get("has_procfile") else "auto-detected"
        return cnb_envs

    framework = runtime_info.get("framework") or {}
    framework_name = framework.get("name", "")
    if framework_name:
        cnb_envs["CNB_FRAMEWORK"] = framework_name

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

    visible_versions = _sort_cnb_policy_versions(visible_versions)
    allowed_versions = _sort_cnb_policy_versions(allowed_versions)
    visible_versions, allowed_versions, default_version = _apply_cnb_policy_version_constraints(
        definition["policy_key"], visible_versions, allowed_versions, default_version)

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
    summary["start_command_source"] = _first_non_empty(build_env_dict, "start_command_source", "START_COMMAND_SOURCE")
    if not summary["start_command_source"]:
        summary["start_command_source"] = "procfile" if build_env_dict.get("BUILD_PROCFILE") else "buildpack-default"
    yaml_observable = {
        "build_type": "cnb",
        "annotations": {
            "rainbond.io/cnb-language": definition["policy_key"]
        }
    }

    if definition["policy_key"] == "java":
        if _first_non_empty(build_env_dict, "BP_JVM_VERSION", "BUILD_RUNTIMES"):
            yaml_observable["annotations"]["cnb-bp-jvm-version"] = _first_non_empty(
                build_env_dict, "BP_JVM_VERSION", "BUILD_RUNTIMES")
        if _first_non_empty(build_env_dict, "BP_JVM_TYPE"):
            yaml_observable["annotations"]["cnb-bp-jvm-type"] = _first_non_empty(build_env_dict, "BP_JVM_TYPE")
        if _first_non_empty(build_env_dict, "BP_MAVEN_BUILD_ARGUMENTS", "BUILD_MAVEN_CUSTOM_GOALS"):
            yaml_observable["annotations"]["cnb-bp-maven-build-arguments"] = _first_non_empty(
                build_env_dict, "BP_MAVEN_BUILD_ARGUMENTS", "BUILD_MAVEN_CUSTOM_GOALS")
        if _first_non_empty(build_env_dict, "BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS", "BUILD_MAVEN_CUSTOM_OPTS"):
            yaml_observable["annotations"]["cnb-bp-maven-additional-build-arguments"] = _first_non_empty(
                build_env_dict, "BP_MAVEN_ADDITIONAL_BUILD_ARGUMENTS", "BUILD_MAVEN_CUSTOM_OPTS")
        if _first_non_empty(build_env_dict, "BP_JAVA_APP_SERVER", "BUILD_RUNTIMES_SERVER"):
            yaml_observable["annotations"]["cnb-bp-java-app-server"] = _first_non_empty(
                build_env_dict, "BP_JAVA_APP_SERVER", "BUILD_RUNTIMES_SERVER")
        if _first_non_empty(build_env_dict, "BP_GRADLE_BUILD_ARGUMENTS", "BUILD_GRADLE_BUILD_ARGUMENTS"):
            yaml_observable["annotations"]["cnb-bp-gradle-build-arguments"] = _first_non_empty(
                build_env_dict, "BP_GRADLE_BUILD_ARGUMENTS", "BUILD_GRADLE_BUILD_ARGUMENTS")
        if _first_non_empty(build_env_dict, "BP_GRADLE_ADDITIONAL_BUILD_ARGUMENTS", "BUILD_GRADLE_ADDITIONAL_BUILD_ARGUMENTS"):
            yaml_observable["annotations"]["cnb-bp-gradle-additional-build-arguments"] = _first_non_empty(
                build_env_dict, "BP_GRADLE_ADDITIONAL_BUILD_ARGUMENTS", "BUILD_GRADLE_ADDITIONAL_BUILD_ARGUMENTS")
        if _first_non_empty(build_env_dict, "BP_MAVEN_BUILT_MODULE", "BUILD_MAVEN_BUILT_MODULE"):
            yaml_observable["annotations"]["cnb-bp-maven-built-module"] = _first_non_empty(
                build_env_dict, "BP_MAVEN_BUILT_MODULE", "BUILD_MAVEN_BUILT_MODULE")
        if _first_non_empty(build_env_dict, "BP_MAVEN_BUILT_ARTIFACT", "BUILD_MAVEN_BUILT_ARTIFACT"):
            yaml_observable["annotations"]["cnb-bp-maven-built-artifact"] = _first_non_empty(
                build_env_dict, "BP_MAVEN_BUILT_ARTIFACT", "BUILD_MAVEN_BUILT_ARTIFACT")
        if _first_non_empty(build_env_dict, "BP_GRADLE_BUILT_MODULE", "BUILD_GRADLE_BUILT_MODULE"):
            yaml_observable["annotations"]["cnb-bp-gradle-built-module"] = _first_non_empty(
                build_env_dict, "BP_GRADLE_BUILT_MODULE", "BUILD_GRADLE_BUILT_MODULE")
        if _first_non_empty(build_env_dict, "BP_GRADLE_BUILT_ARTIFACT", "BUILD_GRADLE_BUILT_ARTIFACT"):
            yaml_observable["annotations"]["cnb-bp-gradle-built-artifact"] = _first_non_empty(
                build_env_dict, "BP_GRADLE_BUILT_ARTIFACT", "BUILD_GRADLE_BUILT_ARTIFACT")
    elif definition["policy_key"] == "python":
        if _first_non_empty(build_env_dict, "BP_CPYTHON_VERSION", "BUILD_RUNTIMES"):
            yaml_observable["annotations"]["cnb-bp-cpython-version"] = _first_non_empty(
                build_env_dict, "BP_CPYTHON_VERSION", "BUILD_RUNTIMES")
        if _first_non_empty(build_env_dict, "BP_CONDA_SOLVER", "BUILD_CONDA_SOLVER"):
            yaml_observable["annotations"]["cnb-bp-conda-solver"] = _first_non_empty(
                build_env_dict, "BP_CONDA_SOLVER", "BUILD_CONDA_SOLVER")
        if build_env_dict.get("BUILD_LIVE_RELOAD_ENABLED"):
            yaml_observable["annotations"]["cnb-bp-live-reload-enabled"] = _bool_to_string(
                build_env_dict.get("BUILD_LIVE_RELOAD_ENABLED"))
    elif definition["policy_key"] == "golang":
        if _first_non_empty(build_env_dict, "BP_GO_VERSION", "BUILD_GOVERSION", "GOVERSION"):
            yaml_observable["annotations"]["cnb-bp-go-version"] = _first_non_empty(
                build_env_dict, "BP_GO_VERSION", "BUILD_GOVERSION", "GOVERSION")
        if _first_non_empty(build_env_dict, "BP_GO_TARGETS", "BUILD_GO_INSTALL_PACKAGE_SPEC"):
            yaml_observable["annotations"]["cnb-bp-go-targets"] = _first_non_empty(
                build_env_dict, "BP_GO_TARGETS", "BUILD_GO_INSTALL_PACKAGE_SPEC")
        if _first_non_empty(build_env_dict, "BP_GO_BUILD_FLAGS", "BUILD_GO_BUILD_FLAGS"):
            yaml_observable["annotations"]["cnb-bp-go-build-flags"] = _first_non_empty(
                build_env_dict, "BP_GO_BUILD_FLAGS", "BUILD_GO_BUILD_FLAGS")
        if _first_non_empty(build_env_dict, "BP_GO_BUILD_LDFLAGS", "BUILD_GO_BUILD_LDFLAGS"):
            yaml_observable["annotations"]["cnb-bp-go-build-ldflags"] = _first_non_empty(
                build_env_dict, "BP_GO_BUILD_LDFLAGS", "BUILD_GO_BUILD_LDFLAGS")
        if _first_non_empty(build_env_dict, "BP_GO_BUILD_IMPORT_PATH", "BUILD_GO_BUILD_IMPORT_PATH"):
            yaml_observable["annotations"]["cnb-bp-go-build-import-path"] = _first_non_empty(
                build_env_dict, "BP_GO_BUILD_IMPORT_PATH", "BUILD_GO_BUILD_IMPORT_PATH")
        if _first_non_empty(build_env_dict, "BP_KEEP_FILES", "BUILD_GO_KEEP_FILES"):
            yaml_observable["annotations"]["cnb-bp-keep-files"] = _first_non_empty(
                build_env_dict, "BP_KEEP_FILES", "BUILD_GO_KEEP_FILES")
        if _first_non_empty(build_env_dict, "BP_GO_WORK_USE", "BUILD_GO_WORK_USE"):
            yaml_observable["annotations"]["cnb-bp-go-work-use"] = _first_non_empty(
                build_env_dict, "BP_GO_WORK_USE", "BUILD_GO_WORK_USE")
        if _first_non_empty(build_env_dict, "BP_LIVE_RELOAD_ENABLED", "BUILD_LIVE_RELOAD_ENABLED"):
            yaml_observable["annotations"]["cnb-bp-live-reload-enabled"] = _bool_to_string(
                _first_non_empty(build_env_dict, "BP_LIVE_RELOAD_ENABLED", "BUILD_LIVE_RELOAD_ENABLED"))
    elif definition["policy_key"] == "php":
        if _first_non_empty(build_env_dict, "BP_PHP_VERSION", "BUILD_RUNTIMES", "RUNTIMES"):
            yaml_observable["annotations"]["cnb-bp-php-version"] = _first_non_empty(
                build_env_dict, "BP_PHP_VERSION", "BUILD_RUNTIMES", "RUNTIMES")
        if build_env_dict.get("BUILD_RUNTIMES_SERVER"):
            yaml_observable["annotations"]["cnb-bp-php-server"] = build_env_dict.get("BUILD_RUNTIMES_SERVER")
        if _first_non_empty(build_env_dict, "BP_COMPOSER_VERSION", "BUILD_COMPOSER_VERSION"):
            yaml_observable["annotations"]["cnb-bp-composer-version"] = _first_non_empty(
                build_env_dict, "BP_COMPOSER_VERSION", "BUILD_COMPOSER_VERSION")
        if _first_non_empty(build_env_dict, "BP_COMPOSER_INSTALL_OPTIONS", "BUILD_COMPOSER_INSTALL_OPTIONS"):
            yaml_observable["annotations"]["cnb-bp-composer-install-options"] = _first_non_empty(
                build_env_dict, "BP_COMPOSER_INSTALL_OPTIONS", "BUILD_COMPOSER_INSTALL_OPTIONS")
        if build_env_dict.get("BUILD_COMPOSER_INSTALL_GLOBAL"):
            yaml_observable["annotations"]["cnb-bp-composer-install-global"] = _bool_to_string(
                build_env_dict.get("BUILD_COMPOSER_INSTALL_GLOBAL"))
        if _first_non_empty(build_env_dict, "BP_PHP_WEB_DIR", "BUILD_PHP_WEB_DIR"):
            yaml_observable["annotations"]["cnb-bp-php-web-dir"] = _first_non_empty(
                build_env_dict, "BP_PHP_WEB_DIR", "BUILD_PHP_WEB_DIR")
        if build_env_dict.get("BUILD_PHP_NGINX_ENABLE_HTTPS"):
            yaml_observable["annotations"]["cnb-bp-php-nginx-enable-https"] = _bool_to_string(
                build_env_dict.get("BUILD_PHP_NGINX_ENABLE_HTTPS"))
        if build_env_dict.get("BUILD_PHP_ENABLE_HTTPS_REDIRECT"):
            yaml_observable["annotations"]["cnb-bp-php-enable-https-redirect"] = _bool_to_string(
                build_env_dict.get("BUILD_PHP_ENABLE_HTTPS_REDIRECT"))
    elif definition["policy_key"] == "nodejs":
        if build_env_dict.get("CNB_NODE_VERSION"):
            yaml_observable["annotations"]["cnb-bp-node-version"] = build_env_dict.get("CNB_NODE_VERSION")
    elif definition["policy_key"] == "dotnet":
        if _first_non_empty(build_env_dict, "BP_DOTNET_FRAMEWORK_VERSION"):
            yaml_observable["annotations"]["cnb-bp-dotnet-framework-version"] = _first_non_empty(
                build_env_dict, "BP_DOTNET_FRAMEWORK_VERSION")
        if _first_non_empty(build_env_dict, "BP_DOTNET_PROJECT_PATH"):
            yaml_observable["annotations"]["cnb-bp-dotnet-project-path"] = _first_non_empty(
                build_env_dict, "BP_DOTNET_PROJECT_PATH")
        if _first_non_empty(build_env_dict, "BP_DOTNET_PUBLISH_FLAGS"):
            yaml_observable["annotations"]["cnb-bp-dotnet-publish-flags"] = _first_non_empty(
                build_env_dict, "BP_DOTNET_PUBLISH_FLAGS")
        if _first_non_empty(build_env_dict, "BUILD_NUGET_CONFIG_NAME"):
            yaml_observable["annotations"][_binding_type_annotation_key(
                _first_non_empty(build_env_dict, "BUILD_NUGET_CONFIG_NAME"))] = "nugetconfig"

    summary["yaml_observable"] = yaml_observable
    return summary


def _bool_to_string(value):
    return "true" if _is_truthy(value) else "false"


def _binding_type_annotation_key(binding_name):
    normalized = re.sub(r"[^a-z0-9-]", "-", str(binding_name or "").strip().lower())
    if not normalized:
        return "cnb-binding-type"
    return "cnb-binding-{name}-type".format(name=normalized)


def _is_java_cnb_language(language):
    normalized = normalize_language(language)
    compact = normalized.replace("-", "").replace("_", "").replace(" ", "")
    return "java" in compact or "gradle" in compact


def _normalize_java_cnb_legacy_aliases(envs):
    for source_key, target_key in JAVA_CNB_LEGACY_TO_BP_ALIASES:
        if _first_non_empty(envs, target_key):
            continue
        source_value = _first_non_empty(envs, source_key)
        if source_value:
            envs[target_key] = source_value


def _drop_java_legacy_aliases(envs):
    for source_key, _ in JAVA_CNB_LEGACY_TO_BP_ALIASES:
        envs.pop(source_key, None)


def _normalize_golang_cnb_legacy_aliases(envs):
    for source_key, target_key in GOLANG_CNB_LEGACY_TO_CURRENT_ALIASES:
        if _first_non_empty(envs, target_key):
            continue
        source_value = _first_non_empty(envs, source_key)
        if source_value:
            envs[target_key] = source_value


def _drop_golang_legacy_aliases(envs):
    for source_key, _ in GOLANG_CNB_LEGACY_TO_CURRENT_ALIASES:
        envs.pop(source_key, None)


def _normalize_php_cnb_legacy_aliases(envs):
    for source_key, target_key in PHP_CNB_LEGACY_TO_CURRENT_ALIASES:
        if _first_non_empty(envs, target_key):
            continue
        source_value = _first_non_empty(envs, source_key)
        if source_value:
            envs[target_key] = source_value


def _drop_php_legacy_aliases(envs):
    for source_key, _ in PHP_CNB_LEGACY_TO_CURRENT_ALIASES:
        envs.pop(source_key, None)


def _strip_php_cnb_hidden_keys(envs):
    envs.pop("BP_COMPOSER_VERSION", None)
    envs.pop("BUILD_COMPOSER_VERSION", None)
    envs.pop("BUILD_COMPOSER_INSTALL_GLOBAL", None)
    envs.pop("BUILD_PHP_NGINX_ENABLE_HTTPS", None)
    envs.pop("BUILD_PHP_ENABLE_HTTPS_REDIRECT", None)
    envs.pop("BUILD_COMPOSER_VENDOR_DIR", None)
    envs.pop("BUILD_COMPOSER_FILE", None)
    envs.pop("BUILD_COMPOSER_AUTH", None)
    envs.pop("COMPOSER_VENDOR_DIR", None)
    envs.pop("COMPOSER", None)
    envs.pop("COMPOSER_AUTH", None)
    envs.pop("BP_PHP_SESSION_HANDLER", None)
    envs.pop("BP_PHP_EXTENSIONS", None)
    envs.pop("BP_PHP_ZEND_EXTENSIONS", None)


def _drop_legacy_cnb_type_markers(envs):
    if str(envs.get("BUILD_TYPE", "")).strip().lower() == "cnb":
        envs.pop("BUILD_TYPE", None)
    if str(envs.get("TYPE", "")).strip().lower() == "cnb":
        envs.pop("TYPE", None)


def _strip_python_manager_specific_keys(envs, manager):
    manager = str(manager or "").strip().lower()

    envs.pop("BP_PIP_REQUIREMENT", None)
    envs.pop("BP_PIP_DEST_PATH", None)
    envs.pop("PIP_EXTRA_INDEX_URL", None)
    envs.pop("BUILD_PIP_EXTRA_INDEX_URL", None)

    if manager not in ("pip", "pipenv"):
        envs.pop("PIP_INDEX_URL", None)
        envs.pop("PIP_TRUSTED_HOST", None)
        envs.pop("BUILD_PIP_INDEX_URL", None)
        envs.pop("BUILD_PIP_TRUSTED_HOST", None)

    if manager != "poetry":
        envs.pop("BUILD_POETRY_SOURCE_NAME", None)
        envs.pop("BUILD_POETRY_SOURCE_URL", None)

    if manager != "conda":
        envs.pop("BUILD_CONDA_CHANNEL_URL", None)
        envs.pop("BUILD_CONDA_SOLVER", None)
    else:
        envs.pop("BUILD_PYTHON_PACKAGE_MANAGER_VERSION", None)


def _normalize_dotnet_cnb_legacy_aliases(envs):
    for source_key, target_key in DOTNET_CNB_LEGACY_TO_CURRENT_ALIASES:
        if _first_non_empty(envs, target_key):
            continue
        source_value = _first_non_empty(envs, source_key)
        if source_value:
            envs[target_key] = source_value


def _drop_dotnet_legacy_aliases(envs):
    for source_key, _ in DOTNET_CNB_LEGACY_TO_CURRENT_ALIASES:
        envs.pop(source_key, None)


def _first_non_empty(envs, *keys):
    envs = envs or {}
    for key in keys:
        value = envs.get(key)
        if value is None:
            continue
        if str(value).strip() == "":
            continue
        return value
    return ""


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
    if policy_key == "dotnet":
        parts = value.split(".")
        if len(parts) >= 2:
            return ".".join(parts[:2])
        return value
    return value


def _append_unique(items, value):
    if value and value not in items:
        items.append(value)


def _apply_cnb_policy_version_constraints(policy_key, visible_versions, allowed_versions, default_version):
    constraint = CNB_POLICY_VERSION_CONSTRAINTS.get(policy_key)
    if not constraint:
        return visible_versions, allowed_versions, default_version

    supported_versions = list(constraint.get("supported_versions") or [])
    supported_version_set = set(supported_versions)

    visible_versions = [version for version in (visible_versions or []) if version in supported_version_set]
    allowed_versions = [version for version in (allowed_versions or []) if version in supported_version_set]

    constrained_default = default_version if default_version in supported_version_set else ""
    preferred_default = constraint.get("default_version", "")
    if preferred_default and preferred_default in allowed_versions:
        constrained_default = preferred_default
    elif not constrained_default and allowed_versions:
        constrained_default = allowed_versions[0]
    elif not constrained_default and visible_versions:
        constrained_default = visible_versions[0]

    return visible_versions, allowed_versions, constrained_default


def _sort_cnb_policy_versions(versions):
    return sorted(versions or [], key=_cnb_policy_version_sort_key)


def _cnb_policy_version_sort_key(version):
    return [int(part) if str(part).isdigit() else -1 for part in str(version or "").split(".")]


def _is_truthy(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in ("1", "true", "yes", "on")
