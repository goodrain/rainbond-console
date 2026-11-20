"""Independent delivery persistence, scoped by enterprise, team, region and app."""
from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING
from uuid import UUID
from django.db.models import QuerySet
from console.services.delivery_manifest import DeliveryError

if TYPE_CHECKING:
    from console.models.delivery_template import DeliveryTemplate, DeliveryTask, DeliveryTemplateVersion


class DeliveryRepository:
    def __init__(self, models: ModuleType | None = None) -> None:
        if models is None:
            from console.models import delivery_template
            self.models: ModuleType = delivery_template
        else:
            self.models = models

    def templates(self, scope: dict[str, str]) -> QuerySet[DeliveryTemplate]:
        return self.models.DeliveryTemplate.objects.filter(**scope)

    def task(self, scope: dict[str, str], task_id: str | UUID) -> DeliveryTask:
        row = self.models.DeliveryTask.objects.select_related("template", "version").filter(
            id=task_id, template__in=self.templates(scope)).first()
        if not row:
            raise DeliveryError("交付任务不存在", 404)
        return row

    def version(self, scope: dict[str, str], version_id: str | UUID, available: bool = True) -> DeliveryTemplateVersion:
        row = self.models.DeliveryTemplateVersion.objects.select_related("template").filter(
            id=version_id, template__in=self.templates(scope)).first()
        if not row or available and row.deleted_at:
            raise DeliveryError("模板版本不存在或已删除", 404)
        return row
