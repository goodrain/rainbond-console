# -*- coding: utf-8 -*-
from console.models.main import TenantServiceBackup


class TenantServiceBackupRepository(object):
    def create(self, **data):
        return TenantServiceBackup.objects.create(**data)

    def get_newest_by_sid(self, tid, sid):
        try:
            return TenantServiceBackup.objects.filter(tenant_id=tid, service_id=sid)\
                .order_by("-update_time")[0:1].get()
        except IndexError:
            return None

    def del_by_sid(self, tid, sid):
        TenantServiceBackup.objects.filter(tenant_id=tid, service_id=sid).delete()


service_backup_repo = TenantServiceBackupRepository()
