# -*- coding: utf-8 -*-
import logging
import re
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.repositories.rainskills_audit_repo import rainskills_audit_repo
from console.services.auth.authentication import EnterpriseBoundAgentRuntimeAuthentication

_SKILL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
logger = logging.getLogger("default")


def _error(status_code: int, error_code: str, message: str) -> Response:
    return Response({
        "status_code": status_code,
        "error_code": error_code,
        "msg": message,
    }, status=status_code)


def _positive_int(raw_value: Any, default: int, minimum: int, maximum: int) -> int:
    if raw_value in (None, ""):
        return default
    if isinstance(raw_value, bool):
        raise ValueError("invalid integer")
    value = int(raw_value)
    if value < minimum or value > maximum:
        raise ValueError("integer out of range")
    return value


class EnterpriseBoundRainSkillsAuditView(APIView):
    authentication_classes = (EnterpriseBoundAgentRuntimeAuthentication, )
    permission_classes = (IsAuthenticated, )

    @staticmethod
    def enterprise_id(request: Request) -> str:
        return str(getattr(request, "audit_enterprise_id", "") or "")


class InternalRainSkillsAuditEventsView(EnterpriseBoundRainSkillsAuditView):

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            after_cursor = _positive_int(request.GET.get("after_cursor"), 0, 0, 2**63 - 1)
            limit = _positive_int(request.GET.get("limit"), 100, 1, 500)
        except (TypeError, ValueError):
            return _error(400, "invalid_cursor", "after_cursor or limit is invalid")

        enterprise_id = self.enterprise_id(request)
        stale_seconds = int(getattr(settings, "RAINSKILLS_AUDIT_UNKNOWN_AFTER_SECONDS", 1800))
        unknown_count = rainskills_audit_repo.materialize_stale_unknown(
            enterprise_id,
            stale_before=timezone.now() - timedelta(seconds=max(stale_seconds, 60)),
        )
        if unknown_count:
            logger.info(
                "rainskills_audit_metric name=terminal_unknown value=%s",
                unknown_count,
            )
        events = rainskills_audit_repo.list_events(enterprise_id, after_cursor, limit + 1)
        has_more = len(events) > limit
        page = events[:limit]
        next_cursor = page[-1].id if page else after_cursor
        latest_cursor = rainskills_audit_repo.latest_event_cursor(enterprise_id)
        logger.info(
            "rainskills_audit_metric name=agent_cursor_lag value=%s",
            max(latest_cursor - after_cursor, 0),
        )
        return Response({
            "data": [{"cursor": event.id, "event": event.payload} for event in page],
            "meta": {
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        }, status=200)


class InternalRainSkillsSkillSnapshotView(EnterpriseBoundRainSkillsAuditView):

    def get(self, request: Request, content_sha256: str, *args: Any, **kwargs: Any) -> Response:
        skill_id = str(request.GET.get("skill_id") or "")
        profile = str(request.GET.get("profile") or "")
        if not _SHA256_PATTERN.fullmatch(content_sha256) or not _SKILL_ID_PATTERN.fullmatch(skill_id) or profile != "cli":
            return _error(400, "invalid_snapshot_query", "skill snapshot query is invalid")

        snapshot = rainskills_audit_repo.get_snapshot(
            self.enterprise_id(request), skill_id, profile, content_sha256)
        if snapshot is None:
            return _error(404, "skill_snapshot_not_found", "skill snapshot not found")
        return Response({
            "data": {
                "skill_id": snapshot.skill_id,
                "profile": snapshot.profile,
                "package_version": snapshot.package_version,
                "source_revision": snapshot.source_revision,
                "content_sha256": snapshot.content_sha256,
                "bundle_sha256": snapshot.bundle_sha256,
                "provenance": snapshot.provenance,
                "content": snapshot.content_text,
            },
        }, status=200)
