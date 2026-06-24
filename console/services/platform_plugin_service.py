# -*- coding: utf8 -*-
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from console.appstore.appstore import app_store
from console.exception.main import ServiceHandleException
from console.models.main import AppMarket, RegionConfig
from console.repositories.app import (
    PLATFORM_PLUGIN_DEFAULT_URL,
    PLATFORM_PLUGIN_MARKET_DOMAIN,
    PLATFORM_PLUGIN_MARKET_NAME,
    app_market_repo,
)
from console.repositories.group import group_repo, tenant_service_group_repo
from console.repositories.region_app import region_app_repo
from console.repositories.region_repo import region_repo
from console.services.app import app_market_service
from console.services.group_service import group_service
from console.services.license import license_service
from console.services.market_app.app_upgrade import AppUpgrade
from console.services.market_app_service import market_app_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.utils.offline import is_cloud_market_disabled
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroup, Tenants

region_api = RegionInvokeApi()
logger = logging.getLogger("default")

# 合成市场名 / domain / 兜底 URL 都从 repository 层导入, 跟通用升级链路的解析逻辑保持一致.
# 这里给两个别名 (MARKET_HOST / MARKET_DOMAIN) 仅为兼容现有引用; 新代码请直接用 PLATFORM_PLUGIN_* 常量.
MARKET_HOST = PLATFORM_PLUGIN_DEFAULT_URL
MARKET_DOMAIN = PLATFORM_PLUGIN_MARKET_DOMAIN
PLUGIN_TEAM_NAME = "rbd-plugins"
PLUGIN_TEAM_ALIAS = "平台插件"
VM_PLATFORM_PLUGIN_ID = "rainbond-vm"
VM_PLATFORM_RUNTIME_GUARD_MSG = "虚拟机功能未正常运行，不允许执行虚拟机相关操作"
MARKET_PLUGIN_CACHE_TTL_SECONDS = 60
REGION_ARCH_CACHE_TTL_SECONDS = 60
KNOWN_ARCHES = ("amd64", "arm64")
DEFAULT_ARCH = "amd64"


