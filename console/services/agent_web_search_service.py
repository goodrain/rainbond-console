# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict, List

import requests

from console.exception.main import ServiceHandleException
from console.services.agent_web_search_config_service import agent_web_search_config_service

logger = logging.getLogger("default")

EXA_SEARCH_URL = "https://api.exa.ai/search"
PERPLEXITY_CHAT_URL = "https://api.perplexity.ai/chat/completions"


class AgentWebSearchService(object):

    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        query = (query or "").strip()
        if not query:
            raise ServiceHandleException(msg="query is required", msg_show="搜索内容不能为空", status_code=400)
        config = agent_web_search_config_service.get_runtime_config()
        if not config.get("enabled", True):
            raise ServiceHandleException(msg="web search disabled", msg_show="联网搜索已关闭", status_code=403)
        api_key = config.get("api_key") or ""
        if not api_key:
            raise ServiceHandleException(msg="web search api key missing", msg_show="联网搜索 API Key 未配置", status_code=503)
        provider = config.get("provider") or "exa"
        limit = max(1, min(int(max_results or config.get("max_results") or 5), 10))
        timeout = max(1.0, min(float(config.get("fetch_timeout_ms") or 15000) / 1000.0, 60.0))
        if provider == "perplexity":
            return self._search_perplexity(query, limit, api_key, timeout)
        return self._search_exa(query, limit, api_key, timeout)

    def _search_exa(self, query: str, limit: int, api_key: str, timeout: float) -> Dict[str, Any]:
        try:
            response = requests.post(
                EXA_SEARCH_URL,
                headers={"x-api-key": api_key, "content-type": "application/json"},
                json={"query": query, "numResults": limit, "contents": {"text": {"maxCharacters": 1200}}},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            logger.warning("exa search failed: %s", exc)
            raise ServiceHandleException(msg="exa search failed", msg_show="联网搜索请求失败", status_code=502)
        if response.status_code >= 400:
            logger.warning("exa search status=%s body=%s", response.status_code, response.text[:300])
            raise ServiceHandleException(msg="exa search failed", msg_show="联网搜索服务返回错误", status_code=502)
        payload = response.json() if response.content else {}
        sources: List[Dict[str, Any]] = []
        for item in (payload.get("results") or [])[:limit]:
            if not item.get("url"):
                continue
            sources.append({
                "url": item["url"],
                "title": item.get("title") or "",
                "snippet": item.get("text") or "",
                "publishedAt": item.get("publishedDate") or "",
            })
        return {"provider": "exa", "sources": sources, "content": "", "truncated": len(sources) >= limit}

    def _search_perplexity(self, query: str, limit: int, api_key: str, timeout: float) -> Dict[str, Any]:
        try:
            response = requests.post(
                PERPLEXITY_CHAT_URL,
                headers={"Authorization": "Bearer {}".format(api_key), "content-type": "application/json"},
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": query}],
                    "max_tokens": 1200,
                },
                timeout=timeout,
            )
        except requests.RequestException as exc:
            logger.warning("perplexity search failed: %s", exc)
            raise ServiceHandleException(msg="perplexity search failed", msg_show="联网搜索请求失败", status_code=502)
        if response.status_code >= 400:
            logger.warning("perplexity status=%s body=%s", response.status_code, response.text[:300])
            raise ServiceHandleException(msg="perplexity search failed", msg_show="联网搜索服务返回错误", status_code=502)
        payload = response.json() if response.content else {}
        choices = payload.get("choices") or []
        content = ""
        if choices:
            content = ((choices[0].get("message") or {}).get("content") or "").strip()
        citations = payload.get("citations") or []
        sources = [{"url": url, "title": "", "snippet": ""} for url in citations[:limit] if url]
        return {"provider": "perplexity", "sources": sources, "content": content, "truncated": len(sources) >= limit}


agent_web_search_service = AgentWebSearchService()
