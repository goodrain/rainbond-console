"""Read delivery versions through the existing application upgrade workflow, without publishing them."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID

from console.repositories.delivery_template_repo import DeliveryRepository
from console.services.delivery_manifest import DeliveryError


class DeliveryUpgradeSource:
    def __init__(self, models: Any = None, gateway: Any = None) -> None:
        self.models, self.gateway = models, gateway

    def template(self, enterprise_id: str, key: str) -> Any:
        try:
            identifier = UUID(str(key))
        except (ValueError, TypeError):
            return None
        return DeliveryRepository(self.models).models.DeliveryTemplate.objects.filter(
            id=identifier, enterprise_id=enterprise_id).first()

    def model(self, enterprise_id: str, key: str) -> Any:
        template = self.template(enterprise_id, key)
        if not template:
            return None
        return SimpleNamespace(app_name=template.name, app_id=template.id.hex,
                               create_user=None, create_team=template.team_name,
                               pic=template.logo, source="local", describe=template.description,
                               is_official=False, details=template.details, is_delivery_source=True)

    def _versions(self, template: Any, team_name: str | None) -> Any:
        versions = template.versions.filter(deleted_at__isnull=True)
        if team_name != template.team_name:
            published = DeliveryRepository(self.models).models.DeliveryListingRequest.objects.filter(
                version__template=template, publication_status="published", destination__type="local")
            versions = versions.filter(pk__in=published.values_list("version_id", flat=True))
        return versions.order_by("-created_at")

    def version_options(self, enterprise_id: str, key: str, team_name: str | None) -> list[Any] | None:
        template = self.template(enterprise_id, key)
        if not template:
            return None
        if not team_name:
            return []
        return [SimpleNamespace(version=row.version, update_time=row.created_at)
                for row in self._versions(template, team_name)]

    def manifest(self, enterprise_id: str, key: str, version: str, team_name: str | None) -> dict | None:
        template = self.template(enterprise_id, key)
        if not template:
            return None
        row = self._versions(template, team_name).filter(version=version).first() if team_name else None
        if not row:
            raise DeliveryError("此模板版本已删除或不可用于目标团队升级", 403)
        published = None
        if team_name != template.team_name:
            listing = row.listings.filter(publication_status="published", destination__type="local").select_related(
                "publication_task").first()
            published = listing.publication_task.result.get("published_manifest") if listing.publication_task else None
            if not published:
                raise DeliveryError("模板同步尚未完成，暂不能升级", 409)
        gateway = self.gateway
        if gateway is None:
            from console.services.delivery_gateway import DeliveryGateway
            gateway = DeliveryGateway()
        return gateway.upgrade_manifest(row, published)


def target_team_name(enterprise_id: str, tenant_id: str) -> str | None:
    from www.models.main import Tenants
    tenant = Tenants.objects.filter(tenant_id=tenant_id, enterprise_id=enterprise_id).first()
    return tenant.tenant_name if tenant else None


delivery_upgrade_source = DeliveryUpgradeSource()
