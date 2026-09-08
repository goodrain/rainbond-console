# -*- coding: utf8 -*-
import logging
from typing import Any, List, Tuple

import yaml

from django.db import transaction
from django.db.models import QuerySet

from console.models.main import K8sResource
from console.exception.main import ServiceHandleException
from console.repositories.k8s_resources import k8s_resources_repo
from console.repositories.region_app import region_app_repo
from console.services.region_resource_processing import region_resource
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class ComponentK8sResourceService(object):
    def get_by_appid_kind_name(self, app_id: str, kind: str, name: str) -> K8sResource:
        resources = k8s_resources_repo.get_by_app_id_kind_name(app_id, kind, name)
        return resources

    def list_by_app_id(self, app_id: str) -> QuerySet:
        resources = k8s_resources_repo.list_by_app_id(app_id)
        return resources

    @transaction.atomic
    def get_k8s_resource(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str, name: str,
                         resource_id: str) -> Any:
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        resources = k8s_resources_repo.get_by_app_id_and_id(app_id, resource_id)
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
        resources = k8s_resources_repo.get_by_app_id_and_id(app_id, resource_id)
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

    @transaction.atomic
    def delete_k8s_resource(self,
                            enterprise_id: str,
                            tenant_name: str,
                            app_id: str,
                            region_name: str,
                            name: str,
                            resource_id: str,
                            cascade_crd: bool = False,
                            is_enterprise_admin: bool = False) -> Any:
        return self.batch_delete_k8s_resource(enterprise_id,
                                              tenant_name,
                                              app_id,
                                              region_name, [resource_id],
                                              cascade_crd=cascade_crd,
                                              is_enterprise_admin=is_enterprise_admin)

    def preview_delete_k8s_resources(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str,
                                     resource_ids: Any) -> Any:
        resources = self._get_owned_resources(app_id, resource_ids)
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        data = self._build_region_resources_payload(region_app_id, namespace, resources)
        _, body = region_api.preview_delete_app_resources(enterprise_id, region_name, data)
        impact = (body or {}).get("bean") or {}
        for crd in impact.get("crds", []):
            crd.pop("affected_region_app_ids", None)
        return impact

    @transaction.atomic
    def batch_delete_k8s_resource(self,
                                  enterprise_id: str,
                                  tenant_name: str,
                                  app_id: str,
                                  region_name: str,
                                  resource_ids: Any,
                                  cascade_crd: bool = False,
                                  is_enterprise_admin: bool = False) -> Any:
        resources = self._get_owned_resources(app_id, resource_ids)
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        impact = self.preview_delete_k8s_resources(enterprise_id, tenant_name, app_id, region_name, resource_ids)
        if cascade_crd and not is_enterprise_admin:
            raise ServiceHandleException(msg="enterprise administrator is required for CRD cascade deletion",
                                         msg_show="仅企业管理员可以确认 CRD 跨应用级联删除",
                                         status_code=403)
        if impact.get("requires_cascade") and not is_enterprise_admin:
            raise ServiceHandleException(msg="CRD deletion affects other applications or unowned resources",
                                         msg_show="该 CRD 被其他应用或未归属资源使用，仅企业管理员可以级联删除",
                                         status_code=403)
        if impact.get("requires_cascade") and not cascade_crd:
            raise ServiceHandleException(msg="explicit CRD cascade confirmation is required",
                                         msg_show="删除会影响其他应用，请明确确认级联删除",
                                         status_code=409,
                                         bean=impact)

        data = self._build_region_resources_payload(region_app_id, namespace, resources)
        data["cascade_crd"] = cascade_crd
        _, body = region_api.batch_delete_app_resources(enterprise_id, region_name, data)
        result = (body or {}).get("bean") or {}
        if result.get("status") != "completed":
            raise ServiceHandleException(msg="Kubernetes resource deletion was not completed",
                                         msg_show="Kubernetes 资源删除未完成，元数据已保留",
                                         status_code=502,
                                         bean=result)

        deleted_client_ids = set(str(item) for item in result.get("deleted_client_ids", []))
        selected_ids = [resource.ID for resource in resources if str(resource.ID) in deleted_client_ids]
        if selected_ids:
            k8s_resources_repo.delete_by_ids(selected_ids)
        self._delete_cascaded_cr_metadata(region_name, result.get("cascaded_crds", []))
        return result

    @transaction.atomic
    def reconcile_k8s_resources(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str) -> Any:
        resources = list(k8s_resources_repo.list_available_resources(app_id))
        if not resources:
            return {"missing_client_ids": [], "unknown": []}
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        data = self._build_region_resources_payload(region_app_id, namespace, resources)
        _, body = region_api.reconcile_app_resources(enterprise_id, region_name, data)
        result = (body or {}).get("bean") or {}
        known_ids = set(str(resource.ID) for resource in resources)
        missing_ids = [int(item) for item in result.get("missing_client_ids", []) if str(item) in known_ids]
        if missing_ids:
            k8s_resources_repo.delete_by_ids(missing_ids)
        return result

    def _get_owned_resources(self, app_id: str, resource_ids: Any) -> List[K8sResource]:
        if not isinstance(resource_ids, (list, tuple)) or not resource_ids:
            raise ServiceHandleException(msg="resource ids are required", msg_show="请选择需要删除的 Kubernetes 资源", status_code=400)
        requested_ids = set(str(resource_id) for resource_id in resource_ids)
        resources = list(k8s_resources_repo.list_by_app_id_and_ids(app_id, resource_ids))
        if set(str(resource.ID) for resource in resources) != requested_ids:
            raise ServiceHandleException(msg="Kubernetes resource not found in current application",
                                         msg_show="部分 Kubernetes 资源不存在或不属于当前应用",
                                         status_code=404)
        return resources

    @staticmethod
    def _build_region_resources_payload(region_app_id: str, namespace: str, resources: List[K8sResource]) -> dict:
        return {
            "app_id":
            region_app_id,
            "k8s_resources": [{
                "client_id": str(resource.ID),
                "app_id": region_app_id,
                "resource_yaml": resource.content,
                "namespace": namespace,
                "name": resource.name,
                "kind": resource.kind,
                "state": resource.state
            } for resource in resources]
        }

    def _delete_cascaded_cr_metadata(self, region_name: str, crds: Any) -> None:
        app_ids = [mapping.app_id for mapping in region_app_repo.list_by_region(region_name)]
        if not app_ids:
            return
        delete_ids = set()
        for crd in crds or []:
            group = crd.get("group")
            kind = crd.get("kind")
            if not group or not kind:
                continue
            for resource in k8s_resources_repo.list_by_app_ids_and_kind(app_ids, kind):
                resource_group, resource_kind = self._yaml_group_kind(resource.content)
                if resource_group == group and resource_kind == kind:
                    delete_ids.add(resource.ID)
        if delete_ids:
            k8s_resources_repo.delete_by_ids(sorted(delete_ids))

    @staticmethod
    def _yaml_group_kind(content: str) -> Tuple[str, str]:
        try:
            resource = yaml.safe_load(content)
        except (TypeError, ValueError, yaml.YAMLError):
            return "", ""
        if not isinstance(resource, dict):
            return "", ""
        api_version = resource.get("apiVersion") or ""
        group = api_version.split("/", 1)[0] if "/" in api_version else ""
        return group, resource.get("kind") or ""

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
