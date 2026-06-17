"""
该文件主要是对管理端构建语言版本的操作，包括创建、更新、删除、展示等操作。
"""
import re
from typing import Any, Dict, List, Optional

from console.repositories.app_config import compile_env_repo

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


def _normalize_long_version_record(record: Any) -> Any:
    if not isinstance(record, dict):
        return record
    normalized = dict(record)
    normalized.setdefault("build_strategy", "slug")
    if normalized.get("is_allowed") is None:
        normalized["is_allowed"] = True
    return normalized


def _normalize_long_version_response(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    normalized = dict(data)
    if isinstance(normalized.get("bean"), dict):
        normalized["bean"] = _normalize_long_version_record(normalized["bean"])
    if isinstance(normalized.get("list"), list):
        normalized["list"] = [_normalize_long_version_record(item) for item in normalized["list"]]
    return normalized


class RegionLongVersion(object):
    def show_long_version(self, eid: str, region_id: str, language: str, build_strategy: str = "") -> Any:
        data = region_api.get_lang_version(eid, region_id, language, "", build_strategy)
        return _normalize_long_version_response(data)

    def create_long_version(
        self,
        eid: str,
        region_id: str,
        lang: str,
        version: str,
        event_id: str,
        file_name: str,
        build_strategy: str = "slug",
        is_allowed: Optional[bool] = True,
    ) -> Any:
        data = {
            "lang": lang,
            "version": version,
            "event_id": event_id,
            "file_name": file_name,
            "show": True,
            "build_strategy": build_strategy or "slug",
            "is_allowed": True if is_allowed is None else is_allowed,
        }
        return _normalize_long_version_response(region_api.create_lang_version(eid, region_id, data))

    def update_long_version(
        self,
        eid: str,
        region_id: str,
        lang: str,
        version: str,
        show: Any,
        first_choice: Any,
        build_strategy: Optional[str] = None,
        is_allowed: Optional[bool] = None,
    ) -> Any:
        data: Dict[str, Any] = {
            "lang": lang,
            "version": version,
            "show": show,
            "first_choice": first_choice
        }
        if build_strategy:
            data["build_strategy"] = build_strategy
        if is_allowed is not None:
            data["is_allowed"] = is_allowed
        return _normalize_long_version_response(region_api.update_lang_version(eid, region_id, data))

    def delete_long_version(
        self,
        eid: str,
        region_id: str,
        lang: str,
        version: str,
        build_strategy: Optional[str] = None,
    ) -> Any:
        data: Dict[str, Any] = {
            "lang": lang,
            "version": version,
        }
        if build_strategy:
            data["build_strategy"] = build_strategy
        use_components = compile_env_repo.get_lang_version_in_use(lang, version)
        if use_components:
            return use_components
        region_api.delete_lang_version(eid, region_id, data)
        return ""

    def is_valid_version(self, version_str: str) -> bool:
        pattern = r'^[a-z0-9]+([-\.][0-9a-zA-Z]+)*$'
        if len(version_str) > 64:
            return False
        return bool(re.match(pattern, version_str))

    def is_valid_image(self, image_name: str) -> bool:
        pattern = r'^[a-z0-9]+([._-][a-z0-9]+)*(\/[a-z0-9]+([._-][a-z0-9]+)*)*(\:[a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*)?$'
        return bool(re.match(pattern, image_name))


region_lang_version = RegionLongVersion()


class RegionCNBConfig(object):
    def show_cnb_frameworks(self, eid: str, region_id: str, lang: str = "nodejs") -> Any:
        return region_api.get_cnb_frameworks(eid, region_id, lang)


region_cnb_config = RegionCNBConfig()
