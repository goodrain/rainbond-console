# -*- coding: utf-8 -*-
import json
from typing import Any, Dict, List, Optional, Tuple

from console.services.app_config import compile_env_service, env_var_service
from console.utils import cnb_build as cnb_build_utils
from console.utils.source_build_state import (build_compile_env_payload, normalize_detected_languages,
                                              pick_preferred_language, read_compile_env_state,
                                              restore_language_snapshot, split_detected_languages,
                                              update_language_snapshot)
from www.models.main import TenantServiceEnv


class SourceBuildStateService(object):
    def _resolve_lang_update_build_strategy(self, language: str, service_build_strategy: str = "") -> str:
        helper = getattr(cnb_build_utils, "resolve_lang_update_build_strategy", None)
        if callable(helper):
            return helper(language, service_build_strategy)  # type: ignore[no-any-return]

        current = (service_build_strategy or "").strip().lower()
        if cnb_build_utils.supports_cnb_build_strategy(language):
            return current or "cnb"
        return ""

    def _default_compile_env(self, language: str) -> dict:
        payload = compile_env_service.get_service_default_env_by_language(language) or {}
        if payload and "language" not in payload:
            payload["language"] = language
        return payload

    def _read(self, service: Any) -> Tuple[Optional[TenantServiceEnv], dict, dict]:
        compile_env = compile_env_service.get_service_compile_env(service)
        compile_env_payload: dict = {}
        state: dict = {}
        if compile_env and compile_env.user_dependency:
            compile_env_payload, state = read_compile_env_state(compile_env.user_dependency)
        return compile_env, compile_env_payload, state

    def _write(self, service: Any, compile_env_payload: dict, state: dict, language: str = "") -> None:
        compile_env = compile_env_service.get_service_compile_env(service)
        record_language = language or (compile_env_payload or {}).get("language") or getattr(service, "language", "")
        payload = build_compile_env_payload(compile_env_payload, state)
        if compile_env:
            update_params = {"user_dependency": json.dumps(payload), "language": record_language}
            compile_env_service.update_service_compile_env(service, **update_params)
        else:
            compile_env_service.save_compile_env(
                service,
                record_language,  # type: ignore[arg-type]  # NOTE: record_language may be None/Any when service.language untyped
                json.dumps({"language": record_language}),
                json.dumps(payload))

    def _get_build_env_dict(self, service: Any, language: str) -> dict:
        build_env_dict: dict = {}
        build_envs = env_var_service.get_service_build_envs(service)
        if build_envs:
            for build_env in build_envs:
                build_env_dict[build_env.attr_name] = build_env.attr_value
        return cnb_build_utils.sanitize_build_env_dict_for_language(build_env_dict, language)  # type: ignore[no-any-return]

    def build_snapshot(
        self,
        service: Any,
        language: str = "",
        compile_env_payload: Optional[dict] = None,
        build_env_dict: Optional[dict] = None,
        build_strategy: Optional[str] = None,
        cmd: Optional[str] = None,
    ) -> Dict[str, Any]:
        effective_language = pick_preferred_language(language or getattr(service, "language", ""))
        if not effective_language:
            effective_language = language or getattr(service, "language", "")

        if not compile_env_payload:
            _, compile_env_payload, _ = self._read(service)
        compile_env_payload = dict(compile_env_payload or self._default_compile_env(effective_language))
        if effective_language:
            compile_env_payload["language"] = effective_language

        if build_env_dict is None:
            build_env_dict = self._get_build_env_dict(service, effective_language)

        if build_strategy is None:
            build_strategy = cnb_build_utils.resolve_build_strategy(getattr(service, "build_strategy", ""), build_env_dict)

        if cmd is None:
            cmd = getattr(service, "cmd", "") or ""

        return {
            "compile_env": compile_env_payload,
            "build_env_dict": build_env_dict,
            "build_strategy": build_strategy or "",
            "cmd": cmd or "",
        }

    def save_user_snapshot(self, service: Any, language: str = "", compile_env_payload: Optional[dict] = None) -> None:
        effective_language = pick_preferred_language(language or getattr(service, "language", ""))
        if not effective_language or effective_language.lower() == "dockerfile":
            return

        _, current_compile_env, state = self._read(service)
        current_compile_env = compile_env_payload or current_compile_env or self._default_compile_env(effective_language)
        current_compile_env["language"] = effective_language
        snapshot = self.build_snapshot(service, effective_language, compile_env_payload=current_compile_env)
        state = update_language_snapshot(state, "user_saved", effective_language, snapshot)
        self._write(service, current_compile_env, state, language=effective_language)

    def save_detected_defaults(
        self,
        service: Any,
        detected_languages: Any,
        primary_snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        ordered_languages: List[str] = split_detected_languages(normalize_detected_languages(detected_languages))
        preferred_language: str = pick_preferred_language(detected_languages)
        if not ordered_languages:
            return

        _, current_compile_env, state = self._read(service)
        if primary_snapshot and primary_snapshot.get("compile_env"):
            current_compile_env = dict(primary_snapshot.get("compile_env") or {})
        if not current_compile_env:
            current_compile_env = self._default_compile_env(preferred_language or ordered_languages[0])
        if preferred_language:
            current_compile_env["language"] = preferred_language

        if preferred_language:
            state = update_language_snapshot(
                state,
                "detected_defaults",
                preferred_language,
                primary_snapshot or self.build_snapshot(
                    service, preferred_language, compile_env_payload=current_compile_env))

        for language in ordered_languages:
            if language == preferred_language:
                continue
            state = update_language_snapshot(
                state,
                "detected_defaults",
                language,
                {
                    "compile_env": self._default_compile_env(language),
                    "build_env_dict": {},
                    "build_strategy": self._resolve_lang_update_build_strategy(language, ""),
                    "cmd": "" if language.lower() == "dockerfile" else "start web",
                })

        self._write(service, current_compile_env, state, language=preferred_language or ordered_languages[0])

    def restore_language(self, service: Any, target_language: str) -> Dict[str, Any]:
        effective_language = pick_preferred_language(target_language) or target_language
        _, current_compile_env, state = self._read(service)
        restored = restore_language_snapshot(state, effective_language, self._default_compile_env(effective_language))
        compile_env_payload = dict(restored.get("compile_env") or self._default_compile_env(effective_language))
        compile_env_payload["language"] = effective_language
        build_env_dict = cnb_build_utils.sanitize_build_env_dict_for_language(restored.get("build_env_dict", {}),
                                                                              effective_language)
        restored["compile_env"] = compile_env_payload
        restored["build_env_dict"] = build_env_dict
        self._write(service, compile_env_payload, state, language=effective_language)
        return restored


source_build_state_service = SourceBuildStateService()
