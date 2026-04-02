# -*- coding: utf-8 -*-
import copy
import json


STATE_KEY = "_source_build_state"
TOP_LEVEL_COMPILE_ENV_KEYS = ("language", "runtimes", "procfile", "dependencies")


def split_detected_languages(languages):
    if not languages:
        return []
    if isinstance(languages, (list, tuple)):
        parts = languages
    else:
        parts = str(languages).split(",")

    seen = set()
    result = []
    for part in parts:
        value = str(part or "").strip()
        if not value:
            continue
        lower = value.lower()
        if lower in seen:
            continue
        seen.add(lower)
        result.append(value)
    return result


def normalize_detected_languages(languages):
    parts = split_detected_languages(languages)
    if not parts:
        return ""
    non_dockerfile = [part for part in parts if part.lower() != "dockerfile"]
    dockerfile = [part for part in parts if part.lower() == "dockerfile"]
    return ",".join(non_dockerfile + dockerfile)


def pick_preferred_language(languages):
    parts = split_detected_languages(normalize_detected_languages(languages))
    if not parts:
        return ""
    return parts[0]


def _clone_dict(value):
    if not isinstance(value, dict):
        return {}
    return copy.deepcopy(value)


def _normalize_language_snapshot(snapshot):
    snapshot = _clone_dict(snapshot)
    compile_env = _clone_dict(snapshot.get("compile_env"))
    build_env_dict = _clone_dict(snapshot.get("build_env_dict"))
    normalized = {
        "compile_env": compile_env,
        "build_env_dict": build_env_dict,
    }
    if "build_strategy" in snapshot:
        normalized["build_strategy"] = snapshot.get("build_strategy", "") or ""
    if "cmd" in snapshot:
        normalized["cmd"] = snapshot.get("cmd", "") or ""
    return normalized


def _normalize_state(state):
    state = _clone_dict(state)
    normalized = {
        "detected_defaults": {},
        "user_saved": {},
    }
    for bucket in ("detected_defaults", "user_saved"):
        values = state.get(bucket, {})
        if not isinstance(values, dict):
            continue
        for language, snapshot in values.items():
            key = str(language or "").strip()
            if not key:
                continue
            normalized[bucket][key] = _normalize_language_snapshot(snapshot)
    return normalized


def read_compile_env_state(payload):
    raw = payload
    if isinstance(payload, str):
        try:
            raw = json.loads(payload)
        except (TypeError, ValueError):
            raw = {}
    if not isinstance(raw, dict):
        raw = {}

    compile_env = {}
    for key in TOP_LEVEL_COMPILE_ENV_KEYS:
        if key in raw:
            compile_env[key] = copy.deepcopy(raw[key])
    state = _normalize_state(raw.get(STATE_KEY, {}))
    return compile_env, state


def build_compile_env_payload(compile_env, state):
    payload = {}
    compile_env = _clone_dict(compile_env)
    for key in TOP_LEVEL_COMPILE_ENV_KEYS:
        if key in compile_env:
            payload[key] = copy.deepcopy(compile_env[key])

    normalized_state = _normalize_state(state)
    if normalized_state["detected_defaults"] or normalized_state["user_saved"]:
        payload[STATE_KEY] = normalized_state
    return payload


def update_language_snapshot(state, bucket, language, snapshot):
    if bucket not in ("detected_defaults", "user_saved"):
        raise ValueError("bucket must be detected_defaults or user_saved")
    key = str(language or "").strip()
    normalized = _normalize_state(state)
    if not key:
        return normalized
    normalized[bucket][key] = _normalize_language_snapshot(snapshot)
    return normalized


def restore_language_snapshot(state, target_language, fallback_compile_env=None):
    normalized = _normalize_state(state)
    target_language = str(target_language or "").strip()
    detected = _normalize_language_snapshot(normalized["detected_defaults"].get(target_language))
    user_saved = _normalize_language_snapshot(normalized["user_saved"].get(target_language))

    compile_env = _clone_dict(fallback_compile_env)
    compile_env.update(detected.get("compile_env", {}))
    compile_env.update(user_saved.get("compile_env", {}))

    build_env_dict = _clone_dict(detected.get("build_env_dict"))
    build_env_dict.update(user_saved.get("build_env_dict", {}))

    if "build_strategy" in user_saved:
        build_strategy = user_saved.get("build_strategy", "") or ""
    else:
        build_strategy = detected.get("build_strategy", "") or ""

    if "cmd" in user_saved:
        cmd = user_saved.get("cmd", "") or ""
    else:
        cmd = detected.get("cmd", "") or ""

    return {
        "compile_env": compile_env,
        "build_env_dict": build_env_dict,
        "build_strategy": build_strategy,
        "cmd": cmd,
    }
