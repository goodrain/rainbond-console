"""Independent delivery persistence, scoped by enterprise, team, region and app."""
from console.services.delivery_manifest import DeliveryError


class DeliveryRepository:
    def __init__(self, models=None):
        if models is None:
            from console.models import delivery_template as models
        self.models = models

    def templates(self, scope):
        return self.models.DeliveryTemplate.objects.filter(**scope)

    def task(self, scope, task_id):
        row = self.models.DeliveryTask.objects.select_related("template", "version").filter(
            id=task_id, template__in=self.templates(scope)).first()
        if not row:
            raise DeliveryError("交付任务不存在", 404)
        return row

    def version(self, scope, version_id, available=True):
        row = self.models.DeliveryTemplateVersion.objects.select_related("template").filter(
            id=version_id, template__in=self.templates(scope)).first()
        if not row or available and row.deleted_at:
            raise DeliveryError("模板版本不存在或已删除", 404)
        return row
