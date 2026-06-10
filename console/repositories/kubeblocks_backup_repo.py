# -*- coding: utf-8 -*-

from datetime import datetime

from console.models import KubeBlocksBackupRepo


class KubeBlocksBackupRepoRepository(object):
    def list_by_team(self, tenant_id, region_name):
        return KubeBlocksBackupRepo.objects.filter(
            tenant_id=tenant_id,
            region_name=region_name,
            is_deleted=False,
        ).order_by("-update_time", "-ID")

    def get_by_repo_name(self, tenant_id, region_name, repo_name):
        return KubeBlocksBackupRepo.objects.filter(
            tenant_id=tenant_id,
            region_name=region_name,
            repo_name=repo_name,
            is_deleted=False,
        ).first()

    def get_by_region_repo_name(self, region_name, repo_name):
        return KubeBlocksBackupRepo.objects.filter(
            region_name=region_name,
            repo_name=repo_name,
        ).first()

    def get_by_display_name(self, tenant_id, region_name, display_name):
        return KubeBlocksBackupRepo.objects.filter(
            tenant_id=tenant_id,
            region_name=region_name,
            display_name=display_name,
            is_deleted=False,
        ).first()

    def create(self, **kwargs):
        return KubeBlocksBackupRepo.objects.create(**kwargs)

    def update(self, repo, **kwargs):
        kwargs["update_time"] = datetime.now()
        for key, value in kwargs.items():
            setattr(repo, key, value)
        repo.save()
        return repo

    def mark_deleted(self, repo):
        repo.is_deleted = True
        repo.status = "Deleted"
        repo.update_time = datetime.now()
        repo.save()
        return repo


kubeblocks_backup_repo_repo = KubeBlocksBackupRepoRepository()