class PlatformPluginService(object):
    ARCH_PLUGIN_SUFFIXES = ("-ARM64", "-AMD64")

    def __init__(self) -> None:
        self._market_plugin_cache: Dict[str, Any] = {}
        self._market_plugin_cache_lock = threading.Lock()
        self._region_arch_cache: Dict[str, Any] = {}
        self._region_arch_cache_lock = threading.Lock()

    def clear_market_plugin_cache(self) -> None:
        with self._market_plugin_cache_lock:
            self._market_plugin_cache.clear()

    def clear_region_arches_cache(self) -> None:
        with self._region_arch_cache_lock:
            self._region_arch_cache.clear()

    @staticmethod
    def _get_region_arch_cache_ttl_seconds() -> int:
        try:
            return int(os.environ.get("REGION_ARCH_CACHE_TTL_SECONDS", REGION_ARCH_CACHE_TTL_SECONDS))
        except (TypeError, ValueError):
            return REGION_ARCH_CACHE_TTL_SECONDS

    def _get_plugin_arch(self, plugin_info: Any) -> str:
        """读取 market plugin 记录的 arch 字段, 兜底为 amd64.

        market platform-plugins 接口在返回结构里携带顶层 arch 字段
        (rbd-app-server PortalSite 0f3cd4a77 起), 取值 amd64 / arm64.
        老版本市场或异常值兜底 amd64, 与 app_template 默认行为保持一致.
        """
        if not isinstance(plugin_info, dict):
            return DEFAULT_ARCH
        arch = (plugin_info.get("arch") or "").strip().lower()
        if arch in KNOWN_ARCHES:
            return arch
        return DEFAULT_ARCH

    def _get_region_arches(self, region_name: str, now: Optional[float] = None) -> Set[str]:
        """返回集群节点支持的架构集合.

        失败 fallback 为全集 {amd64, arm64}, 避免单点接口异常导致 ARM 集群
        看不到 ARM 版本插件. 同 region 60s 内缓存, 避免顶栏轮询打爆 region API.
        """
        ttl = self._get_region_arch_cache_ttl_seconds()
        now = time.time() if now is None else now
        if ttl > 0:
            with self._region_arch_cache_lock:
                entry = self._region_arch_cache.get(region_name)
                if entry and entry["expires_at"] > now:
                    return set(entry["arches"])

        try:
            _, body = region_api.get_cluster_nodes_arch(region_name)
            raw = (body or {}).get("list") or []
            arches = {str(item).strip().lower() for item in raw if item}
            arches = {a for a in arches if a in KNOWN_ARCHES}
            if not arches:
                arches = set(KNOWN_ARCHES)
        except Exception as e:
            logger.warning("get region arches failed region=%s: %s", region_name, e)
            arches = set(KNOWN_ARCHES)

        if ttl > 0:
            with self._region_arch_cache_lock:
                self._region_arch_cache[region_name] = {
                    "expires_at": now + ttl,
                    "arches": set(arches),
                }
        return arches

    @staticmethod
    def _get_market_plugin_cache_ttl_seconds() -> int:
        try:
            return int(os.environ.get("MARKET_PLUGIN_CACHE_TTL_SECONDS", MARKET_PLUGIN_CACHE_TTL_SECONDS))
        except (TypeError, ValueError):
            return MARKET_PLUGIN_CACHE_TTL_SECONDS

    @staticmethod
    def _copy_market_plugins(plugins: Any) -> List[Any]:
        return [dict(item) if isinstance(item, dict) else item for item in (plugins or [])]

    def _strip_plugin_arch_suffix(self, plugin_id: Any) -> str:
        plugin_id = str(plugin_id or "").strip()
        upper_plugin_id = plugin_id.upper()
        for suffix in self.ARCH_PLUGIN_SUFFIXES:
            if upper_plugin_id.endswith(suffix):
                return plugin_id[:-len(suffix)]
        return plugin_id

    def _resolve_plugin_mapping_app_key(self, plugin_mapping: Any, plugin_id: Any) -> Optional[str]:
        plugin_id = str(plugin_id or "").strip()
        if not plugin_id or not plugin_mapping:
            return None
        if plugin_id in plugin_mapping:
            return plugin_mapping[plugin_id]
        normalized_plugin_id = self._strip_plugin_arch_suffix(plugin_id)
        for mapping_plugin_id, app_key in plugin_mapping.items():
            if self._strip_plugin_arch_suffix(mapping_plugin_id) == normalized_plugin_id:
                return app_key
        return None

    def _is_plugin_authorized(self, plugin_mapping: Any, plugin_id: Any) -> bool:
        return bool(self._resolve_plugin_mapping_app_key(plugin_mapping, plugin_id))

    def _extract_arch_hint(self, plugin_info: Any) -> Any:
        if not isinstance(plugin_info, dict):
            return ""
        arch_keys = [
            "arch",
            "architecture",
            "architectures",
            "arches",
            "supported_arch",
            "supported_arches",
            "supported_architectures",
            "support_arch",
            "support_arches",
            "support_architectures",
            "build_arch",
            "build_arches",
            "version_arch",
            "version_arches",
            "latest_version_arch",
            "latest_version_arches",
            "template_arch",
            "template_arches",
        ]
        for key in arch_keys:
            value = plugin_info.get(key)
            if value not in (None, "", [], {}):
                return value
        return ""

    def _plugin_debug_summary(self, plugin_info: Any) -> Dict[str, Any]:
        if not plugin_info:
            return {}
        return {
            "plugin_id": plugin_info.get("plugin_id", ""),
            "app_key": plugin_info.get("appKeyID") or plugin_info.get("app_key", ""),
            "app_level": self._normalize_app_level(plugin_info),
            "plugin_name": plugin_info.get("plugin_name") or plugin_info.get("name", ""),
            "latest_version": plugin_info.get("latest_version", ""),
            "arch_hint": self._extract_arch_hint(plugin_info),
            "keys": sorted(plugin_info.keys()),
        }

    def _get_license_bean(self, enterprise_id: str, region_name: str) -> Dict[str, Any]:
        try:
            body = license_service.get_license_status(enterprise_id, region_name)
            return body.get("bean", {}) if body else {}
        except Exception as e:
            logger.warning("Failed to get license status: %s", e)
            return {}

    def _get_default_market(self, enterprise_id: str) -> AppMarket:
        markets = app_market_repo.get_app_markets(enterprise_id)
        app_market_repo.create_default_app_market_if_not_exists(markets, enterprise_id, None)
        market = app_market_repo.get_app_markets(enterprise_id).first()
        if not market:
            raise ServiceHandleException(msg="no found app market", msg_show="默认应用市场不存在", status_code=404)
        return market

    def _build_platform_market(self, enterprise_id: str) -> AppMarket:
        default_market = self._get_default_market(enterprise_id)
        return AppMarket(
            name=PLATFORM_PLUGIN_MARKET_NAME,
            url=default_market.url or MARKET_HOST,
            domain=MARKET_DOMAIN,
            access_key=default_market.access_key,
        )

    def _get_market_platform_plugins(self, enterprise_id: str) -> Tuple[AppMarket, List[Any]]:
        market = self._build_platform_market(enterprise_id)
        if is_cloud_market_disabled():
            logger.debug("platform plugin market fetch skipped because cloud market is disabled enterprise_id=%s", enterprise_id)
            return market, []
        logger.debug(
            "platform plugin market fetch enterprise_id=%s market_url=%s market_domain=%s has_access_key=%s",
            enterprise_id,
            market.url,
            market.domain,
            bool(market.access_key),
        )
        data = app_store.get_platform_plugins(market, page=1, page_size=-1)
        plugins = data.get("plugins", []) if data else []
        logger.debug(
            "platform plugin market fetch result enterprise_id=%s plugin_count=%s",
            enterprise_id,
            len(plugins),
        )
        return market, plugins

    def _get_market_platform_plugins_cached(self, enterprise_id: str, now: Optional[float] = None) -> Tuple[AppMarket, List[Any]]:
        ttl = self._get_market_plugin_cache_ttl_seconds()
        if ttl <= 0:
            return self._get_market_platform_plugins(enterprise_id)

        now = time.time() if now is None else now
        cache_key = enterprise_id
        with self._market_plugin_cache_lock:
            entry = self._market_plugin_cache.get(cache_key)
            if entry and entry["expires_at"] > now:
                logger.debug(
                    "platform plugin market cache hit enterprise_id=%s plugin_count=%s ttl_remaining_ms=%.1f",
                    enterprise_id,
                    len(entry["plugins"]),
                    (entry["expires_at"] - now) * 1000,
                )
                return entry["market"], self._copy_market_plugins(entry["plugins"])

        logger.debug("platform plugin market cache miss enterprise_id=%s", enterprise_id)
        market, plugins = self._get_market_platform_plugins(enterprise_id)
        cached_plugins = self._copy_market_plugins(plugins)
        with self._market_plugin_cache_lock:
            self._market_plugin_cache[cache_key] = {
                "expires_at": now + ttl,
                "market": market,
                "plugins": cached_plugins,
            }
        return market, self._copy_market_plugins(cached_plugins)

    def _get_installed_plugins(self, enterprise_id: str, region_name: str) -> Dict[str, Any]:
        installed_plugins = {}
        try:
            _, body = region_api.list_plugins(enterprise_id, region_name, False)
            plugins = body.get("list") or []  # type: ignore[union-attr]  # NOTE: body is dict|None; callers already wrap in try/except
            for plugin in plugins:
                installed_plugins[plugin.get("name", "")] = plugin
        except Exception as e:
            logger.warning("Failed to list region plugins: %s", e)
        return installed_plugins

    def get_vm_plugin_status(self, enterprise_id: str, region_name: str) -> str:
        installed_plugins = self._get_installed_plugins(enterprise_id, region_name)
        vm_plugin = installed_plugins.get(VM_PLATFORM_PLUGIN_ID) or {}
        return str(vm_plugin.get("status", "") or "").upper()

    def is_vm_plugin_running(self, enterprise_id: str, region_name: str) -> bool:
        return self.get_vm_plugin_status(enterprise_id, region_name) == "RUNNING"

    def ensure_vm_plugin_running(self, enterprise_id: str, region_name: str) -> None:
        if self.is_vm_plugin_running(enterprise_id, region_name):
            return
        raise ServiceHandleException(
            msg="vm plugin not running",
            msg_show=VM_PLATFORM_RUNTIME_GUARD_MSG,
            status_code=412,
        )

    def _get_region_app_id_map(self, region_name: str, installed_plugins: Dict[str, Any]) -> Dict[str, Any]:
        region_app_id_map: Dict[str, Any] = {}
        region_app_ids: List[Any] = []
        for plugin in installed_plugins.values():
            region_app_id = plugin.get("region_app_id", "")
            if region_app_id:
                region_app_ids.append(region_app_id)
        if not region_app_ids:
            return region_app_id_map
        try:
            region_apps = region_app_repo.list_by_region_app_ids(region_name, region_app_ids)
            for region_app in region_apps:
                region_app_id_map[region_app.region_app_id] = region_app.app_id
        except Exception as e:
            logger.warning("Failed to map region_app_ids: %s", e)
        return region_app_id_map

    def _normalize_app_level(self, plugin_info: Any) -> str:
        return plugin_info.get("appLevel") or plugin_info.get("app_level") or "enterprise"

    def _select_market_plugin(self, market_plugins: List[Any], plugin_id: str, plugin_mapping: Any) -> Optional[Any]:
        candidates = [item for item in market_plugins if item.get("plugin_id") == plugin_id]
        if not candidates:
            logger.debug("platform plugin select plugin_id=%s reason=no_candidates", plugin_id)
            return None

        candidate_summaries = [self._plugin_debug_summary(item) for item in candidates]
        free_candidates = [item for item in candidates if self._normalize_app_level(item) == "free"]
        if free_candidates:
            selected = free_candidates[0]
            logger.debug(
                "platform plugin select plugin_id=%s reason=prefer_free candidates=%s selected=%s",
                plugin_id,
                json.dumps(candidate_summaries, ensure_ascii=False, sort_keys=True),
                json.dumps(self._plugin_debug_summary(selected), ensure_ascii=False, sort_keys=True),
            )
            return selected

        app_key = self._resolve_plugin_mapping_app_key(plugin_mapping, plugin_id)
        if app_key:
            for item in candidates:
                item_app_key = item.get("appKeyID") or item.get("app_key")
                if item_app_key == app_key:
                    logger.debug(
                        "platform plugin select plugin_id=%s reason=match_license_app_key candidates=%s selected=%s",
                        plugin_id,
                        json.dumps(candidate_summaries, ensure_ascii=False, sort_keys=True),
                        json.dumps(self._plugin_debug_summary(item), ensure_ascii=False, sort_keys=True),
                    )
                    return item

        selected = candidates[0]
        logger.debug(
            "platform plugin select plugin_id=%s reason=first_candidate candidates=%s selected=%s",
            plugin_id,
            json.dumps(candidate_summaries, ensure_ascii=False, sort_keys=True),
            json.dumps(self._plugin_debug_summary(selected), ensure_ascii=False, sort_keys=True),
        )
        return selected

    def _resolve_installed_sku(self, installed_plugin: Any, region_app_id_map: Dict[str, Any], candidates: List[Any]) -> Optional[Any]:
        """根据已安装 RBDPlugin 的 region_app_id 反查安装时的 app_key, 从 market 候选里
        找到对应 SKU 记录, 用来锚定 latest_version 与 installed_arch.
        失败/拿不到时返回 None, 由上层退化为按集群 arch 选中的 SKU.
        """
        if not installed_plugin or not candidates:
            return None
        region_app_id = installed_plugin.get("region_app_id", "")
        console_app_id = region_app_id_map.get(region_app_id)
        if not console_app_id:
            return None
        try:
            cgroups = tenant_service_group_repo.get_group_by_app_id(console_app_id)
            if not cgroups:
                return None
            installed_app_key = cgroups.last().group_key  # type: ignore[union-attr]  # NOTE: .last() returns None when QuerySet empty, but guarded by `if not cgroups` above; Django ORM returns None for empty QS.last()
        except Exception as e:
            logger.warning("resolve installed SKU failed app_id=%s: %s", console_app_id, e)
            return None
        if not installed_app_key:
            return None
        for c in candidates:
            ak = c.get("appKeyID") or c.get("app_key")
            if ak == installed_app_key:
                return c
        return None

    def _build_plugin_info(self, plugin_id: str, selected: Any, display_sku: Any, installed_sku: Optional[Any],
                           installed_plugins: Dict[str, Any], region_app_id_map: Dict[str, Any],
                           candidates: List[Any]) -> Dict[str, Any]:
        """构造单条 plugin 返回 dict. display_sku 决定 latest_version 等版本类字段,
        selected 决定 app_level/路由/前端组件等运行时字段.
        """
        app_level = self._normalize_app_level(selected)
        plugin_info = {
            "plugin_id": plugin_id,
            "app_key": display_sku.get("appKeyID") or display_sku.get("app_key", ""),
            "plugin_name": display_sku.get("plugin_name") or plugin_id,
            "name": display_sku.get("name") or plugin_id,
            "description": display_sku.get("description", ""),
            "logo": display_sku.get("logo", ""),
            "app_level": app_level,
            "latest_version": display_sku.get("latest_version", ""),
            "plugin_type": display_sku.get("plugin_type", ""),
            "plugin_views": display_sku.get("plugin_views", []),
            "frontend_component": display_sku.get("frontend_component", ""),
            "entry_path": display_sku.get("entry_path", ""),
            "menu_title": display_sku.get("menu_title", ""),
            "route_path": display_sku.get("route_path", ""),
            "installed": False,
            "status": "",
            "installed_version": "",
            "upgradeable": False,
            "can_upgrade": False,
            "team_name": "",
            "app_id": -1,
            "author": "Rainbond 官方",
            "selected_arch": self._get_plugin_arch(selected),
            "installed_arch": self._get_plugin_arch(installed_sku) if installed_sku else None,
            "available_arches": sorted({self._get_plugin_arch(c) for c in candidates}),
        }
        if plugin_id in installed_plugins:
            plugin_info["installed"] = True
            installed_plugin = installed_plugins[plugin_id]
            plugin_info["status"] = installed_plugin.get("status", "")
            plugin_info["team_name"] = installed_plugin.get("team_name", "")
            region_app_id = installed_plugin.get("region_app_id", "")
            console_app_id = region_app_id_map.get(region_app_id, -1)
            plugin_info["app_id"] = console_app_id
            plugin_info["plugin_type"] = installed_plugin.get("plugin_type", plugin_info["plugin_type"])
            plugin_info["plugin_views"] = installed_plugin.get("plugin_views", plugin_info["plugin_views"])
            if console_app_id > 0:
                cgroups = tenant_service_group_repo.get_group_by_app_id(console_app_id)
                if cgroups:
                    plugin_info["installed_version"] = cgroups.last().group_version or ""  # type: ignore[union-attr]  # NOTE: .last() may return None when QuerySet is empty, but guarded by `if cgroups` above
            # installed_sku 为 None = 当前安装的 app 跟列表里选中的 market SKU 不是同一份
            # (例如本地 import 的 app model 跟市场上同名 plugin_id 的 SKU), 跨源比对版本会
            # 假阳性报"可升级", 而升级页按 service_source.group_key 拉本地版本会"暂无新版本"
            # 形成 UI 矛盾. 这里显式锁住: 跨源时强制不报可升级, latest 等同于 installed.
            if not installed_sku:
                plugin_info["latest_version"] = plugin_info["installed_version"]
                plugin_info["upgradeable"] = False
                plugin_info["can_upgrade"] = False
            elif plugin_info["latest_version"] and plugin_info["installed_version"]:
                plugin_info["upgradeable"] = plugin_info["latest_version"] != plugin_info["installed_version"]
                plugin_info["can_upgrade"] = plugin_info["upgradeable"]
        return plugin_info

    def list_platform_plugins(self, enterprise_id: str, region_name: str) -> List[Dict[str, Any]]:
        """
        List platform plugins from app store.

        Rules:
        - 按集群节点支持的 arch 过滤候选 (混合架构集群保留所有匹配 arch 的候选, AMD 优先选中)
        - 未授权前: 展示应用市场中的全部平台插件
        - 已授权后: 只展示免费插件 + 已授权企业插件
        - 已安装插件的 latest_version 锚定到"安装时的物理 SKU", 避免跨架构误报可升级
        """
        if is_cloud_market_disabled():
            logger.debug(
                "platform plugin list skipped because cloud market is disabled enterprise_id=%s region_name=%s",
                enterprise_id,
                region_name,
            )
            return []
        bean = self._get_license_bean(enterprise_id, region_name)
        plugin_mapping = bean.get("plugin_mapping", {}) or {}
        has_valid_license = bool(bean.get("valid"))
        installed_plugins = self._get_installed_plugins(enterprise_id, region_name)
        region_app_id_map = self._get_region_app_id_map(region_name, installed_plugins)
        region_arches = self._get_region_arches(region_name)
        try:
            _, market_plugins = self._get_market_platform_plugins_cached(enterprise_id)
        except Exception as e:
            logger.warning("Failed to get market platform plugins: %s", e)
            market_plugins = []

        logger.debug(
            "platform plugin list source summary enterprise_id=%s region_name=%s "
            "license_valid=%s mapping_keys=%s market_plugin_count=%s region_arches=%s",
            enterprise_id,
            region_name,
            has_valid_license,
            list(plugin_mapping.keys()),
            len(market_plugins),
            sorted(region_arches),
        )

        # 按 plugin_id 分组所有 market SKU
        grouped: Dict[str, List[Any]] = {}
        for mp in market_plugins:
            pid = mp.get("plugin_id", "")
            if pid:
                grouped.setdefault(pid, []).append(mp)

        result = []
        for plugin_id, candidates in grouped.items():
            # 1. 按集群 arch 过滤候选
            arch_matched = [c for c in candidates if self._get_plugin_arch(c) in region_arches]
            if not arch_matched:
                logger.debug(
                    "platform plugin filtered by arch enterprise_id=%s region_name=%s "
                    "plugin_id=%s region_arches=%s candidate_arches=%s",
                    enterprise_id, region_name, plugin_id,
                    sorted(region_arches),
                    sorted({self._get_plugin_arch(c) for c in candidates}),
                )
                continue

            # 2. 混合架构集群 tie-breaker: AMD 优先 (保持老用户体验稳定)
            arch_matched = sorted(
                arch_matched,
                key=lambda c: 0 if self._get_plugin_arch(c) == DEFAULT_ARCH else 1,
            )

            # 3. 在 arch 匹配的候选里按 free → license app_key → first 选
            selected = self._select_market_plugin(arch_matched, plugin_id, plugin_mapping)
            if not selected:
                continue

            # 4. license 过滤 (按 plugin_id 基名)
            app_level = self._normalize_app_level(selected)
            if has_valid_license and app_level != "free" and not self._is_plugin_authorized(
                    plugin_mapping, plugin_id):
                logger.debug(
                    "platform plugin filtered by license enterprise_id=%s region_name=%s "
                    "plugin_id=%s app_level=%s mapping_keys=%s",
                    enterprise_id, region_name, plugin_id, app_level,
                    list(plugin_mapping.keys()),
                )
                continue

            # 5. installed SKU 锚定 latest_version
            installed_sku = None
            if plugin_id in installed_plugins:
                installed_sku = self._resolve_installed_sku(
                    installed_plugins[plugin_id], region_app_id_map, candidates)
            display_sku = installed_sku or selected

            plugin_info = self._build_plugin_info(
                plugin_id=plugin_id,
                selected=selected,
                display_sku=display_sku,
                installed_sku=installed_sku,
                installed_plugins=installed_plugins,
                region_app_id_map=region_app_id_map,
                candidates=candidates,
            )
            result.append(plugin_info)

        logger.debug(
            "platform plugin list result summary enterprise_id=%s region_name=%s result_count=%s result_plugins=%s",
            enterprise_id,
            region_name,
            len(result),
            [item.get("plugin_id", "") for item in result],
        )
        return result

    def install_platform_plugin(self, enterprise_id: str, region_name: str, plugin_id: str, user: Any) -> Dict[str, Any]:
        """
        Install a platform plugin: auto-create team/app, fetch from market, install.

        - 候选先按集群 arch 过滤, 避免 ARM 集群装 AMD 模板时被 region 端 arch 校验拒掉
        - 在 arch 匹配候选中按 free → license app_key → first 选物理 SKU
        """
        bean = self._get_license_bean(enterprise_id, region_name)
        plugin_mapping = bean.get("plugin_mapping", {}) or {}
        plugin_names = bean.get("plugin_names", {}) or {}
        license_access_key = bean.get("access_key", "")

        platform_market, market_plugins = self._get_market_platform_plugins(enterprise_id)
        region_arches = self._get_region_arches(region_name)
        candidates_all = [mp for mp in market_plugins if mp.get("plugin_id") == plugin_id]
        candidates = [c for c in candidates_all if self._get_plugin_arch(c) in region_arches]
        # 混合架构集群 tie-breaker: AMD 优先 (与 list 接口保持一致)
        candidates = sorted(
            candidates,
            key=lambda c: 0 if self._get_plugin_arch(c) == DEFAULT_ARCH else 1,
        )
        logger.info(
            "platform plugin install request enterprise_id=%s region_name=%s plugin_id=%s "
            "license_valid=%s mapping_keys=%s region_arches=%s arch_matched=%s/%s",
            enterprise_id, region_name, plugin_id,
            bool(bean.get("valid")), list(plugin_mapping.keys()),
            sorted(region_arches), len(candidates), len(candidates_all),
        )
        logger.info(
            "platform plugin install market candidates plugin_id=%s candidates=%s",
            plugin_id,
            json.dumps(
                [self._plugin_debug_summary(item) for item in candidates],
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        if candidates_all and not candidates:
            raise ServiceHandleException(
                msg="no arch-matched plugin",
                msg_show="当前集群架构({})没有匹配的{}版本".format(
                    ",".join(sorted(region_arches)), plugin_id),
                status_code=404,
            )
        market_plugin = self._select_market_plugin(candidates, plugin_id, plugin_mapping)
        if not market_plugin:
            raise ServiceHandleException(msg="plugin not found", msg_show="应用市场中未找到该插件", status_code=404)

        app_level = self._normalize_app_level(market_plugin)
        plugin_name = market_plugin.get("plugin_name") or plugin_names.get(plugin_id, plugin_id)
        logger.info(
            "platform plugin install selected plugin plugin_id=%s selected=%s",
            plugin_id,
            json.dumps(self._plugin_debug_summary(market_plugin), ensure_ascii=False, sort_keys=True),
        )

        if app_level == "free":
            market = platform_market
            app_key = market_plugin.get("appKeyID") or market_plugin.get("app_key")
            logger.info(
                "platform plugin install resolved as free plugin plugin_id=%s app_key=%s latest_version=%s",
                plugin_id,
                app_key,
                market_plugin.get("latest_version", ""),
            )
        else:
            authorized_app_key = self._resolve_plugin_mapping_app_key(plugin_mapping, plugin_id)
            if not authorized_app_key:
                logger.warning(
                    "platform plugin install unauthorized enterprise plugin plugin_id=%s selected=%s mapping_keys=%s",
                    plugin_id,
                    json.dumps(self._plugin_debug_summary(market_plugin), ensure_ascii=False, sort_keys=True),
                    list(plugin_mapping.keys()),
                )
                raise ServiceHandleException(msg="plugin not authorized", msg_show="该插件未授权")
            if not license_access_key:
                raise ServiceHandleException(msg="no access_key in license", msg_show="授权信息中缺少 access_key")
            app_key = authorized_app_key
            market = AppMarket(
                name=PLATFORM_PLUGIN_MARKET_NAME,
                url=MARKET_HOST,
                domain=MARKET_DOMAIN,
                access_key=license_access_key,
            )
            logger.info(
                "platform plugin install resolved as enterprise plugin plugin_id=%s app_key=%s latest_version=%s",
                plugin_id,
                app_key,
                market_plugin.get("latest_version", ""),
            )

        latest_version = market_plugin.get("latest_version", "")
        if not latest_version:
            versions_data = app_store.get_app_versions(market, app_key)
            if not versions_data or not versions_data.versions:
                raise ServiceHandleException(msg="no versions found", msg_show="应用市场中未找到该插件的版本")
            latest_version = versions_data.versions[0].app_version

        # 4. Find or create the "rbd-plugins" team
        tenant = self._ensure_plugin_team(enterprise_id, region_name, user)

        # 5. Find or create app group for this plugin
        region = region_repo.get_enterprise_region_by_region_name(enterprise_id, region_name)
        if not region:
            raise ServiceHandleException(msg="region not found", msg_show="集群不存在")
        app = self._ensure_plugin_app(tenant, region_name, plugin_name, enterprise_id, plugin_id)

        # 6. Get app template from market
        market_app, app_version = app_market_service.cloud_app_model_to_db_model(
            market, app_key, latest_version, for_install=True)
        if not app_version:
            raise ServiceHandleException(msg="app version not found", msg_show="未找到插件版本模板")

        app_template = json.loads(app_version.app_template)
        app_template["update_time"] = app_version.update_time
        app_template["arch"] = app_version.arch

        # 7. Create component group and install
        component_group = market_app_service._create_tenant_service_group(
            region_name, tenant.tenant_id, app.ID, market_app.app_id,  # type: ignore[union-attr, arg-type]  # NOTE: app is Optional[ServiceGroup]; _ensure_plugin_app only returns None when get_group_by_id returns None (pk lookup, should not happen post-create); app.ID is int but _create_tenant_service_group expects str (pre-existing callers pass int)
            latest_version, market_app.app_name)

        app_upgrade = AppUpgrade(
            enterprise_id, tenant, region, user, app,  # type: ignore[arg-type]  # NOTE: app is Optional[ServiceGroup]; see above
            latest_version, component_group, app_template,
            True, PLATFORM_PLUGIN_MARKET_NAME, is_deploy=True)
        app_upgrade.install()

        # 8. Create RBDPlugin CR if template has platform_plugin info
        market_app_service._create_rbdplugin_if_needed(tenant, region, app_template, app.ID)  # type: ignore[union-attr, arg-type]  # NOTE: app is Optional[ServiceGroup]; _create_rbdplugin_if_needed expects str|None but app.ID is int (pre-existing int/str mismatch at call site)

        return {
            "plugin_id": plugin_id,
            "plugin_name": plugin_name,
            "version": latest_version,
            "team_name": tenant.tenant_name,
            "app_id": app.ID,  # type: ignore[union-attr]  # NOTE: app is Optional[ServiceGroup]; see above
        }

    def _ensure_plugin_team(self, enterprise_id: str, region_name: str, user: Any) -> Tenants:
        """Find or create the rbd-plugins team and ensure it's initialized on the region."""
        try:
            tenant = Tenants.objects.get(namespace=PLUGIN_TEAM_NAME, enterprise_id=enterprise_id)
        except Tenants.DoesNotExist:
            from www.models.main import TenantEnterprise
            enterprise = TenantEnterprise.objects.get(enterprise_id=enterprise_id)
            tenant = team_services.create_team(
                user, enterprise, team_alias=PLUGIN_TEAM_ALIAS, namespace=PLUGIN_TEAM_NAME)
        # Ensure tenant is initialized on the region
        region_services.create_tenant_on_region(enterprise_id, tenant.tenant_name, region_name, PLUGIN_TEAM_NAME)
        return tenant

    def _ensure_plugin_app(self, tenant: Tenants, region_name: str, plugin_name: str, eid: str, plugin_id: str) -> Optional[ServiceGroup]:
        """Find or create an app group for the plugin under the rbd-plugins team."""
        apps = group_repo.get_tenant_region_groups(tenant.tenant_id, region_name)
        for app in apps:
            if app.group_name == plugin_name:
                return app
        result = group_service.create_app(tenant, region_name, plugin_name, eid=eid, k8s_app=plugin_id)
        return group_repo.get_group_by_id(result["app_id"])


platform_plugin_service = PlatformPluginService()
