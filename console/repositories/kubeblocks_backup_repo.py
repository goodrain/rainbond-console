# -*- coding: utf-8 -*-

from datetime import datetime
from typing import Any, Optional

from django.db.models import QuerySet

from console.models import KubeBlocksBackupRepo


class KubeBlocksBackupRepoRepository(object):
    def list_by_team(self, tenant_id: str, region_name: str) -> QuerySet[KubeBlocksBackupRepo]:
        return KubeBlocksBackupRepo.objects.filter(
            tenant_id=tenant_id,
            region_name=region_name,
            is_deleted=False,
        ).order_by("-update_time", "-ID")

    def get_by_repo_name(self, tenant_id: str, region_name: str,
                         repo_name: str) -> Optional[KubeBlocksBackupRepo]:
        return KubeBlocksBackupRepo.objects.filter(
            tenant_id=tenant_id,
            region_name=region_name,
            repo_name=repo_name,
            is_deleted=False,
        ).first()

    def get_by_region_repo_name(self, region_name: str, repo_name: str) -> Optional[KubeBlocksBackupRepo]:
        return KubeBlocksBackupRepo.objects.filter(
            region_name=region_name,
            repo_name=repo_name,
        ).first()

    def get_deleted_by_region_repo_name(self, region_name: str,
                                        repo_name: str) -> Optional[KubeBlocksBackupRepo]:
        return KubeBlocksBackupRepo.objects.filter(
            region_name=region_name,
            repo_name=repo_name,
            is_deleted=True,
        ).first()

    def get_by_display_name(self, tenant_id: str, region_name: str,
                            display_name: str) -> Optional[KubeBlocksBackupRepo]:
        return KubeBlocksBackupRepo.objects.filter(
            tenant_id=tenant_id,
            region_name=region_name,
            display_name=display_name,
            is_deleted=False,
        ).first()

    def create(self, **kwargs: Any) -> KubeBlocksBackupRepo:
        return KubeBlocksBackupRepo.objects.create(**kwargs)

    def update(self, repo: KubeBlocksBackupRepo, **kwargs: Any) -> KubeBlocksBackupRepo:
        kwargs["update_time"] = datetime.now()
        for key, value in kwargs.items():
            setattr(repo, key, value)
        repo.save()
        return repo

    def delete(self, repo: KubeBlocksBackupRepo) -> None:
        repo.delete()


kubeblocks_backup_repo_repo = KubeBlocksBackupRepoRepository()
