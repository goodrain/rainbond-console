# -*- coding: utf-8 -*-
import logging
import time
from typing import Any, List, Optional

from console.exception.main import ServiceHandleException

logger = logging.getLogger("default")


class AIEngineProxyService(object):
    ALLOWED_TARGETS = {
        ("GET", "v1/models"),
        ("POST", "v1/chat/completions"),
        ("POST", "v1/completions"),
        ("POST", "v1/embeddings"),
    }

    def __init__(self, cache_ttl_seconds: int = 30) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._region_cache: dict = {}

    def extract_bearer_token(self, authorization: Any) -> str:
        authorization = str(authorization or "").strip()
        if not authorization:
            raise ServiceHandleException("missing Authorization header", status_code=401)

        parts = authorization.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            raise ServiceHandleException("invalid Authorization format, expected Bearer <api-key>", status_code=401)
        return parts[1].strip()

    def validate_proxy_target(self, method: Any, proxy_path: Any) -> str:
        normalized_path = str(proxy_path or "").strip().strip("/")
        normalized_method = str(method or "").upper()
        if (normalized_method, normalized_path) not in self.ALLOWED_TARGETS:
            raise ServiceHandleException(
                "path {} with method {} is not allowed".format(normalized_path or "/", normalized_method or "UNKNOWN"),
                status_code=405)
        return normalized_path

    def resolve_unique_region(self, team_name: str) -> Any:
        normalized_team = str(team_name or "").strip()
        if not normalized_team:
            raise ServiceHandleException("team not found", status_code=404)

        cached_region = self._get_cached_region(normalized_team)
        if cached_region:
            return cached_region

        team = self._get_team(normalized_team)
        if not team:
            raise ServiceHandleException("team {} not found".format(normalized_team), status_code=404)

        candidate_regions = self._get_candidate_regions(team)
        if not candidate_regions:
            raise ServiceHandleException("team {} has no active regions".format(normalized_team), status_code=404)

        matched_regions: list = []
        lookup_failures: list = []
        for region_name in candidate_regions:
            try:
                if self._region_has_ai_engine(team.enterprise_id, region_name):
                    matched_regions.append(region_name)
            except Exception as err:
                logger.warning(
                    "failed to inspect ai-engine plugin on region=%s team=%s: %s",
                    region_name,
                    normalized_team,
                    err,
                )
                lookup_failures.append(region_name)

        if len(matched_regions) == 1:
            self._cache_region(normalized_team, matched_regions[0])
            return matched_regions[0]

        if len(matched_regions) > 1:
            raise ServiceHandleException(
                "team {} is bound to multiple ai-engine regions".format(normalized_team),
                status_code=409)

        if lookup_failures and len(lookup_failures) == len(candidate_regions):
            raise ServiceHandleException(
                "failed to inspect ai-engine clusters for team {}".format(normalized_team),
                status_code=502)

        raise ServiceHandleException("team {} has no available ai-engine cluster".format(normalized_team), status_code=404)

    def build_region_proxy_path(self, proxy_path: Any, query_string: str = "") -> str:
        normalized_path = str(proxy_path or "").strip().lstrip("/")
        path = "/v2/platform/backend/plugins/rainbond-ai-engine/{}".format(normalized_path)
        if query_string:
            return "{}?{}".format(path, query_string)
        return path

    def proxy_request(self, request: Any, region_name: str, proxy_path: Any, query_string: str = "") -> Any:
        from www.apiclient.regionapi import RegionInvokeApi

        region_api = RegionInvokeApi()
        return region_api.proxy(request, self.build_region_proxy_path(proxy_path, query_string), region_name)

    def _get_cached_region(self, team_name: str) -> Optional[str]:
        cache_item = self._region_cache.get(team_name)
        if not cache_item:
            return None
        if cache_item["expires_at"] <= time.time():
            self._region_cache.pop(team_name, None)
            return None
        return cache_item["region_name"]

    def _cache_region(self, team_name: str, region_name: str) -> None:
        self._region_cache[team_name] = {
            "region_name": region_name,
            "expires_at": time.time() + self.cache_ttl_seconds,
        }

    def _get_team(self, team_name: str) -> Any:
        from console.repositories.team_repo import team_repo

        return team_repo.get_team_by_team_name(team_name)

    def _get_candidate_regions(self, team: Any) -> List[Any]:
        from www.models.main import TenantRegionInfo

        # NOTE: legacy int (1/0) used for BooleanField lookups; stubs expect bool.
        region_infos = TenantRegionInfo.objects.filter(
            tenant_id=team.tenant_id, is_active=1, is_init=1)  # type: ignore[misc]
        return [item.region_name for item in region_infos]

    def _region_has_ai_engine(self, enterprise_id: str, region_name: str) -> bool:
        from www.apiclient.regionapi import RegionInvokeApi

        region_api = RegionInvokeApi()
        _, body = region_api.list_plugins(enterprise_id, region_name, False)
        # NOTE: region api body may be None per stubs; backlog null-safety.
        plugins = body.get("list") or []  # type: ignore[union-attr]
        for plugin in plugins:
            if isinstance(plugin, dict) and plugin.get("name") == "rainbond-ai-engine":
                return True
        return False


ai_engine_proxy_service = AIEngineProxyService()
