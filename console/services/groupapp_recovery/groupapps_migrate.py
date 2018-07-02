# -*- coding: utf8 -*-
"""
  Created on 2018/5/25.
  应用迁移
"""
from console.repositories.backup_repo import backup_record_repo
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class GroupappsMigrateService(object):
    def start_migrate(self, user, current_team, current_region, migrate_team, migrate_region, backup_id):
        backup_record = backup_record_repo.get_record_by_backup_id(backup_id)
        if not backup_record:
            return 404, "无备份记录"
        data = {
            # TODO 跟region端交互的数据
            "team": migrate_team,
            "region": migrate_region
        }
        region_api.star_apps_migrate_task(current_region, current_team, data)
        # 创建迁移记录

        return 200, "操作成功，开始备份"


migrate_service = GroupappsMigrateService()