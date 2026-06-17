# -*- coding: utf8 -*-
import logging
import os
import time
from typing import Any, Dict, List, Optional

from console.enum.enterprise_enum import EnterpriseRolesEnum
from console.exception.main import ServiceHandleException
from console.models.main import EnterpriseUserPerm
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.repositories.region_repo import region_repo
from console.services.user_services import user_services
from django.db import transaction
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Users

logger = logging.getLogger("default")

region_api = RegionInvokeApi()

ENTERPRISE_BASE_PLUGIN = "rainbond-enterprise-base"
EDITION_OPEN_SOURCE = "open_source"
EDITION_ENTERPRISE = "enterprise"
EDITION_SAAS = "saas"
EDITION_ENTERPRISE_SAAS = "enterprise_saas"

# Short in-process cache so the high-frequency agent access poll does not probe
# every cluster on every request. TTL is configurable for slow environments.
PLUGIN_CACHE_TTL = int(os.getenv("AGENT_ACCESS_PLUGIN_CACHE_TTL", "60"))


class AgentAccessService(object):
    def __init__(self) -> None:
        # enterprise_id -> (expire_ts, has_enterprise_base)
        self._enterprise_base_cache: Dict[str, Any] = {}

    def get_agent_access(self, user: Any) -> Dict[str, Any]:
        if not user:
            return self._build_access(False, EDITION_OPEN_SOURCE, False, False, False, "not_authenticated")

        enterprise_id = getattr(user, "enterprise_id", "")
        if not enterprise_id:
            return self._build_access(False, EDITION_OPEN_SOURCE, False, False, False, "enterprise_not_found")

        edition = self.get_platform_edition(enterprise_id)
        is_saas = edition in (EDITION_SAAS, EDITION_ENTERPRISE_SAAS)
        has_enterprise_base = edition in (EDITION_ENTERPRISE, EDITION_ENTERPRISE_SAAS)
        marker = self.ensure_initial_enterprise_admin_marker(enterprise_id)
        is_initial_admin = bool(marker and marker.user_id == user.user_id)

        if edition != EDITION_OPEN_SOURCE:
            return self._build_access(True, edition, is_saas, has_enterprise_base, is_initial_admin, "")

        is_enterprise_admin = enterprise_user_perm_repo.is_admin(enterprise_id, user.user_id)

        if is_enterprise_admin and is_initial_admin:
            return self._build_access(True, edition, is_saas, has_enterprise_base, True, "")

        deny_reason = "not_enterprise_admin"
        if is_enterprise_admin:
            deny_reason = "open_source_requires_enterprise"
        return self._build_access(False, edition, is_saas, has_enterprise_base, is_initial_admin, deny_reason)

    def get_platform_edition(self, enterprise_id: str) -> str:
        is_saas = bool(os.getenv("USE_SAAS"))
        has_enterprise_base = self.has_enterprise_base_plugin(enterprise_id)
        if is_saas and has_enterprise_base:
            return EDITION_ENTERPRISE_SAAS
        if is_saas:
            return EDITION_SAAS
        if has_enterprise_base:
            return EDITION_ENTERPRISE
        return EDITION_OPEN_SOURCE

    def has_enterprise_base_plugin(self, enterprise_id: str) -> bool:
        now = time.time()
        cached = self._enterprise_base_cache.get(enterprise_id)
        if cached and cached[0] > now:
            return cached[1]

        result = self._compute_has_enterprise_base_plugin(enterprise_id)
        self._enterprise_base_cache[enterprise_id] = (now + PLUGIN_CACHE_TTL, result)
        return result

    def _compute_has_enterprise_base_plugin(self, enterprise_id: str) -> bool:
        try:
            regions = region_repo.get_usable_regions(enterprise_id)
        except Exception as exc:
            logger.warning("failed to list usable regions for agent access: %s", exc)
            return False

        for region in regions or []:
            if self._region_has_enterprise_base(enterprise_id, region.region_name):
                return True
        return False

    def _region_has_enterprise_base(self, enterprise_id: str, region_name: str) -> bool:
        try:
            return region_api.cluster_plugin_exists(enterprise_id, region_name, ENTERPRISE_BASE_PLUGIN)
        except ServiceHandleException as exc:
            if exc.status_code == 404:
                # Older region without the probe endpoint: fall back to listing.
                return self._region_has_enterprise_base_fallback(enterprise_id, region_name)
            logger.warning("failed to probe enterprise base plugin: region=%s error=%s", region_name, exc)
            return False
        except Exception as exc:
            logger.warning("failed to probe enterprise base plugin: region=%s error=%s", region_name, exc)
            return False

    def _region_has_enterprise_base_fallback(self, enterprise_id: str, region_name: str) -> bool:
        try:
            _, body = region_api.list_plugins(enterprise_id, region_name, True)
        except Exception as exc:
            logger.warning("failed to list plugins for agent access: region=%s error=%s", region_name, exc)
            return False
        for plugin in (body or {}).get("list") or []:
            if plugin.get("name") == ENTERPRISE_BASE_PLUGIN:
                return True
        return False

    def get_initial_enterprise_admin_marker(self, enterprise_id: str) -> Optional[EnterpriseUserPerm]:
        return EnterpriseUserPerm.objects.filter(
            enterprise_id=enterprise_id,
            is_initial_enterprise_admin=True).first()

    def ensure_initial_enterprise_admin_marker(self, enterprise_id: str) -> Optional[EnterpriseUserPerm]:
        if not enterprise_id:
            return None

        with transaction.atomic():
            markers = list(
                EnterpriseUserPerm.objects.select_for_update().filter(
                    enterprise_id=enterprise_id,
                    is_initial_enterprise_admin=True))
            if markers:
                marker = self._normalize_markers(enterprise_id, markers)
                return marker

            target_perm = self._select_existing_admin_perm(enterprise_id)
            if not target_perm:
                first_user = Users.objects.filter(enterprise_id=enterprise_id).order_by("create_time", "user_id").first()
                if not first_user:
                    return None
                target_perm = self._ensure_admin_perm(first_user.user_id, enterprise_id)

            self._mark_initial_admin(enterprise_id, target_perm)
            return target_perm

    def _build_access(self, can_open_agent: bool, edition: str, is_saas: bool, has_enterprise_base: bool,
                      is_initial_admin: bool, deny_reason: str) -> Dict[str, Any]:
        return {
            "can_open_agent": can_open_agent,
            "edition": edition,
            "is_open_source": edition == EDITION_OPEN_SOURCE,
            "is_saas": is_saas,
            "has_enterprise_base": has_enterprise_base,
            "is_initial_enterprise_admin": is_initial_admin,
            "deny_reason": deny_reason,
        }

    def _normalize_markers(self, enterprise_id: str, markers: List[EnterpriseUserPerm]) -> EnterpriseUserPerm:
        user_ids = [marker.user_id for marker in markers]
        user_order = self._get_user_order(enterprise_id, user_ids)
        markers.sort(key=lambda marker: (user_order.get(marker.user_id, 999999999), marker.user_id))
        marker = markers[0]
        duplicate_ids = [item.ID for item in markers[1:]]
        if duplicate_ids:
            EnterpriseUserPerm.objects.filter(ID__in=duplicate_ids).update(is_initial_enterprise_admin=False)
        return marker

    def _select_existing_admin_perm(self, enterprise_id: str) -> Optional[EnterpriseUserPerm]:
        admin_perms = list(
            EnterpriseUserPerm.objects.select_for_update().filter(
                enterprise_id=enterprise_id,
                identity__contains=EnterpriseRolesEnum.admin.name))
        if not admin_perms:
            return None
        user_order = self._get_user_order(enterprise_id, [perm.user_id for perm in admin_perms])
        admin_perms.sort(key=lambda perm: (user_order.get(perm.user_id, 999999999), perm.user_id))
        return admin_perms[0]

    def _ensure_admin_perm(self, user_id: int, enterprise_id: str) -> EnterpriseUserPerm:
        perm = EnterpriseUserPerm.objects.select_for_update().filter(user_id=user_id, enterprise_id=enterprise_id).first()
        if perm:
            if EnterpriseRolesEnum.admin.name not in perm.identity:
                perm.identity = EnterpriseRolesEnum.admin.name
                perm.save(update_fields=["identity"])
            return perm
        token = user_services.generate_key()
        return enterprise_user_perm_repo.create_enterprise_user_perm(
            user_id, enterprise_id, EnterpriseRolesEnum.admin.name, token)  # type: ignore[arg-type]  # NOTE: repo stub declares user_id as str but callers pass int; mismatch pre-dates this annotation pass

    def _mark_initial_admin(self, enterprise_id: str, target_perm: EnterpriseUserPerm) -> None:
        EnterpriseUserPerm.objects.filter(enterprise_id=enterprise_id).exclude(ID=target_perm.ID).update(
            is_initial_enterprise_admin=False)
        if not target_perm.is_initial_enterprise_admin:
            target_perm.is_initial_enterprise_admin = True
            target_perm.save(update_fields=["is_initial_enterprise_admin"])

    def _get_user_order(self, enterprise_id: str, user_ids: List[int]) -> Dict[int, int]:
        if not user_ids:
            return {}
        users = Users.objects.filter(enterprise_id=enterprise_id, user_id__in=user_ids).order_by("create_time", "user_id")
        return {user.user_id: index for index, user in enumerate(users)}


agent_access_service = AgentAccessService()
