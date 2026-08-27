# -*- coding: utf8 -*-
import logging
from typing import Any, Dict, List, Tuple

from django.db import transaction
from django.db.models import QuerySet

from console.exception.main import ServiceHandleException
from console.models.main import K8S_RESOURCE_DELETE_STATUS_ACTIVE, K8S_RESOURCE_DELETE_STATUS_DELETING, \
    K8S_RESOURCE_DELETE_STATUS_FAILED, K8sResource
from console.repositories.k8s_resources import k8s_resources_repo
from console.repositories.region_app import region_app_repo
from console.services.region_resource_processing import region_resource
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants

region_api = RegionInvokeApi()

logger = logging.getLogger('default')

DELETE_STATUS_DISPLAY = {
    K8S_RESOURCE_DELETE_STATUS_ACTIVE: "ACTIVE",
    K8S_RESOURCE_DELETE_STATUS_DELETING: "DELETING",
    K8S_RESOURCE_DELETE_STATUS_FAILED: "DELETE_FAILED",
}


class ComponentK8sResourceService(object):
    def get_by_appid_kind_name(self, app_id: str, kind: str, name: str) -> K8sResource:
        resources = k8s_resources_repo.get_by_app_id_kind_name(app_id, kind, name)
        return resources

    def list_by_app_id(self, app_id: str) -> QuerySet:
        resources = k8s_resources_repo.list_by_app_id(app_id)
        return resources

    def list_for_display(self, app_id: str) -> List[Dict[str, Any]]:
        resources = k8s_resources_repo.list_by_app_id(app_id).values()
        return [self._serialize_delete_status(resource) for resource in resources]

    @transaction.atomic
    def get_k8s_resource(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str, name: str,
                         resource_id: str) -> Any:
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        resources = k8s_resources_repo.get_by_id(resource_id)
        self._ensure_resource_is_active(app_id, resources)
        data = {
            "app_id": region_app_id,
            "resource_yaml": resources.content,
            "namespace": namespace,
            "name": name,
            "kind": resources.kind
        }
        res, body = region_api.get_app_resource(enterprise_id, region_name, data)
        k8s_resources_repo.update(app_id, name, resources.kind, content=body["bean"]["content"])  # type: ignore[index]  # NOTE: region_api returns Optional[dict]; runtime always non-None on success
        return body["bean"]  # type: ignore[index]  # NOTE: same as above

    @transaction.atomic
    def create_k8s_resource(self, enterprise_id: str, tenant_name: str, app_id: str, resource_yaml: str,
                            region_name: str) -> None:
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        data = {"app_id": region_app_id, "resource_yaml": resource_yaml, "namespace": namespace}
        res, body = region_api.create_app_resource(enterprise_id, region_name, data)
        region_resource.create_k8s_resources(body["list"], app_id)  # type: ignore[index]  # NOTE: region_api returns Optional[dict]; runtime always non-None on success

    @transaction.atomic
    def update_k8s_resource(self, enterprise_id: str, tenant_name: str, app_id: str, resource_yaml: str,
                            region_name: str, name: str, resource_id: str) -> Any:
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        resources = k8s_resources_repo.get_by_id(resource_id)
        self._ensure_resource_is_active(app_id, resources)
        data: dict = {
            "app_id": region_app_id,
            "resource_yaml": resource_yaml,
            "namespace": namespace,
            "name": name,
            "kind": resources.kind
        }
        res, body = region_api.update_app_resource(enterprise_id, region_name, data)
        data = {
            "content": body["bean"]["content"],  # type: ignore[index]  # NOTE: region_api returns Optional[dict]; runtime always non-None on success
            "error_overview": body["bean"]["error_overview"],  # type: ignore[index]  # NOTE: same as above
            "state": body["bean"]["state"]  # type: ignore[index]  # NOTE: same as above
        }
        k8s_resources_repo.update(app_id, name, resources.kind, **data)
        return data["state"]

    def delete_k8s_resource(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str, name: str,
                            resource_id: str) -> List[Dict[str, Any]]:
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        resources = k8s_resources_repo.get_by_id(resource_id)
        self._ensure_resource_belongs_to_app(app_id, resources)
        data = self._build_delete_target(region_app_id, namespace, resources)
        _, body = region_api.delete_app_resource(enterprise_id, region_name, data)
        statuses = self._region_delete_statuses(body)
        self._record_delete_acceptance([resources], statuses)
        return statuses

    def batch_delete_k8s_resource(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str,
                                  resource_ids: Any) -> List[Dict[str, Any]]:
        resource_ids = resource_ids or []
        resources = list(k8s_resources_repo.list_by_ids(resource_ids, app_id))
        try:
            expected_ids = {int(resource_id) for resource_id in resource_ids}
        except (TypeError, ValueError):
            raise ServiceHandleException("invalid k8s resource ids", "Kubernetes 资源 ID 格式错误", status_code=400)
        actual_ids = {resource.ID for resource in resources}
        if expected_ids != actual_ids:
            raise ServiceHandleException("k8s resource not found", "Kubernetes 资源不存在或不属于当前应用", status_code=404)
        if not resources:
            return []
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        data = {
            "app_id": region_app_id,
            "k8s_resources": [self._build_delete_target(region_app_id, namespace, resource) for resource in resources],
        }
        _, body = region_api.batch_delete_app_resources(enterprise_id, region_name, data)
        statuses = self._region_delete_statuses(body)
        self._record_delete_acceptance(resources, statuses)
        return statuses

    def reconcile_delete_statuses(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str) -> None:
        resources = list(k8s_resources_repo.list_deleting_by_app_id(app_id))
        if not resources:
            return
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        data = {
            "app_id": region_app_id,
            "k8s_resources": [self._build_delete_target(region_app_id, namespace, resource) for resource in resources],
        }
        try:
            _, body = region_api.get_app_resource_delete_status(enterprise_id, region_name, data)
            statuses = self._region_status_list(body)
        except Exception:
            # The Console record is a durable user-visible indication that cleanup
            # is still pending. A temporary Region outage must never make it vanish.
            logger.exception("reconcile k8s resource deletion status for app %s failed", app_id)
            return
        self._record_delete_reconciliation(resources, statuses)

    @staticmethod
    def _build_delete_target(region_app_id: str, namespace: str, resource: K8sResource) -> Dict[str, Any]:
        target = {
            "app_id": region_app_id,
            "resource_yaml": resource.content,
            "namespace": namespace,
            "name": resource.name,
            "kind": resource.kind,
            "state": resource.state,
        }
        if resource.region_resource_id:
            target["resource_id"] = resource.region_resource_id
        return target

    @staticmethod
    def _serialize_delete_status(resource: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(resource)
        delete_status = result.get("delete_status", K8S_RESOURCE_DELETE_STATUS_ACTIVE)
        try:
            delete_status = int(delete_status)
        except (TypeError, ValueError):
            delete_status = K8S_RESOURCE_DELETE_STATUS_FAILED
        result["delete_status"] = DELETE_STATUS_DISPLAY.get(delete_status, "DELETE_FAILED")
        return result

    @staticmethod
    def _region_delete_statuses(body: Any) -> List[Dict[str, Any]]:
        statuses = body.get("bean") if body else None
        if isinstance(statuses, dict):
            statuses = [statuses]
        if not isinstance(statuses, list):
            raise ServiceHandleException("invalid Region k8s delete response", "数据中心未返回有效的删除受理结果", status_code=502)
        return statuses

    @staticmethod
    def _region_status_list(body: Any) -> List[Dict[str, Any]]:
        statuses = body.get("list") if body else None
        if not isinstance(statuses, list):
            raise ServiceHandleException("invalid Region k8s delete status response", "数据中心未返回有效的删除状态", status_code=502)
        return statuses

    @staticmethod
    def _match_region_statuses(resources: List[K8sResource], statuses: List[Dict[str, Any]],
                               require_all: bool) -> List[Tuple[K8sResource, Dict[str, Any]]]:
        statuses_by_id = {int(status["resource_id"]): status for status in statuses if status.get("resource_id")}
        statuses_by_name_kind: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for status in statuses:
            key = (status.get("name", ""), status.get("kind", ""))
            statuses_by_name_kind.setdefault(key, []).append(status)

        matches = []
        for resource in resources:
            status = statuses_by_id.get(int(resource.region_resource_id or 0))
            if status is None and not resource.region_resource_id:
                candidates = statuses_by_name_kind.get((resource.name, resource.kind), [])
                if len(candidates) == 1:
                    status = candidates[0]
            if status is None:
                if require_all:
                    raise ServiceHandleException(
                        "Region k8s delete response is missing resource status",
                        "数据中心没有确认所有 Kubernetes 资源的删除请求，请稍后重试",
                        status_code=502)
                continue
            matches.append((resource, status))
        return matches

    @transaction.atomic
    def _record_delete_acceptance(self, resources: List[K8sResource], statuses: List[Dict[str, Any]]) -> None:
        for resource, status in self._match_region_statuses(resources, statuses, require_all=True):
            k8s_resources_repo.update_delete_lifecycle(resource.ID, status, accepted=True)

    @transaction.atomic
    def _record_delete_reconciliation(self, resources: List[K8sResource], statuses: List[Dict[str, Any]]) -> None:
        matches = self._match_region_statuses(resources, statuses, require_all=False)
        returned_region_ids = {int(status["resource_id"]) for _, status in matches if status.get("resource_id")}
        for resource, status in matches:
            if int(status.get("delete_status", K8S_RESOURCE_DELETE_STATUS_DELETING)) == K8S_RESOURCE_DELETE_STATUS_ACTIVE:
                status = dict(status)
                status["delete_status"] = K8S_RESOURCE_DELETE_STATUS_FAILED
                status["delete_error"] = "Region deletion lifecycle was reset unexpectedly"
            k8s_resources_repo.update_delete_lifecycle(resource.ID, status)
        for resource in resources:
            # Only an ID-backed target can interpret an absent Region record as a
            # physical NotFound. Legacy records first receive this ID on delete.
            if resource.region_resource_id and int(resource.region_resource_id) not in returned_region_ids:
                k8s_resources_repo.delete_by_id(resource.ID)

    @staticmethod
    def _ensure_resource_belongs_to_app(app_id: str, resource: K8sResource) -> None:
        if str(resource.app_id) != str(app_id):
            raise ServiceHandleException("k8s resource does not belong to app", "Kubernetes 资源不属于当前应用", status_code=404)

    def _ensure_resource_is_active(self, app_id: str, resource: K8sResource) -> None:
        self._ensure_resource_belongs_to_app(app_id, resource)
        if resource.delete_status != K8S_RESOURCE_DELETE_STATUS_ACTIVE:
            raise ServiceHandleException(
                "k8s resource cleanup is pending",
                "Kubernetes 资源正在删除或删除失败，请先等待清理完成或重试删除",
                status_code=409)

    def get_app_id_and_namespace(self, app_id: str, tenant_name: str, region_name: str) -> Tuple[Any, str]:
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        return tenant.namespace, region_app_id

    def create_governance_resource(self, app: Any, resource_yaml: str) -> None:
        # state	CreateSuccess = 1
        data = {
            "app_id": app.app_id,
            "name": app.k8s_app,
            "kind": "ServiceMesh",
            "content": resource_yaml,
            "state": 1,
        }
        k8s_resources_repo.create(**data)

    def update_governance_resource(self, app: Any, resource_yaml: str) -> None:
        # state	UpdateSuccess = 2
        data = {
            "content": resource_yaml,
            "state": 2,
        }
        k8s_resources_repo.update(app.app_id, app.k8s_app, "ServiceMesh", **data)

    def delete_governance_resource(self, app: Any) -> None:
        k8s_resources_repo.delete_by_name(app.app_id, "ServiceMesh", app.k8s_app)


k8s_resource_service = ComponentK8sResourceService()
