# -*- coding: utf8 -*-
import logging
from typing import Any, List, Tuple

from django.db import transaction
from django.db.models import QuerySet

from console.models.main import K8sResource
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
        resources = k8s_resources_repo.get_by_id(resource_id)
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
    def delete_k8s_resource(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str, name: str,
                            resource_id: str) -> None:
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        resources = k8s_resources_repo.get_by_id(resource_id)
        if name != "未识别":
            data = {
                "app_id": region_app_id,
                "resource_yaml": resources.content,
                "namespace": namespace,
                "name": name,
                "kind": resources.kind,
                "state": resources.state
            }
            region_api.delete_app_resource(enterprise_id, region_name, data)
        k8s_resources_repo.delete_by_id(resource_id)

    def batch_delete_k8s_resource(self, enterprise_id: str, tenant_name: str, app_id: str, region_name: str,
                                  resource_ids: Any) -> None:
        resources = k8s_resources_repo.list_by_ids(resource_ids)
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        data = {
            "app_id":
            region_app_id,
            "k8s_resources": [{
                "app_id": region_app_id,
                "resource_yaml": resource.content,
                "namespace": namespace,
                "name": resource.name,
                "kind": resource.kind,
                "state": resource.state
            } for resource in resources]
        }
        region_api.batch_delete_app_resources(enterprise_id, region_name, data)
        resources.delete()

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
