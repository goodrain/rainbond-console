# -*- coding: utf-8 -*-
"""Provision only the resolved AI backend with its existing Region-owned credential."""
import re
from typing import Any

from console.exception.main import ServiceHandleException
from console.repositories.app_config import env_var_repo
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.services.app_config import env_var_service
from www.apiclient.regionapi import RegionInvokeApi

PLATFORM_TOKEN_ENV = "AI_ENGINE_PLATFORM_TOKEN"
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
        if existing and existing.attr_value == value and existing.scope == "inner" and existing.is_change:
            return
        if backend.create_status == "complete":
            # Both bootstrap and credential writes verify the Region peer. The
            # generic env client may inherit legacy unverified TLS defaults.
            region_api.set_ai_engine_platform_env(enterprise_id,
                                                  region.region_name,
                                                  tenant.tenant_name,
                                                  backend.service_alias,
                                                  value,
                                                  create=not bool(existing))
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
    except Exception:
        # Upstream errors may echo request data. Do not leak this credential
        # through installation errors, chained exception tracebacks or results.
        raise _unavailable() from None
