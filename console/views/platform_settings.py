# -*- coding: utf-8 -*-
from typing import Any, Tuple
from rest_framework.request import Request
from rest_framework.response import Response

from console.exception.exceptions import ConfigExistError
from console.services.config_service import EnterpriseConfigService
from console.views.base import EnterpriseAdminView, JWTAuthApiView
from www.utils.return_message import general_message
from www.models.main import TenantEnterprise
from console.models.main import ConsoleSysConfig

GLOBAL_IMAGE_REGISTRY_CONFIG_KEY = "GLOBAL_IMAGE_REGISTRY"


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return bool(value)


def _get_or_create_global_image_registry_config(eid: str) -> Tuple[EnterpriseConfigService, ConsoleSysConfig]:
    config_service = EnterpriseConfigService(eid, None)
    config = config_service.get_config_by_key(GLOBAL_IMAGE_REGISTRY_CONFIG_KEY)
    if not config:
        try:
            config = config_service.add_config(key=GLOBAL_IMAGE_REGISTRY_CONFIG_KEY,
                                               default_value=None,
                                               type="string",
                                               enable=False,
                                               desc="全局容器镜像仓库开关")
        except ConfigExistError:
            config = config_service.get_config_by_key(GLOBAL_IMAGE_REGISTRY_CONFIG_KEY)
            if not config:
                raise
    return config_service, config


class PlatformSettingsView(JWTAuthApiView):
    def get(self, request: Request, eid: str, *args: Any, **kwargs: Any) -> Response:
        try:
            enterprise = TenantEnterprise.objects.get(enterprise_id=eid)
        except TenantEnterprise.DoesNotExist:
            return Response(general_message(404, "not found", "企业不存在"), status=404)
        _, global_image_registry_config = _get_or_create_global_image_registry_config(eid)
        data = {
            "enable_team_resource_view": enterprise.enable_team_resource_view,
            "enable_global_image_registry": global_image_registry_config.enable,
        }
        return Response(general_message(200, "success", "获取成功", bean=data))


class PlatformSettingsUpdateView(EnterpriseAdminView):
    def put(self, request: Request, eid: str, *args: Any, **kwargs: Any) -> Response:
        try:
            enterprise = TenantEnterprise.objects.get(enterprise_id=eid)
        except TenantEnterprise.DoesNotExist:
            return Response(general_message(404, "not found", "企业不存在"), status=404)
        has_team_resource_view = "enable_team_resource_view" in request.data
        has_global_image_registry = "enable_global_image_registry" in request.data
        if not has_team_resource_view and not has_global_image_registry:
            return Response(general_message(400, "bad request",
                                            "缺少 enable_team_resource_view 或 enable_global_image_registry 参数"),
                            status=400)
        if has_team_resource_view:
            enterprise.enable_team_resource_view = _parse_bool(request.data.get("enable_team_resource_view"))
            enterprise.save(update_fields=["enable_team_resource_view"])
        if has_global_image_registry:
            config_service, _ = _get_or_create_global_image_registry_config(eid)
            config_service.update_config_enable_status(key=GLOBAL_IMAGE_REGISTRY_CONFIG_KEY,
                                                       enable=_parse_bool(request.data.get("enable_global_image_registry")))
        return Response(general_message(200, "success", "更新成功"))
