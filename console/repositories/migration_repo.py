# -*- coding: utf8 -*-
"""
  Created on 2018/5/28.
"""
from typing import Any, Optional

from django.db.models import QuerySet

from console.models.main import GroupAppMigrateRecord


class GroupAppMigrationRespository(object):
    def create_migrate_record(self, **params: Any) -> GroupAppMigrateRecord:
        return GroupAppMigrateRecord.objects.create(**params)

    def get_by_event_id(self, event_id: str) -> Optional[GroupAppMigrateRecord]:
        return GroupAppMigrateRecord.objects.filter(event_id=event_id).first()

    def get_by_restore_id(self, restore_id: str) -> Optional[GroupAppMigrateRecord]:
        return GroupAppMigrateRecord.objects.filter(restore_id=restore_id).first()

    def get_by_original_group_id(self, original_grup_id: str) -> QuerySet:
        return GroupAppMigrateRecord.objects.filter(original_group_id=original_grup_id)

    def get_user_unfinished_migrate_record(self, group_uuid: str) -> QuerySet:
        return GroupAppMigrateRecord.objects.filter(group_uuid=group_uuid).exclude(status__in=['success', 'failed'])


migrate_repo = GroupAppMigrationRespository()
