# -*- coding: utf-8 -*-

from console.exception.bcode import ErrAppSnapshotNotFound
from console.exception.bcode import ErrAppSnapshotExists
from console.models.main import AppSnapshot


class AppSnapshotRepo(object):
    @staticmethod
    def get_by_snapshot_id(snapshot_id):
        try:
            return AppSnapshot.objects.get(snapshot_id=snapshot_id)
        except AppSnapshot.DoesNotExist:
            raise ErrAppSnapshotNotFound

    def create(self, snapshot: AppSnapshot):
        try:
            self.get_by_snapshot_id(snapshot.snapshot_id)
            raise ErrAppSnapshotExists
        except ErrAppSnapshotNotFound:
            snapshot.save()
            return snapshot


app_snapshot_repo = AppSnapshotRepo()
