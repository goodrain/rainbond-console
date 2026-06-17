from typing import Any

from django.db.models import QuerySet

from console.models.main import OperationLog


class OperationLogRepo(object):
    def create(self, **data: Any) -> OperationLog:
        return OperationLog.objects.create(**data)

    def list(self) -> QuerySet:
        return OperationLog.objects.all().values()


operation_log_repo = OperationLogRepo()
