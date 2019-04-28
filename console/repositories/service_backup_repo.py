# -*- coding: utf-8 -*-
from console.models import TenantServiceBackup


class TenantServiceBackupRepository(object):
    def create(self, **data):
        return TenantServiceBackup.objects.create(**data)


service_backup_repo = TenantServiceBackupRepository()
