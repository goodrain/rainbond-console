# -*- coding: utf-8 -*-
"""Provision the current AI application with platform and dedicated monitoring credentials."""
import re
import secrets
from typing import Any

from django.db import transaction

from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig
from console.repositories.app_config import env_var_repo
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.services.app_config import env_var_service
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroupRelation, TenantServiceInfo

PLATFORM_TOKEN_ENV = "AI_ENGINE_PLATFORM_TOKEN"
MONITORING_TOKEN_ENV = "AI_ENGINE_MONITORING_TOKEN"
region_api = RegionInvokeApi()


def _unavailable() -> ServiceHandleException:
    return ServiceHandleException(
        msg="AI Engine platform credential unavailable",
        msg_show="AI 插件平台凭据未就绪，请检查平台团队归属和集群通信配置",
        status_code=503,
    )


def configure_installation(tenant: Any, region: Any, backend: Any) -> None:
    """Configure only an administrator-owned platform team's resolved backend.

    Installation/upgrade invokes this before normal deployment. Reconciliation
    alone saves desired configuration; it never restarts an existing component.
    """
    try:
        enterprise_id = getattr(tenant, "enterprise_id", None)
        owner_id = getattr(tenant, "creater", None)
        if (not enterprise_id or owner_id is None or getattr(tenant, "namespace", None) != "rbd-plugins"
                or getattr(region, "enterprise_id", None) != enterprise_id
                or getattr(backend, "tenant_id", None) != getattr(tenant, "tenant_id", None)
                or getattr(backend, "service_region", None) != getattr(region, "region_name", None)
                or not enterprise_user_perm_repo.is_admin(enterprise_id, owner_id)):
            raise _unavailable()
        value = region_api.bootstrap_ai_engine_platform_token(enterprise_id, region.region_name)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise _unavailable()
        existing = env_var_service.get_env_by_attr_name(tenant, backend, PLATFORM_TOKEN_ENV)
        if backend.create_status == "complete":
            # Both bootstrap and credential writes verify the Region peer. The
            # generic env client may inherit legacy unverified TLS defaults.
            # Console state alone cannot prove the Region env is still present.
            region_api.set_ai_engine_platform_env(enterprise_id,
                                                  region.region_name,
                                                  tenant.tenant_name,
                                                  backend.service_alias,
                                                  value,
                                                  create=True)
        if existing and existing.attr_value == value and existing.scope == "inner" and existing.is_change:
            configure_monitoring_installation(tenant, region, backend)
            return
        if existing:
            env_var_repo.update_env_var(tenant.tenant_id,
                                        backend.service_id,
                                        PLATFORM_TOKEN_ENV,
                                        attr_value=value,
                                        is_change=True,
                                        scope="inner")
        else:
            env_var_repo.add_service_env(tenant_id=tenant.tenant_id,
                                         service_id=backend.service_id,
                                         container_port=0,
                                         name=PLATFORM_TOKEN_ENV,
                                         attr_name=PLATFORM_TOKEN_ENV,
                                         attr_value=value,
                                         is_change=True,
                                         scope="inner")
        configure_monitoring_installation(tenant, region, backend)
    except Exception:
        # Upstream errors may echo request data. Do not leak this credential
        # through installation errors, chained exception tracebacks or results.
        raise _unavailable() from None


def _component_role(component: Any) -> str:
    if getattr(component, "service_source", None) in ("vm_run", "third_party"):
        return ""
    return getattr(component, "k8s_component_name", "") or getattr(component, "service_cname", "")


