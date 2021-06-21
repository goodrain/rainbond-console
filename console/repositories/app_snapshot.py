# -*- coding: utf-8 -*-

from console.exception.bcode import ErrAppSnapshotNotFound
from console.exception.bcode import ErrAppSnapshotExists
from console.models.main import AppUpgradeSnapshot


class AppSnapshotRepo(object):
    @staticmethod
    def get_by_snapshot_id(snapshot_id):
        try:
            return AppUpgradeSnapshot.objects.get(snapshot_id=snapshot_id)
        except AppUpgradeSnapshot.DoesNotExist:
            raise ErrAppSnapshotNotFound

    def create(self, snapshot: AppUpgradeSnapshot):
        try:
            self.get_by_snapshot_id(snapshot.snapshot_id)
            raise ErrAppSnapshotExists
        except ErrAppSnapshotNotFound:
            snapshot.save()
            return snapshot


app_snapshot_repo = AppSnapshotRepo()
