# -*- coding: utf8 -*-
"""
  Created on 2018/5/28.
"""
from console.models.main import GroupAppMigrateRecord


class GroupAppMigrationRespository(object):
    def create_migrate_record(self, **params):
        return GroupAppMigrateRecord.objects.create(**params)

    def get_by_event_id(self, event_id):
        return GroupAppMigrateRecord.objects.filter(event_id=event_id).first()

    def get_by_restore_id(self, restore_id):
        return GroupAppMigrateRecord.objects.filter(restore_id=restore_id).first()

    def get_by_original_group_id(self, original_grup_id):
        return GroupAppMigrateRecord.objects.filter(original_group_id=original_grup_id)

    def get_user_unfinished_migrate_record(self, group_id):
        return GroupAppMigrateRecord.objects.filter(group_id=group_id).exclude(status__in=['success', 'failed'])


migrate_repo = GroupAppMigrationRespository()
