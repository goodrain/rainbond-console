from typing import Any, List, Optional

from django.db import IntegrityError
from django.db.models import QuerySet

from www.models.main import HelmRepoInfo, TaskEvent


class HelmRepo(object):
    def create_helm_repo(self, **params: Any) -> HelmRepoInfo:
        return HelmRepoInfo.objects.create(**params)

    def get_all_repo(self) -> QuerySet[HelmRepoInfo]:
        return HelmRepoInfo.objects.filter()

    def delete_helm_repo(self, repo_name: str) -> Optional[tuple[int, dict[str, int]]]:
        data = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not data:
            return None
        return data.delete()

    def get_helm_repo_by_name(self, repo_name: str) -> Optional[dict]:
        data = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not data:
            return None
        repo: dict = data[0].to_dict()
        return repo

    def get_helm_repo_by_url(self, url: str) -> Optional[dict]:
        data = HelmRepoInfo.objects.filter(repo_url=url)
        if not data:
            return None
        repo: dict = data[0].to_dict()
        return repo

    def update_helm_repo(self, repo_name: str, repo_url: str) -> None:
        data = HelmRepoInfo.objects.filter(repo_name=repo_name)
        if not data:
            return None
        data[0].repo_url = repo_url
        data[0].save()


class RegionEvent(object):
    # 创建 TaskEvent
    def create_region_event(self, **params: Any) -> None:
        try:
            event = TaskEvent(**params)
            event.save()  # 保存到数据库
        except IntegrityError as e:
            # 如果插入重复记录，捕获错误并处理
            raise Exception(f"Error creating TaskEvent: {str(e)}")

    # 列出指定 enterprise_id 和 task_id 的事件
    def list_event(self, eid: str, task_id: str) -> QuerySet[TaskEvent]:
        return TaskEvent.objects.filter(enterprise_id=eid, task_id=task_id)

    # 更新状态批量更新 TaskEvent 的状态
    def update_status_in_batch(self, event_ids: List[str], status: str) -> None:
        try:
            TaskEvent.objects.filter(ID__in=event_ids).update(status=status)  # 批量更新状态
        except IntegrityError as e:
            raise Exception(f"Error updating TaskEvent status: {str(e)}")

    # 删除指定 enterprise_id 和 task_id 的事件
    def delete_event(self, eid: str, task_id: str) -> None:
        try:
            TaskEvent.objects.filter(enterprise_id=eid, task_id=task_id).delete()  # 删除相关事件
        except IntegrityError as e:
            raise Exception(f"Error deleting TaskEvent: {str(e)}")


helm_repo = HelmRepo()
region_event = RegionEvent()
