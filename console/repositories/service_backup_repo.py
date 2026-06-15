# -*- coding: utf-8 -*-
from typing import Any, Optional

from console.models.main import TenantServiceBackup


class TenantServiceBackupRepository(object):
    def create(self, **data: Any) -> TenantServiceBackup:
        return TenantServiceBackup.objects.create(**data)

    def get_newest_by_sid(self, tid: str, sid: str) -> Optional[TenantServiceBackup]:
        try:
            return TenantServiceBackup.objects.filter(tenant_id=tid, service_id=sid)\
                .order_by("-update_time")[0:1].get()
        except IndexError:
            return None

    def del_by_sid(self, tid: str, sid: str) -> None:
        TenantServiceBackup.objects.filter(tenant_id=tid, service_id=sid).delete()


service_backup_repo = TenantServiceBackupRepository()
