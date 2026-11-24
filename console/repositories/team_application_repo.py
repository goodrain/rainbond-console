"""Scoped persistence for immutable team application records."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING
from uuid import UUID
from django.db.models import QuerySet

if TYPE_CHECKING:
    from console.models.team_application import TeamApplication


class TeamApplicationRepository:
    def __init__(self, model: type[TeamApplication] | None = None) -> None:
        self._model = model

    @property
    def model(self) -> type[TeamApplication]:
        if self._model is None:
            from console.models.team_application import TeamApplication
            self._model = TeamApplication
        return self._model

    def list(self, enterprise_id: str, user_id: int | None = None) -> QuerySet[TeamApplication]:
        rows = self.model.objects.filter(enterprise_id=enterprise_id)
        return rows if user_id is None else rows.filter(applicant_id=user_id)

    def locked(self, enterprise_id: str, request_id: str | UUID) -> TeamApplication | None:
        return self.model.objects.select_for_update().filter(enterprise_id=enterprise_id, id=request_id).first()

    def create(self, **values: Any) -> TeamApplication:
        return self.model.objects.create(**values)


team_application_repo = TeamApplicationRepository()
