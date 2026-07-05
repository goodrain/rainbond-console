# -*- coding: utf8 -*-
"""
  Created on 2018/5/23.
"""
from typing import Any, Dict, Optional, Tuple

from django.db.models import QuerySet

from console.models.main import GroupAppBackupRecord


class GroupAppBackupRecordRespository(object):
    def get_multi_apps_backup_records(self, group_ids: Any) -> QuerySet:
        return GroupAppBackupRecord.objects.filter(group_id__in=group_ids)

    def get_group_backup_records(self, team_id: str, region_name: str,
                                 group_id: str) -> QuerySet:
        return GroupAppBackupRecord.objects.filter(team_id=team_id, region=region_name, group_id=group_id)

    def get_group_backup_records_by_team_id(self, team_id: str,
                                            region_name: str) -> QuerySet:
        return GroupAppBackupRecord.objects.filter(team_id=team_id, region=region_name)

    def create_backup_records(self, **params: Any) -> GroupAppBackupRecord:
        return GroupAppBackupRecord.objects.create(**params)

    def get_record_by_backup_id(self, team_id: str, backup_id: str) -> Optional[GroupAppBackupRecord]:
        if team_id:
            return GroupAppBackupRecord.objects.filter(team_id=team_id, backup_id=backup_id).first()
        else:
            return GroupAppBackupRecord.objects.filter(backup_id=backup_id).first()

    def get_record_by_group_id(self, group_id: str) -> QuerySet:
        return GroupAppBackupRecord.objects.filter(group_id=group_id)

    def delete_record_by_backup_id(self, team_id: str, backup_id: str) -> Tuple[int, Dict[str, int]]:
        return GroupAppBackupRecord.objects.filter(team_id=team_id, backup_id=backup_id).delete()

    def get_record_by_group_id_and_backup_id(self, group_id: str,
                                             backup_id: str) -> QuerySet:
        return GroupAppBackupRecord.objects.filter(group_id=group_id, backup_id=backup_id)

    @staticmethod
    def count_by_app_id(app_id: str) -> int:
        return GroupAppBackupRecord.objects.filter(group_id=app_id).count()


backup_record_repo = GroupAppBackupRecordRespository()
