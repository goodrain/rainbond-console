# -*- coding: utf8 -*-
import logging

from django.db import transaction

from console.repositories.k8s_resources import k8s_resources_repo
from console.repositories.region_app import region_app_repo
from console.services.region_resource_processing import region_resource
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants

region_api = RegionInvokeApi()

logger = logging.getLogger('default')


class ComponentK8sResourceService(object):
    def get_by_app_id_and_name(self, app_id, name):
        resources = k8s_resources_repo.get_by_app_id_name(app_id, name)
        return resources

    def list_by_app_id(self, app_id):
        resources = k8s_resources_repo.list_by_app_id(app_id)
        return resources

    @transaction.atomic
    def get_k8s_resource(self, enterprise_id, tenant_name, app_id, region_name, name, resource_id):
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        resources = k8s_resources_repo.get_by_id(resource_id)
        data = {"app_id": region_app_id, "resource_yaml": "", "namespace": namespace, "name": name, "kind": resources.kind}
        res, body = region_api.get_app_resource(enterprise_id, region_name, data)
        k8s_resources_repo.update(app_id, name, resources.kind, content=body["bean"]["content"])
        return body["bean"]

    @transaction.atomic
    def create_k8s_resource(self, enterprise_id, tenant_name, app_id, resource_yaml, region_name):
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        data = {"app_id": region_app_id, "resource_yaml": resource_yaml, "namespace": namespace}
        res, body = region_api.create_app_resource(enterprise_id, region_name, data)
        region_resource.create_k8s_resources(body["list"], app_id)

    @transaction.atomic
    def update_k8s_resource(self, enterprise_id, tenant_name, app_id, resource_yaml, region_name, name, resource_id):
        namespace, region_app_id = self.get_app_id_and_namespace(app_id, tenant_name, region_name)
        resources = k8s_resources_repo.get_by_id(resource_id)
        data = {
            "app_id": region_app_id,
            "resource_yaml": resource_yaml,
            "namespace": namespace,
            "name": name,
            "kind": resources.kind
        }
        res, body = region_api.update_app_resource(enterprise_id, region_name, data)
        data = {
            "content": body["bean"]["content"],
            "error_overview": body["bean"]["error_overview"],
            "state": body["bean"]["state"]
        }
        k8s_resources_repo.update(app_id, name, resources.kind, **data)
        return data["state"]

    @transaction.atomic
    def delete_k8s_resource(self, enterprise_id, tenant_name, app_id, region_name, name, resource_id):
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

    def batch_delete_k8s_resource(self, enterprise_id, tenant_name, app_id, region_name, resource_ids):
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

    def get_app_id_and_namespace(self, app_id, tenant_name, region_name):
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        region_app_id = region_app_repo.get_region_app_id(region_name, app_id)
        return tenant.namespace, region_app_id

    def create_governance_resource(self, app, resource_yaml):
        # state	CreateSuccess = 1
        data = {
            "app_id": app.app_id,
            "name": app.k8s_app,
            "kind": "ServiceMesh",
            "content": resource_yaml,
            "state": 1,
        }
        k8s_resources_repo.create(**data)

    def update_governance_resource(self, app, resource_yaml):
        # state	UpdateSuccess = 2
        data = {
            "content": resource_yaml,
            "state": 2,
        }
        k8s_resources_repo.update(app.app_id, app.k8s_app, "ServiceMesh", **data)

    def delete_governance_resource(self, app):
        k8s_resources_repo.delete_by_name(app.app_id, app.k8s_app)


k8s_resource_service = ComponentK8sResourceService()
