# -*- coding: utf-8 -*-
import logging
import time
from typing import Any, Dict, List

import requests

from console.exception.main import ServiceHandleException
from console.services.agent_web_search_config_service import agent_web_search_config_service

logger = logging.getLogger("default")

DEEPSEEK_SEARCH_URL = "https://api.deepseek.com/v1/tools/search"
DEEPSEEK_SEARCH_MAX_RESULTS = 50
DEEPSEEK_SNIPPET_MAX_CHARS = 1200
DEEPSEEK_SEARCH_TIMEOUT_SECONDS = 15.0


class AgentWebSearchService(object):

    RATE_LIMIT = 30
    RATE_WINDOW_SECONDS = 60

    def __init__(self) -> None:
        self._requests: Dict[str, List[float]] = {}

    def _check_rate_limit(self, scope: str) -> None:
        now = time.time()
        timestamps = [ts for ts in self._requests.get(scope, []) if now - ts < self.RATE_WINDOW_SECONDS]
        if len(timestamps) >= self.RATE_LIMIT:
            raise ServiceHandleException(
                msg="web search rate limited",
                msg_show="联网搜索请求过于频繁，请稍后再试",
                status_code=429,
            )
        timestamps.append(now)
        self._requests[scope] = timestamps

    def search(self, query: str, max_results: int = 5, scope: str = "global") -> Dict[str, Any]:
        query = (query or "").strip()
        if not query:
            raise ServiceHandleException(msg="query is required", msg_show="搜索内容不能为空", status_code=400)
        self._check_rate_limit(scope or "global")
        config = agent_web_search_config_service.get_runtime_config()
        if not config.get("enabled", True):
            raise ServiceHandleException(msg="web search disabled", msg_show="联网搜索已关闭", status_code=403)
        provider = config.get("provider") or "deepseek"
        if provider != "deepseek":
            raise ServiceHandleException(
                msg="unsupported web search provider",
                msg_show="联网搜索目前仅支持 DeepSeek",
                status_code=400,
            )
        api_key = config.get("api_key") or ""
        if not api_key:
            raise ServiceHandleException(
                msg="web search api key missing",
                msg_show="联网搜索 DeepSeek API Key 未配置",
                status_code=503,
            )
        limit = max(1, min(int(max_results or config.get("max_results") or 5), DEEPSEEK_SEARCH_MAX_RESULTS))
        timeout = DEEPSEEK_SEARCH_TIMEOUT_SECONDS
        result = self._search_deepseek(query, limit, api_key, timeout)
        logger.info(
            "agent_web_search scope=%s provider=deepseek query_len=%s sources=%s",
            scope or "global", len(query), len(result.get("sources") or []),
        )
        return result

    def _search_deepseek(self, query: str, limit: int, api_key: str, timeout: float) -> Dict[str, Any]:
        try:
            response = requests.post(
                DEEPSEEK_SEARCH_URL,
                headers={"Authorization": "Bearer {}".format(api_key), "content-type": "application/json"},
                json={"query": query, "count": limit, "need_content": False},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            logger.warning("deepseek search failed: %s", exc)
            raise ServiceHandleException(msg="deepseek search failed", msg_show="联网搜索请求失败", status_code=502)
        if response.status_code >= 400:
            logger.warning("deepseek search status=%s body=%s", response.status_code, response.text[:300])
            if response.status_code in (401, 403):
                raise ServiceHandleException(
                    msg="deepseek search unauthorized", msg_show="DeepSeek API Key 无效", status_code=401)
            raise ServiceHandleException(msg="deepseek search failed", msg_show="联网搜索服务返回错误", status_code=502)
        payload = response.json() if response.content else {}
        results = payload.get("results") or []
        sources: List[Dict[str, Any]] = []
        for item in results[:limit]:
            if not item.get("url"):
                continue
            snippet = item.get("snippet") or item.get("summary") or ""
            sources.append({
                "url": item["url"],
                "title": item.get("title") or "",
                "snippet": snippet[:DEEPSEEK_SNIPPET_MAX_CHARS],
                "publishedAt": item.get("date") or "",
            })
        return {"provider": "deepseek", "sources": sources, "content": "", "truncated": len(results) >= limit}


agent_web_search_service = AgentWebSearchService()
