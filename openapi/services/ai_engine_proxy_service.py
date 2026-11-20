# -*- coding: utf-8 -*-
import json
import logging
from itertools import chain
from typing import Any, List

import urllib3

from console.exception.main import ServiceHandleException

logger = logging.getLogger("default")


class AIEngineProxyService(object):
    ALLOWED_TARGETS = {
        ("GET", "v1/models"),
        ("POST", "v1/chat/completions"),
        ("POST", "v1/completions"),
        ("POST", "v1/embeddings"),
        ("POST", "v1/messages"),
    }

    def extract_bearer_token(self, authorization: Any) -> str:
        authorization = str(authorization or "").strip()
        if not authorization:
            raise ServiceHandleException("missing Authorization header", status_code=401)

        parts = authorization.split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
            raise ServiceHandleException("invalid Authorization format, expected Bearer <api-key>", status_code=401)
        return parts[1].strip()

    def extract_api_key(self, authorization: Any, api_key: Any = None) -> str:
        bearer = self.extract_bearer_token(authorization) if authorization else ""
        anthropic = str(api_key or "").strip()
        for credential in (bearer, anthropic):
            if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in credential):
                raise ServiceHandleException("invalid API key", status_code=401)
        if bearer and anthropic and bearer != anthropic:
            raise ServiceHandleException("conflicting API credentials", status_code=400)
        if not bearer and not anthropic:
            raise ServiceHandleException("API key required", status_code=401)
        return bearer or anthropic

    def resolve_region(self, team_name: str, region_name: Any = None) -> str:
        if region_name is None:
            return self.resolve_unique_region(team_name)
        team = self._get_team(team_name)
        if not team:
            raise ServiceHandleException("team not found", status_code=404)
        if region_name not in self._get_candidate_regions(team):
            raise ServiceHandleException("team is not active in this region", status_code=403)
        if not self._region_has_ai_engine(team.enterprise_id, region_name):
            raise ServiceHandleException("AI Engine is unavailable in this region", status_code=404)
        return region_name

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

        team = self._get_team(normalized_team)
        if not team:
            raise ServiceHandleException("team {} not found".format(normalized_team), status_code=404)

        # Revalidate live bindings; cached uniqueness can authorize a removed region.
        candidate_regions = list(dict.fromkeys(self._get_candidate_regions(team)))
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

        if lookup_failures:
            raise ServiceHandleException("failed to inspect ai-engine clusters", status_code=502)

        if len(matched_regions) == 1:
            return matched_regions[0]

        if len(matched_regions) > 1:
            raise ServiceHandleException(
                "team {} is bound to multiple ai-engine regions".format(normalized_team),
                status_code=409)

        raise ServiceHandleException("team {} has no available ai-engine cluster".format(normalized_team), status_code=404)

    def build_region_proxy_path(self, proxy_path: Any, query_string: str = "") -> str:
        normalized_path = str(proxy_path or "").strip().lstrip("/")
        path = "/v2/platform/backend/plugins/rainbond-ai-engine/{}".format(normalized_path)
        if query_string:
            return "{}?{}".format(path, query_string)
        return path

    def proxy_request(self,
                      request: Any,
                      region_name: str,
                      proxy_path: Any,
                      query_string: str = "",
                      team_name: str = "") -> Any:
        from www.apiclient.regionapi import RegionInvokeApi

        team = self._get_team(team_name)
        if not team:
            raise ServiceHandleException("team not found", status_code=404)
        if not getattr(team, "namespace", None):
            raise ServiceHandleException("team namespace unavailable", status_code=503)
        credential = self.extract_api_key(request.META.get("HTTP_AUTHORIZATION"), request.META.get("HTTP_X_API_KEY"))
        headers = {
            "X-AI-Team-Name": team.tenant_name,
            "X-AI-Region-Name": region_name,
            "X-AI-Team-Namespace": team.namespace,
            "X-Original-Authorization": "Bearer " + credential,
        }
        if request.META.get("HTTP_X_API_KEY"):
            headers["x-api-key"] = credential
        response = RegionInvokeApi().stream_proxy(request,
                                                  self.build_region_proxy_path(proxy_path, query_string),
                                                  region_name,
                                                  requests_args={
                                                      "headers": headers,
                                                      "retries": False
                                                  },
                                                  timeout=urllib3.Timeout(connect=10, read=None))
        if self._is_plugin_transport_error(response):
            raise ServiceHandleException("upstream ai-engine proxy failed", status_code=502)
        return response

    def _is_plugin_transport_error(self, response: Any) -> bool:
        if getattr(response, "status_code", None) != 502:
            return False
        if getattr(response, "streaming", False):
            if "application/json" not in response.get("Content-Type", "").lower():
                return False
            # Only inspect the bounded JSON error envelope. Inference SSE is
            # never read ahead; genuine provider errors retain all original bytes.
            stream = iter(response.streaming_content)
            prefix = []
            size = 0
            for chunk in stream:
                prefix.append(chunk)
                size += len(chunk)
                if size > 64 * 1024:
                    break
            response.streaming_content = chain(prefix, stream)
            if size > 64 * 1024:
                return False
            content = b"".join(prefix)
        else:
            content = response.content
        try:
            payload = json.loads(content.decode("utf-8"))
        except (AttributeError, TypeError, ValueError, UnicodeDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        transport_error = all((
            payload.get("code") == 502,
            payload.get("plugin") == "rainbond-ai-engine",
            str(payload.get("msg",
                            "")).startswith("plugin backend unavailable:"),
        ))
        if transport_error:
            response.close()
        return transport_error

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
        plugins = (body or {}).get("list") or []
        for plugin in plugins:
            if isinstance(plugin, dict) and plugin.get("name") == "rainbond-ai-engine":
                return True
        return False


ai_engine_proxy_service = AIEngineProxyService()
