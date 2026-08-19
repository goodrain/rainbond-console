# -*- coding: utf-8 -*-
import uuid
from datetime import datetime, timedelta, timezone as datetime_timezone
from typing import Any, Dict, List, Optional, Tuple

from django.db import IntegrityError, transaction
from django.utils import timezone

from console.models.main import (
    RainSkillsOperation,
    RainSkillsOperationEvent,
    RainSkillsSkillSnapshot,
)


ASIA_SHANGHAI_TIMEZONE = datetime_timezone(timedelta(hours=8))


def _asia_shanghai_isoformat(value: datetime) -> str:
    """Serialize Console-local datetimes as unambiguous RFC 3339 timestamps."""
    if timezone.is_naive(value):
        value = value.replace(tzinfo=ASIA_SHANGHAI_TIMEZONE)
    else:
        value = value.astimezone(ASIA_SHANGHAI_TIMEZONE)
    return value.isoformat()


class RainSkillsAuditRepository(object):

    @staticmethod
    def get_operation(enterprise_id: str, operation_id: str) -> Optional[RainSkillsOperation]:
        return RainSkillsOperation.objects.select_related("skill_snapshot").filter(
            enterprise_id=enterprise_id,
            operation_id=operation_id,
        ).first()

    def get_or_create_snapshot(self, enterprise_id: str,
                               skill: Dict[str, Any]) -> Tuple[RainSkillsSkillSnapshot, bool]:
        lookup = {
            "enterprise_id": enterprise_id,
            "skill_id": skill["id"],
            "profile": skill["profile"],
            "content_sha256": skill["content_sha256"],
        }
        defaults = {
            "package_version": skill["package_version"],
            "source_revision": skill.get("source_revision"),
            "bundle_sha256": skill.get("bundle_sha256"),
            "content_text": skill["content"],
            "provenance": "client_manifest_verified",
        }
        try:
            with transaction.atomic():
                return RainSkillsSkillSnapshot.objects.get_or_create(defaults=defaults, **lookup)
        except IntegrityError:
            return RainSkillsSkillSnapshot.objects.get(**lookup), False

    def begin_operation(self, **values: Any) -> Tuple[RainSkillsOperation, bool]:
        enterprise_id = values["enterprise_id"]
        operation_id = values["operation_id"]
        snapshot = values.pop("snapshot", None)
        with transaction.atomic():
            existing = RainSkillsOperation.objects.select_for_update().filter(
                enterprise_id=enterprise_id,
                operation_id=operation_id,
            ).first()
            if existing is not None:
                return existing, False

            operation = RainSkillsOperation.objects.create(
                started_at=timezone.now(),
                status="executing",
                skill_snapshot=snapshot,
                **values
            )
            self._create_event(operation, "operation_started")
            return operation, True

    def finalize_operation(self, operation: RainSkillsOperation, status: str,
                           output_summary: Optional[str] = None,
                           error_code: Optional[str] = None,
                           error_message: Optional[str] = None) -> RainSkillsOperation:
        if status not in ("succeeded", "failed", "unknown"):
            raise ValueError("invalid terminal RainSkills operation status")
        with transaction.atomic():
            locked = RainSkillsOperation.objects.select_for_update().get(pk=operation.pk)
            if locked.status != "executing":
                return locked
            locked.status = status
            locked.output_summary = output_summary
            locked.error_code = error_code
            locked.error_message = error_message
            locked.finished_at = timezone.now()
            locked.save(update_fields=(
                "status",
                "output_summary",
                "error_code",
                "error_message",
                "finished_at",
                "updated_at",
            ))
            self._create_event(locked, "operation_{}".format(status))
            return locked

    @staticmethod
    def binding_matches(operation: RainSkillsOperation, tool_name: str,
                        arguments_digest: str, skill_id: Optional[str],
                        skill_digest: Optional[str]) -> bool:
        snapshot = operation.skill_snapshot
        stored_skill_digest = snapshot.content_sha256 if snapshot is not None else None
        return (
            operation.tool_name == tool_name
            and operation.arguments_digest == arguments_digest
            and operation.skill_id == skill_id
            and stored_skill_digest == skill_digest
        )

    @staticmethod
    def list_events(enterprise_id: str, after_cursor: int,
                    limit: int) -> List[RainSkillsOperationEvent]:
        return list(RainSkillsOperationEvent.objects.filter(
            enterprise_id=enterprise_id,
            id__gt=after_cursor,
        ).order_by("id")[:limit])

    @staticmethod
    def latest_event_cursor(enterprise_id: str) -> int:
        latest = RainSkillsOperationEvent.objects.filter(
            enterprise_id=enterprise_id).order_by("-id").values_list("id", flat=True).first()
        return int(latest or 0)

    def materialize_stale_unknown(self, enterprise_id: str, stale_before: datetime,
                                  limit: int = 100) -> int:
        operation_ids = list(RainSkillsOperation.objects.filter(
            enterprise_id=enterprise_id,
            status="executing",
            started_at__lt=stale_before,
        ).order_by("id").values_list("id", flat=True)[:limit])
        materialized = 0
        for operation_id in operation_ids:
            operation = RainSkillsOperation.objects.get(pk=operation_id)
            terminal = self.finalize_operation(
                operation,
                status="unknown",
                error_code="audit_terminal_missing",
                error_message="Tool terminal audit was not persisted; verify the resource state manually",
            )
            if terminal.status == "unknown":
                materialized += 1
        return materialized

    @staticmethod
    def get_snapshot(enterprise_id: str, skill_id: str, profile: str,
                     content_sha256: str) -> Optional[RainSkillsSkillSnapshot]:
        return RainSkillsSkillSnapshot.objects.filter(
            enterprise_id=enterprise_id,
            skill_id=skill_id,
            profile=profile,
            content_sha256=content_sha256,
        ).first()

    @staticmethod
    def _create_event(operation: RainSkillsOperation,
                      event_type: str) -> RainSkillsOperationEvent:
        event_id = "rs_evt_{}".format(uuid.uuid4().hex)
        occurred_at = timezone.now()
        snapshot = operation.skill_snapshot if operation.skill_snapshot_id else None
        skill = None
        if snapshot is not None:
            skill = {
                "id": snapshot.skill_id,
                "root_skill_id": operation.root_skill_id,
                "profile": snapshot.profile,
                "package_version": snapshot.package_version,
                "source_revision": snapshot.source_revision,
                "content_sha256": snapshot.content_sha256,
                "bundle_sha256": snapshot.bundle_sha256,
                "provenance": snapshot.provenance,
            }
        payload = {
            "schema": "rainskills.operation.v1",
            "event_id": event_id,
            "event_type": event_type,
            "occurred_at": _asia_shanghai_isoformat(occurred_at),
            "operation": {
                "operation_id": operation.operation_id,
                "enterprise_id": operation.enterprise_id,
                "user_id": operation.user_id,
                "username": operation.username,
                "deploy_client": operation.deploy_client,
                "tool_name": operation.tool_name,
                "operation_class": operation.operation_class,
                "risk": operation.risk,
                "scope": operation.scope,
                "arguments_digest": operation.arguments_digest,
                "target_context": operation.target_context,
                "operation_descriptor": (
                    operation.target_context.get("operation_descriptor")
                    if isinstance(operation.target_context, dict) else None
                ),
                "input_json": operation.input_json,
                "confirmation_type": operation.confirmation_type,
                "status": operation.status,
                "output_summary": operation.output_summary,
                "error_code": operation.error_code,
                "error_message": operation.error_message,
                "started_at": _asia_shanghai_isoformat(operation.started_at),
                "finished_at": (
                    _asia_shanghai_isoformat(operation.finished_at)
                    if operation.finished_at else None
                ),
            },
            "skill": skill,
        }
        return RainSkillsOperationEvent.objects.create(
            event_id=event_id,
            enterprise_id=operation.enterprise_id,
            operation_id=operation.operation_id,
            event_type=event_type,
            payload=payload,
            created_at=occurred_at,
        )


rainskills_audit_repo = RainSkillsAuditRepository()
