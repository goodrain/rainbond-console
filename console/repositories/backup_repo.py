# -*- coding: utf8 -*-
"""
  Created on 2018/5/23.
"""
from console.models.main import GroupAppBackupRecord


class GroupAppBackupRecordRespository(object):
    def get_multi_apps_backup_records(self, group_ids):
        return GroupAppBackupRecord.objects.filter(group_id__in=group_ids)

    def get_group_backup_records(self, team_id, region_name, group_id):
        return GroupAppBackupRecord.objects.filter(team_id=team_id, region=region_name, group_id=group_id)

    def get_group_backup_records_by_team_id(self, team_id, region_name):
        return GroupAppBackupRecord.objects.filter(team_id=team_id, region=region_name)

    def create_backup_records(self, **params):
        return GroupAppBackupRecord.objects.create(**params)

    def get_record_by_backup_id(self, team_id, backup_id):
        if team_id:
            return GroupAppBackupRecord.objects.filter(team_id=team_id, backup_id=backup_id).first()
        else:
            return GroupAppBackupRecord.objects.filter(backup_id=backup_id).first()

    def get_record_by_group_id(self, group_id):
        return GroupAppBackupRecord.objects.filter(group_id=group_id)

    def delete_record_by_backup_id(self, team_id, backup_id):
        return GroupAppBackupRecord.objects.filter(team_id=team_id, backup_id=backup_id).delete()

    def get_record_by_group_id_and_backup_id(self, group_id, backup_id):
        return GroupAppBackupRecord.objects.filter(group_id=group_id, backup_id=backup_id)

    @staticmethod
    def count_by_app_id(app_id):
        return GroupAppBackupRecord.objects.filter(group_id=app_id).count()


backup_record_repo = GroupAppBackupRecordRespository()