def _monitoring_pair(tenant: Any, region: Any, component: Any):
    enterprise_id = getattr(tenant, "enterprise_id", None)
    if (not enterprise_id or getattr(tenant, "creater", None) is None or tenant.namespace != "rbd-plugins"
            or region.enterprise_id != enterprise_id or component.tenant_id != tenant.tenant_id
            or component.service_region != region.region_name
            or not enterprise_user_perm_repo.is_admin(enterprise_id, tenant.creater)):
        raise _unavailable()
    memberships = list(ServiceGroupRelation.objects.filter(service_id=component.service_id))
    if (len(memberships) != 1 or memberships[0].tenant_id != tenant.tenant_id
            or memberships[0].region_name != region.region_name):
        raise _unavailable()
    relations = list(ServiceGroupRelation.objects.filter(group_id=memberships[0].group_id))
    if any(item.tenant_id != tenant.tenant_id or item.region_name != region.region_name for item in relations):
        raise _unavailable()
    components = list(TenantServiceInfo.objects.filter(service_id__in=[item.service_id for item in relations]))
    roles = {}
    for candidate in components:
        role = _component_role(candidate)
        if role not in ("ai-engine", "ai-engine-prometheus"):
            continue
        if (candidate.tenant_id != tenant.tenant_id or candidate.service_region != region.region_name or role in roles):
            raise _unavailable()
        candidate_memberships = list(ServiceGroupRelation.objects.filter(service_id=candidate.service_id))
        if len(candidate_memberships) != 1 or candidate_memberships[0].group_id != memberships[0].group_id:
            raise _unavailable()
        roles[role] = candidate
    if set(roles) != {"ai-engine", "ai-engine-prometheus"}:
        raise _unavailable()
    return roles["ai-engine"], roles["ai-engine-prometheus"]


def _valid_monitoring_token(value: Any) -> bool:
    return isinstance(value, str) and 32 <= len(value) <= 4096 and all(33 <= ord(char) <= 126 for char in value)


def _allocate_monitoring_token(tenant: Any, pair):
    # Lock existing component rows, since legacy env rows have no unique key.
    # This transaction ends before any Region request is made.
    with transaction.atomic():
        locked = list(TenantServiceInfo.objects.select_for_update().filter(
            tenant_id=tenant.tenant_id, service_id__in=[item.service_id for item in pair]).order_by("service_id"))
        if len(locked) != 2:
            raise _unavailable()
        existing = [env_var_service.get_env_by_attr_name(tenant, item, MONITORING_TOKEN_ENV) for item in pair]
        for item in existing:
            if item and not _valid_monitoring_token(item.attr_value):
                raise _unavailable()
        if existing[0] and existing[1] and existing[0].attr_value != existing[1].attr_value:
            # A normal backend update must not invalidate a running Prometheus.
            raise _unavailable()
        value = next((item.attr_value for item in existing if item), None) or secrets.token_hex(32)
        for component, current in zip(pair, existing):
            if current:
                env_var_repo.update_env_var(tenant.tenant_id,
                                            component.service_id,
                                            MONITORING_TOKEN_ENV,
                                            attr_value=value,
                                            is_change=True,
                                            scope="inner")
            else:
                env_var_repo.add_service_env(tenant_id=tenant.tenant_id,
                                             service_id=component.service_id,
                                             container_port=0,
                                             name=MONITORING_TOKEN_ENV,
                                             attr_name=MONITORING_TOKEN_ENV,
                                             attr_value=value,
                                             is_change=True,
                                             scope="inner")
    return value, existing


def configure_monitoring_installation(tenant: Any, region: Any, component: Any) -> None:
    """Pair the backend and its dedicated Prometheus without rotating existing credentials."""
    try:
        pair = _monitoring_pair(tenant, region, component)
        value, _ = _allocate_monitoring_token(tenant, pair)
        for target in pair:
            if target.create_status == "complete":
                # Always reconcile: an earlier write can fail after local persistence.
                region_api.set_ai_engine_monitoring_env(tenant.enterprise_id,
                                                        region.region_name,
                                                        tenant.tenant_name,
                                                        target.service_alias,
                                                        value,
                                                        create=True)
    except Exception:
        raise _unavailable() from None


def prepare_component_credentials(tenant: Any, components: Any) -> None:
    """Only lifecycle operations call this; ordinary queries never provision secrets."""
    if getattr(tenant, "namespace", None) != "rbd-plugins":
        return
    prepared = set()
    for component in components:
        if _component_role(component) not in ("ai-engine", "ai-engine-prometheus"):
            continue
        try:
            region = RegionConfig.objects.get(region_name=component.service_region, enterprise_id=tenant.enterprise_id)
            pair = _monitoring_pair(tenant, region, component)
            backend = pair[0]
            if backend.service_id in prepared:
                continue
            configure_installation(tenant, region, backend)
            prepared.add(backend.service_id)
        except Exception:
            raise _unavailable() from None
