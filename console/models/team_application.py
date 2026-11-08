"""Persistent team creation applications; audit data is never deleted with a team."""
import uuid
from django.db import models


class TeamApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enterprise_id = models.CharField(max_length=64, db_index=True)
    applicant_id = models.IntegerField(db_index=True)
    applicant_name = models.CharField(max_length=128)
    team_alias = models.CharField(max_length=64)
    namespace = models.CharField(max_length=33)
    namespace_claim = models.CharField(max_length=33, null=True, unique=True)
    alias_claim = models.CharField(max_length=64, null=True)
    regions = models.JSONField()
    region_labels = models.JSONField()
    quota = models.JSONField()
    reason = models.CharField(max_length=500)
    logo = models.CharField(max_length=2048, blank=True)
    previous_id = models.UUIDField(null=True, unique=True)
    status = models.CharField(max_length=16, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewer_id = models.IntegerField(null=True)
    reviewer_name = models.CharField(max_length=128, blank=True)
    reviewed_at = models.DateTimeField(null=True)
    comment = models.CharField(max_length=500, blank=True)
    team_id = models.CharField(max_length=33, blank=True)
    team_name = models.CharField(max_length=64, blank=True)
    regions_done = models.JSONField(default=list)
    provisioning_error = models.CharField(max_length=256, blank=True)

    class Meta:
        app_label = "console"
        db_table = "team_creation_application"
        ordering = ["-submitted_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["enterprise_id", "alias_claim"], name="team_app_pending_alias")]

    def public(self):
        return {name: getattr(self, name) for name in (
            "enterprise_id", "applicant_id", "applicant_name", "team_alias", "namespace", "regions", "region_labels",
            "quota", "reason", "logo", "status", "reviewer_name", "comment", "team_id", "team_name", "provisioning_error")
        } | {"id": str(self.id), "previous_id": str(self.previous_id) if self.previous_id else "",
             "submitted_at": self.submitted_at.isoformat(),
             "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else ""}
