"""Application delivery objects. These models have no snapshot relationships."""
import uuid
from django.db import models


class DeliveryTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enterprise_id = models.CharField(max_length=64, db_index=True)
    team_name = models.CharField(max_length=64)
    region_name = models.CharField(max_length=64)
    app_id = models.CharField(max_length=64)
    name = models.CharField(max_length=64)
    app_name = models.CharField(max_length=128)
    logo = models.CharField(max_length=2048, blank=True, default="")
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "console"
        db_table = "delivery_template"
        constraints = [
            models.UniqueConstraint(fields=["enterprise_id", "team_name", "region_name", "app_id"],
                                    name="delivery_source_unique")
        ]


class DeliveryTemplateVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(DeliveryTemplate, on_delete=models.PROTECT, related_name="versions")
    version = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    manifest = models.JSONField()
    source_baseline = models.JSONField()
    digest = models.CharField(max_length=64)
    sync_id = models.UUIDField(unique=True, null=True)
    creation_key = models.CharField(max_length=128, unique=True, null=True)
    creator_id = models.IntegerField()
    creator_name = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True)
    deleted_by = models.CharField(max_length=128, blank=True)

    class Meta:
        app_label = "console"
        db_table = "delivery_template_version"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["template", "version"], name="delivery_version_unique")]


class DeliveryTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(DeliveryTemplate, on_delete=models.PROTECT, related_name="tasks")
    version = models.ForeignKey(DeliveryTemplateVersion, null=True, on_delete=models.PROTECT, related_name="tasks")
    kind = models.CharField(max_length=24)
    status = models.CharField(max_length=16, default="queued", db_index=True)
    actor_id = models.IntegerField()
    actor_name = models.CharField(max_length=128)
    request_key = models.CharField(max_length=128, unique=True)
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    error = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "console"
        db_table = "delivery_task"
        ordering = ["-created_at"]


class DeliveryTaskItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(DeliveryTask, on_delete=models.PROTECT, related_name="items")
    key = models.CharField(max_length=128)
    component = models.JSONField()
    status = models.CharField(max_length=16, default="queued")
    remote_id = models.CharField(max_length=128, blank=True)
    event_id = models.CharField(max_length=128, blank=True)
    result = models.JSONField(default=dict)
    error = models.CharField(max_length=256, blank=True)

    class Meta:
        app_label = "console"
        db_table = "delivery_task_item"
        constraints = [models.UniqueConstraint(fields=["task", "key"], name="delivery_task_item_unique")]


class DeliveryListingRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(DeliveryTemplateVersion, on_delete=models.PROTECT, related_name="listings")
    destination = models.JSONField(default=dict)
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=16, default="pending")
    publication_status = models.CharField(max_length=16, default="not_started")
    applicant_id = models.IntegerField()
    applicant_name = models.CharField(max_length=128)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewer_name = models.CharField(max_length=128, blank=True)
    comment = models.CharField(max_length=500, blank=True)
    reviewed_at = models.DateTimeField(null=True)
    publication_task = models.ForeignKey(DeliveryTask, null=True, on_delete=models.PROTECT)

    class Meta:
        app_label = "console"
        db_table = "delivery_listing_request"
        ordering = ["-submitted_at"]
